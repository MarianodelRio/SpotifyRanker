from __future__ import annotations

from pathlib import Path

import numpy as np
import torch

from libs.common.models import Track, UserProfile
from libs.ml.features import build_track_features, build_user_features, load_vocab
from libs.ml.models.item_tower import ItemTower
from libs.ml.models.user_tower import UserTower
from libs.ml.trainer import TowerPair

_MODELS_STORE = Path("models_store")


class ModelNotTrainedError(Exception):
    """Raised when required model files are absent from models_store/."""


def load_model() -> TowerPair:
    """Load trained towers from models_store/. Raises ModelNotTrainedError if files are absent."""
    user_path = _MODELS_STORE / "user_tower.pt"
    item_path = _MODELS_STORE / "item_tower.pt"
    vocab_path = _MODELS_STORE / "vocab.json"

    missing = [p for p in (user_path, item_path, vocab_path) if not p.exists()]
    if missing:
        names = ", ".join(p.name for p in missing)
        raise ModelNotTrainedError(
            f"Model not trained — missing files in models_store/: {names}. "
            "Run POST /model/train first."
        )

    vocab = load_vocab(vocab_path)
    dummy_profile = UserProfile()
    input_dim = len(build_user_features(dummy_profile, vocab))

    user_tower = UserTower(input_dim)
    item_tower = ItemTower(input_dim)
    user_tower.load_state_dict(torch.load(user_path, map_location="cpu", weights_only=True))
    item_tower.load_state_dict(torch.load(item_path, map_location="cpu", weights_only=True))
    user_tower.eval()
    item_tower.eval()

    return TowerPair(user_tower=user_tower, item_tower=item_tower)


def get_vocab() -> list[str]:
    """Load genre vocabulary from models_store/vocab.json."""
    vocab_path = _MODELS_STORE / "vocab.json"
    if not vocab_path.exists():
        raise ModelNotTrainedError(
            "Vocabulary not found in models_store/vocab.json. Run POST /model/train first."
        )
    return load_vocab(vocab_path)


def compute_user_embedding(
    profile: UserProfile,
    towers: TowerPair,
    vocab: list[str],
) -> np.ndarray[tuple[int], np.dtype[np.float32]]:
    """Build user feature vector and project through UserTower. Returns 32-dim L2-normalized array."""
    features = build_user_features(profile, vocab)
    tensor = torch.tensor(features, dtype=torch.float32).unsqueeze(0)
    with torch.no_grad():
        emb = towers.user_tower(tensor)
    result: np.ndarray[tuple[int], np.dtype[np.float32]] = emb.squeeze(0).numpy()
    return result


def compute_item_embedding(
    track: Track,
    towers: TowerPair,
    genres: list[str],
    artist_popularity: int,
    vocab: list[str],
) -> np.ndarray[tuple[int], np.dtype[np.float32]]:
    """Build track feature vector and project through ItemTower. Returns 32-dim L2-normalized array."""
    features = build_track_features(track, genres, artist_popularity, vocab)
    tensor = torch.tensor(features, dtype=torch.float32).unsqueeze(0)
    with torch.no_grad():
        emb = towers.item_tower(tensor)
    result: np.ndarray[tuple[int], np.dtype[np.float32]] = emb.squeeze(0).numpy()
    return result


def score_candidates(
    user_emb: np.ndarray[tuple[int], np.dtype[np.float32]],
    item_embs: list[np.ndarray[tuple[int], np.dtype[np.float32]]],
) -> list[float]:
    """Dot-product scores of user embedding against each item embedding.

    Both vectors are L2-normalized (tower outputs), so scores are in [-1, 1].
    """
    if not item_embs:
        return []
    user_tensor = torch.tensor(user_emb, dtype=torch.float32)
    items_tensor = torch.tensor(np.stack(item_embs), dtype=torch.float32)
    with torch.no_grad():
        scores = (items_tensor @ user_tensor).tolist()
    result: list[float] = scores
    return result
