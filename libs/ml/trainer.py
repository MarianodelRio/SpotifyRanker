from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import torch
import torch.nn.functional as F
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from db.models import Artist, TrackArtist
from db.models import Track as DBTrack
from libs.common.models import Track as CommonTrack
from libs.common.models import UserProfile
from libs.ml.features import (
    build_genre_vocab,
    build_track_features,
    build_user_features,
    save_vocab,
)
from libs.ml.models.item_tower import ItemTower
from libs.ml.models.user_tower import UserTower
from libs.ml.training_set import TrainingExample, build_training_set

_MODELS_STORE = Path("models_store")
_TAU = 0.1
_DEFAULT_EPOCHS = 20
_DEFAULT_LR = 1e-3
_BATCH_SIZE = 32


@dataclass
class TrainingResult:
    epochs: int
    final_loss: float
    examples_count: int
    trained_at: datetime


@dataclass
class TowerPair:
    user_tower: UserTower
    item_tower: ItemTower


async def train(
    session: AsyncSession,
    profile: UserProfile,
    epochs: int = _DEFAULT_EPOCHS,
) -> TrainingResult:
    """Train UserTower + ItemTower with InfoNCE loss and save model files."""
    examples = await build_training_set(session, profile)
    if not examples:
        raise ValueError("Cannot train: no training examples in the database.")

    track_meta = await _load_track_metadata(session, {ex.track_id for ex in examples})

    all_genres: list[str] = []
    for meta in track_meta.values():
        all_genres.extend(meta["genres"])
    vocab = build_genre_vocab(all_genres)

    _MODELS_STORE.mkdir(parents=True, exist_ok=True)
    save_vocab(vocab, _MODELS_STORE / "vocab.json")

    user_feat = build_user_features(profile, vocab)
    _populate_features(examples, track_meta, vocab, user_feat)

    examples = [ex for ex in examples if ex.user_features.size > 0 and ex.track_features.size > 0]
    if not examples:
        raise ValueError("No examples with valid features after population.")

    input_dim = len(examples[0].user_features)
    user_tower = UserTower(input_dim)
    item_tower = ItemTower(input_dim)
    user_tower.train()
    item_tower.train()

    optimizer = torch.optim.Adam(
        list(user_tower.parameters()) + list(item_tower.parameters()), lr=_DEFAULT_LR
    )

    user_tensor = torch.tensor(examples[0].user_features, dtype=torch.float32).unsqueeze(0)
    track_tensors = torch.tensor([ex.track_features for ex in examples], dtype=torch.float32)
    label_tensors = torch.tensor([ex.label for ex in examples], dtype=torch.float32)
    weight_tensors = torch.tensor([ex.weight for ex in examples], dtype=torch.float32)

    n = len(examples)
    final_loss = float("inf")

    for _ in range(epochs):
        perm = torch.randperm(n).tolist()
        epoch_losses: list[float] = []

        for start in range(0, n, _BATCH_SIZE):
            batch_idx = perm[start : start + _BATCH_SIZE]
            if len(batch_idx) < 2:
                continue

            track_batch = track_tensors[batch_idx]
            label_batch = label_tensors[batch_idx]
            weight_batch = weight_tensors[batch_idx]

            user_emb = user_tower(user_tensor)
            item_embs = item_tower(track_batch)

            scores = (user_emb @ item_embs.T).squeeze(0) / _TAU

            pos_mask = label_batch >= 0.5
            if not pos_mask.any():
                continue

            log_softmax = F.log_softmax(scores, dim=0)
            loss = -(log_softmax[pos_mask] * weight_batch[pos_mask]).mean()

            optimizer.zero_grad()
            loss.backward()  # type: ignore[no-untyped-call]
            torch.nn.utils.clip_grad_norm_(
                list(user_tower.parameters()) + list(item_tower.parameters()), max_norm=1.0
            )
            optimizer.step()

            epoch_losses.append(loss.item())

        if epoch_losses:
            final_loss = sum(epoch_losses) / len(epoch_losses)

    user_tower.eval()
    item_tower.eval()
    torch.save(user_tower.state_dict(), _MODELS_STORE / "user_tower.pt")
    torch.save(item_tower.state_dict(), _MODELS_STORE / "item_tower.pt")

    return TrainingResult(
        epochs=epochs,
        final_loss=final_loss,
        examples_count=len(examples),
        trained_at=datetime.utcnow(),
    )


def _populate_features(
    examples: list[TrainingExample],
    track_meta: dict[str, dict[str, Any]],
    vocab: list[str],
    user_feat: Any,
) -> None:
    for ex in examples:
        meta = track_meta.get(ex.track_id)
        if meta is None:
            continue
        ex.user_features = user_feat
        ex.track_features = build_track_features(
            meta["track"], meta["genres"], meta["artist_popularity"], vocab
        )


async def _load_track_metadata(
    session: AsyncSession, track_ids: set[str]
) -> dict[str, dict[str, Any]]:
    """Load tracks with primary artist + genres for feature building."""
    stmt = (
        select(DBTrack)
        .where(DBTrack.id.in_(track_ids))
        .options(
            selectinload(DBTrack.artist_links)
            .selectinload(TrackArtist.artist)
            .selectinload(Artist.genres)
        )
    )
    result = await session.scalars(stmt)
    db_tracks = list(result.unique())

    meta: dict[str, dict[str, Any]] = {}
    for db_track in db_tracks:
        primary_artist = next(
            (ta.artist for ta in db_track.artist_links if ta.is_primary), None
        ) or (db_track.artist_links[0].artist if db_track.artist_links else None)

        genres: list[str] = []
        artist_popularity = 0
        if primary_artist:
            genres = [g.name for g in primary_artist.genres]
            artist_popularity = primary_artist.popularity or 0

        common_track = CommonTrack(
            spotify_id=db_track.spotify_id,
            title=db_track.title,
            artist_name=primary_artist.name if primary_artist else "",
            album_title="",
            duration_ms=db_track.duration_ms or 0,
            popularity=db_track.popularity or 0,
        )
        meta[db_track.id] = {
            "track": common_track,
            "genres": genres,
            "artist_popularity": artist_popularity,
        }

    return meta
