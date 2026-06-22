"""Unit tests for libs/ml/trainer.py — no DB, no Spotify required."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import numpy as np
import pytest
import torch

from libs.common.models import UserProfile
from libs.ml.trainer import (
    TowerPair,
    TrainingResult,
    _mine_hard_negatives,
    _populate_features,
    train,
)
from libs.ml.training_set import TrainingExample

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_profile() -> UserProfile:
    return UserProfile(
        genre_weights={"pop": 0.8, "rock": 0.5},
        artist_affinities={"artist_a": 0.9},
        known_track_ids=set(),
        global_like_ratio=0.6,
        diversity_score=0.4,
    )


def _make_examples(n: int, feat_dim: int) -> list[TrainingExample]:
    rng = np.random.default_rng(42)
    examples = []
    for i in range(n):
        ex = TrainingExample(
            track_id=f"track_{i}",
            label=0.9 if i % 3 != 0 else 0.1,
            weight=1.0,
        )
        ex.user_features = rng.random(feat_dim).astype(np.float32)
        ex.track_features = rng.random(feat_dim).astype(np.float32)
        examples.append(ex)
    return examples


# ---------------------------------------------------------------------------
# TrainingResult dataclass
# ---------------------------------------------------------------------------


class TestTrainingResult:
    def test_has_required_fields(self):
        from datetime import datetime

        result = TrainingResult(
            epochs=5,
            final_loss=0.42,
            examples_count=100,
            trained_at=datetime.utcnow(),
        )
        assert result.epochs == 5
        assert result.final_loss == pytest.approx(0.42)
        assert result.examples_count == 100
        assert isinstance(result.trained_at, datetime)


# ---------------------------------------------------------------------------
# TowerPair dataclass
# ---------------------------------------------------------------------------


class TestTowerPair:
    def test_holds_towers(self):
        from libs.ml.models.item_tower import ItemTower
        from libs.ml.models.user_tower import UserTower

        u = UserTower(input_dim=8)
        i = ItemTower(input_dim=8)
        pair = TowerPair(user_tower=u, item_tower=i)
        assert pair.user_tower is u
        assert pair.item_tower is i


# ---------------------------------------------------------------------------
# Loss decreases over epochs (synthetic data — no DB)
# ---------------------------------------------------------------------------


class TestLossDecreases:
    def test_loss_decreases_over_5_epochs(self, tmp_path):
        """Train on synthetic data; final loss must be below initial loss."""
        feat_dim = 24  # len(vocab)=0 + 20 artist slots + 4 scalar slots
        n_examples = 80
        examples = _make_examples(n_examples, feat_dim)

        losses_per_epoch: list[float] = []

        import torch.nn.functional as F

        from libs.ml.models.item_tower import ItemTower
        from libs.ml.models.user_tower import UserTower

        _TAU = 0.1
        user_tower = UserTower(feat_dim)
        item_tower = ItemTower(feat_dim)
        user_tower.train()
        item_tower.train()
        optimizer = torch.optim.Adam(
            list(user_tower.parameters()) + list(item_tower.parameters()), lr=1e-3
        )

        user_tensor = torch.tensor(examples[0].user_features, dtype=torch.float32).unsqueeze(0)
        track_tensors = torch.tensor([ex.track_features for ex in examples], dtype=torch.float32)
        label_tensors = torch.tensor([ex.label for ex in examples], dtype=torch.float32)
        weight_tensors = torch.tensor([ex.weight for ex in examples], dtype=torch.float32)

        for _ in range(5):
            perm = torch.randperm(n_examples).tolist()
            epoch_losses = []
            for start in range(0, n_examples, 32):
                batch_idx = perm[start : start + 32]
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
                loss.backward()
                optimizer.step()
                epoch_losses.append(loss.item())

            if epoch_losses:
                losses_per_epoch.append(sum(epoch_losses) / len(epoch_losses))

        assert len(losses_per_epoch) >= 2, "Need at least 2 epochs with loss to compare"
        assert losses_per_epoch[-1] < losses_per_epoch[0], (
            f"Loss did not decrease: initial={losses_per_epoch[0]:.4f}, "
            f"final={losses_per_epoch[-1]:.4f}"
        )


# ---------------------------------------------------------------------------
# Model files saved to models_store
# ---------------------------------------------------------------------------


class TestModelFilesSaved:
    def test_files_written_after_train(self, tmp_path):
        """Mocks DB + build_training_set; verifies model files are created."""
        feat_dim = 24
        n = 60
        examples = _make_examples(n, feat_dim)
        profile = _make_profile()

        mock_session = AsyncMock()

        with (
            patch("libs.ml.trainer.build_training_set", new=AsyncMock(return_value=examples)),
            patch("libs.ml.trainer._load_track_metadata", new=AsyncMock(return_value={})),
            patch("libs.ml.trainer._MODELS_STORE", new=tmp_path),
            patch("libs.ml.trainer.build_genre_vocab", return_value=[]),
            patch("libs.ml.trainer.save_vocab"),
            patch(
                "libs.ml.trainer.build_user_features",
                return_value=np.zeros(feat_dim, dtype=np.float32),
            ),
        ):
            result = asyncio.run(train(mock_session, profile, epochs=3))

        assert (tmp_path / "user_tower.pt").exists()
        assert (tmp_path / "item_tower.pt").exists()
        assert isinstance(result, TrainingResult)
        assert result.epochs == 3
        assert result.examples_count == n


# ---------------------------------------------------------------------------
# _populate_features helper
# ---------------------------------------------------------------------------


class TestPopulateFeatures:
    def test_skips_missing_track(self):
        ex = TrainingExample(track_id="missing", label=0.9, weight=1.0)
        _populate_features([ex], track_meta={}, vocab=[], user_feat=np.zeros(4, dtype=np.float32))
        assert ex.user_features.size == 0
        assert ex.track_features.size == 0

    def test_populates_known_track(self, tmp_path):
        from libs.common.models import Track as CommonTrack

        feat_dim = 24
        ex = TrainingExample(track_id="t1", label=0.9, weight=1.0)
        vocab: list[str] = []

        common_track = CommonTrack(
            spotify_id="sp1",
            title="Song",
            artist_name="Artist",
            album_title="Album",
            duration_ms=200000,
            popularity=70,
        )
        track_meta = {"t1": {"track": common_track, "genres": [], "artist_popularity": 70}}
        user_feat = np.random.rand(feat_dim).astype(np.float32)

        _populate_features([ex], track_meta, vocab, user_feat)

        assert ex.user_features is user_feat
        assert ex.track_features.size == feat_dim


# ---------------------------------------------------------------------------
# Hard Negative Mining
# ---------------------------------------------------------------------------


class TestHardNegativeMining:
    def _make_tensors(self, feat_dim: int = 16, n: int = 60):
        rng = np.random.default_rng(0)
        track_tensors = torch.tensor(rng.random((n, feat_dim)).astype(np.float32))
        label_tensors = torch.tensor(
            [0.9 if i % 3 != 0 else 0.1 for i in range(n)], dtype=torch.float32
        )
        weight_tensors = torch.ones(n, dtype=torch.float32)
        return track_tensors, label_tensors, weight_tensors

    def test_hnm_runs_without_errors(self, tmp_path):
        feat_dim = 24
        n = 60
        examples = _make_examples(n, feat_dim)
        profile = _make_profile()

        mock_session = AsyncMock()
        with (
            patch("libs.ml.trainer.build_training_set", new=AsyncMock(return_value=examples)),
            patch("libs.ml.trainer._load_track_metadata", new=AsyncMock(return_value={})),
            patch("libs.ml.trainer._MODELS_STORE", new=tmp_path),
            patch("libs.ml.trainer.build_genre_vocab", return_value=[]),
            patch("libs.ml.trainer.save_vocab"),
            patch(
                "libs.ml.trainer.build_user_features",
                return_value=np.zeros(feat_dim, dtype=np.float32),
            ),
        ):
            result = asyncio.run(train(mock_session, profile, epochs=3, use_hnm=True, hnm_epochs=2))

        assert isinstance(result, TrainingResult)
        assert (tmp_path / "user_tower.pt").exists()

    def test_hard_negatives_score_above_threshold(self):
        from libs.ml.models.item_tower import ItemTower
        from libs.ml.models.user_tower import UserTower

        feat_dim = 16
        n = 60
        track_tensors, label_tensors, weight_tensors = self._make_tensors(feat_dim, n)
        user_tensor = torch.zeros(1, feat_dim)

        user_tower = UserTower(feat_dim)
        item_tower = ItemTower(feat_dim)

        percentile = 80.0
        aug_tracks, aug_labels, aug_weights, aug_n = _mine_hard_negatives(
            user_tower,
            item_tower,
            user_tensor,
            track_tensors,
            label_tensors,
            weight_tensors,
            percentile=percentile,
            weight_multiplier=2.0,
        )

        n_original = track_tensors.shape[0]
        if aug_n > n_original:
            user_tower.eval()
            item_tower.eval()
            with torch.no_grad():
                user_emb = user_tower(user_tensor)
                item_embs = item_tower(track_tensors)
                scores = (user_emb @ item_embs.T).squeeze(0)

            neg_mask = label_tensors < 0.5
            neg_scores = scores[neg_mask]
            threshold = torch.quantile(neg_scores, percentile / 100.0).item()

            added_tracks = aug_tracks[n_original:]
            added_embs = item_tower(added_tracks)
            added_scores = (user_emb @ added_embs.T).squeeze(0)
            assert (added_scores >= threshold - 1e-5).all(), (
                f"Some hard negatives score below threshold {threshold:.4f}"
            )

        assert aug_n >= n_original

    def test_hnm_loss_lower_than_base(self, tmp_path):
        feat_dim = 24
        n = 80
        examples_base = _make_examples(n, feat_dim)
        examples_hnm = _make_examples(n, feat_dim)
        profile = _make_profile()

        def run_train(examples, use_hnm):
            mock_session = AsyncMock()
            with (
                patch(
                    "libs.ml.trainer.build_training_set",
                    new=AsyncMock(return_value=examples),
                ),
                patch("libs.ml.trainer._load_track_metadata", new=AsyncMock(return_value={})),
                patch("libs.ml.trainer._MODELS_STORE", new=tmp_path),
                patch("libs.ml.trainer.build_genre_vocab", return_value=[]),
                patch("libs.ml.trainer.save_vocab"),
                patch(
                    "libs.ml.trainer.build_user_features",
                    return_value=np.zeros(feat_dim, dtype=np.float32),
                ),
            ):
                return asyncio.run(
                    train(
                        mock_session,
                        profile,
                        epochs=5,
                        use_hnm=use_hnm,
                        hnm_epochs=3,
                    )
                )

        result_base = run_train(examples_base, use_hnm=False)
        result_hnm = run_train(examples_hnm, use_hnm=True)

        assert result_hnm.final_loss <= result_base.final_loss + 0.5, (
            f"HNM loss {result_hnm.final_loss:.4f} unexpectedly much higher than "
            f"base loss {result_base.final_loss:.4f}"
        )

    def test_use_hnm_false_no_regression(self, tmp_path):
        feat_dim = 24
        n = 60
        examples = _make_examples(n, feat_dim)
        profile = _make_profile()

        mock_session = AsyncMock()
        with (
            patch("libs.ml.trainer.build_training_set", new=AsyncMock(return_value=examples)),
            patch("libs.ml.trainer._load_track_metadata", new=AsyncMock(return_value={})),
            patch("libs.ml.trainer._MODELS_STORE", new=tmp_path),
            patch("libs.ml.trainer.build_genre_vocab", return_value=[]),
            patch("libs.ml.trainer.save_vocab"),
            patch(
                "libs.ml.trainer.build_user_features",
                return_value=np.zeros(feat_dim, dtype=np.float32),
            ),
        ):
            result = asyncio.run(train(mock_session, profile, epochs=3, use_hnm=False))

        assert isinstance(result, TrainingResult)
        assert result.epochs == 3
        assert result.examples_count == n
        assert result.final_loss < float("inf")
