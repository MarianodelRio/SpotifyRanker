"""Unit tests for libs/ml/inference.py — no DB, no Spotify, no trained model files required."""

from __future__ import annotations

import json
import time

import numpy as np
import pytest
import torch

from libs.common.models import Track, UserProfile
from libs.ml.inference import (
    ModelNotTrainedError,
    compute_item_embedding,
    compute_user_embedding,
    get_vocab,
    load_model,
    score_candidates,
)
from libs.ml.models.item_tower import ItemTower
from libs.ml.models.user_tower import UserTower
from libs.ml.trainer import TowerPair

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_VOCAB = ["electronic", "pop", "rock"]
_INPUT_DIM = len(_VOCAB) + 20 + 4  # matches features._fixed_dim()


def _make_towers() -> TowerPair:
    torch.manual_seed(0)
    user_tower = UserTower(_INPUT_DIM)
    item_tower = ItemTower(_INPUT_DIM)
    user_tower.eval()
    item_tower.eval()
    return TowerPair(user_tower=user_tower, item_tower=item_tower)


def _make_profile() -> UserProfile:
    return UserProfile(
        genre_weights={"pop": 0.8, "rock": 0.5},
        artist_affinities={"artist_a": 0.9},
        known_track_ids=set(),
        global_like_ratio=0.6,
        diversity_score=0.4,
    )


def _make_track(popularity: int = 60) -> Track:
    return Track(
        spotify_id="track_001",
        title="Test Track",
        artist_name="Test Artist",
        album_title="Test Album",
        duration_ms=200000,
        popularity=popularity,
    )


# ---------------------------------------------------------------------------
# load_model — error handling
# ---------------------------------------------------------------------------


class TestLoadModel:
    def test_raises_when_all_files_missing(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        with pytest.raises(ModelNotTrainedError) as exc_info:
            load_model()
        msg = str(exc_info.value)
        assert "user_tower.pt" in msg
        assert "item_tower.pt" in msg
        assert "vocab.json" in msg

    def test_raises_when_only_vocab_missing(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        store = tmp_path / "models_store"
        store.mkdir()
        towers = _make_towers()
        torch.save(towers.user_tower.state_dict(), store / "user_tower.pt")
        torch.save(towers.item_tower.state_dict(), store / "item_tower.pt")
        with pytest.raises(ModelNotTrainedError) as exc_info:
            load_model()
        assert "vocab.json" in str(exc_info.value)

    def test_error_message_is_actionable(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        with pytest.raises(ModelNotTrainedError) as exc_info:
            load_model()
        assert "POST /model/train" in str(exc_info.value)

    def test_loads_successfully_with_valid_files(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        store = tmp_path / "models_store"
        store.mkdir()
        towers = _make_towers()
        torch.save(towers.user_tower.state_dict(), store / "user_tower.pt")
        torch.save(towers.item_tower.state_dict(), store / "item_tower.pt")
        (store / "vocab.json").write_text(json.dumps(_VOCAB))
        loaded = load_model()
        assert isinstance(loaded, TowerPair)
        assert isinstance(loaded.user_tower, UserTower)
        assert isinstance(loaded.item_tower, ItemTower)

    def test_loaded_towers_are_in_eval_mode(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        store = tmp_path / "models_store"
        store.mkdir()
        towers = _make_towers()
        torch.save(towers.user_tower.state_dict(), store / "user_tower.pt")
        torch.save(towers.item_tower.state_dict(), store / "item_tower.pt")
        (store / "vocab.json").write_text(json.dumps(_VOCAB))
        loaded = load_model()
        assert not loaded.user_tower.training
        assert not loaded.item_tower.training


# ---------------------------------------------------------------------------
# get_vocab — error handling
# ---------------------------------------------------------------------------


class TestGetVocab:
    def test_raises_when_vocab_missing(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        with pytest.raises(ModelNotTrainedError):
            get_vocab()

    def test_returns_vocab_list(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        store = tmp_path / "models_store"
        store.mkdir()
        (store / "vocab.json").write_text(json.dumps(_VOCAB))
        vocab = get_vocab()
        assert vocab == _VOCAB


# ---------------------------------------------------------------------------
# compute_user_embedding
# ---------------------------------------------------------------------------


class TestComputeUserEmbedding:
    def test_output_is_32_dim(self):
        towers = _make_towers()
        emb = compute_user_embedding(_make_profile(), towers, _VOCAB)
        assert emb.shape == (32,)

    def test_output_is_l2_normalized(self):
        towers = _make_towers()
        emb = compute_user_embedding(_make_profile(), towers, _VOCAB)
        norm = float(np.linalg.norm(emb))
        assert abs(norm - 1.0) < 1e-5

    def test_deterministic(self):
        towers = _make_towers()
        profile = _make_profile()
        emb1 = compute_user_embedding(profile, towers, _VOCAB)
        emb2 = compute_user_embedding(profile, towers, _VOCAB)
        np.testing.assert_array_equal(emb1, emb2)

    def test_empty_profile_does_not_raise(self):
        towers = _make_towers()
        emb = compute_user_embedding(UserProfile(), towers, _VOCAB)
        assert emb.shape == (32,)

    def test_unknown_genres_in_profile_are_ignored(self):
        towers = _make_towers()
        profile = UserProfile(genre_weights={"unknown_genre_xyz": 0.9})
        emb = compute_user_embedding(profile, towers, _VOCAB)
        assert emb.shape == (32,)


# ---------------------------------------------------------------------------
# compute_item_embedding
# ---------------------------------------------------------------------------


class TestComputeItemEmbedding:
    def test_output_is_32_dim(self):
        towers = _make_towers()
        emb = compute_item_embedding(_make_track(), towers, ["pop"], 70, _VOCAB)
        assert emb.shape == (32,)

    def test_output_is_l2_normalized(self):
        towers = _make_towers()
        emb = compute_item_embedding(_make_track(), towers, ["pop"], 70, _VOCAB)
        norm = float(np.linalg.norm(emb))
        assert abs(norm - 1.0) < 1e-5

    def test_deterministic(self):
        towers = _make_towers()
        track = _make_track()
        emb1 = compute_item_embedding(track, towers, ["pop"], 70, _VOCAB)
        emb2 = compute_item_embedding(track, towers, ["pop"], 70, _VOCAB)
        np.testing.assert_array_equal(emb1, emb2)

    def test_unknown_genre_produces_valid_embedding(self):
        towers = _make_towers()
        emb = compute_item_embedding(_make_track(), towers, ["jazz_obscure_xyz"], 50, _VOCAB)
        assert emb.shape == (32,)

    def test_zero_artist_popularity_sets_unknown_flag(self):
        towers = _make_towers()
        emb = compute_item_embedding(_make_track(), towers, [], 0, _VOCAB)
        assert emb.shape == (32,)


# ---------------------------------------------------------------------------
# score_candidates
# ---------------------------------------------------------------------------


class TestScoreCandidates:
    def test_empty_returns_empty_list(self):
        towers = _make_towers()
        user_emb = compute_user_embedding(_make_profile(), towers, _VOCAB)
        assert score_candidates(user_emb, []) == []

    def test_scores_in_minus_one_to_one(self):
        towers = _make_towers()
        profile = _make_profile()
        user_emb = compute_user_embedding(profile, towers, _VOCAB)
        item_embs = [
            compute_item_embedding(_make_track(p), towers, ["pop"], 60, _VOCAB)
            for p in range(10, 110, 10)
        ]
        scores = score_candidates(user_emb, item_embs)
        assert len(scores) == 10
        for s in scores:
            assert -1.0 - 1e-5 <= s <= 1.0 + 1e-5, f"Score {s} out of [-1, 1]"

    def test_returns_float_list(self):
        towers = _make_towers()
        user_emb = compute_user_embedding(_make_profile(), towers, _VOCAB)
        item_emb = compute_item_embedding(_make_track(), towers, ["rock"], 50, _VOCAB)
        scores = score_candidates(user_emb, [item_emb])
        assert isinstance(scores, list)
        assert isinstance(scores[0], float)

    def test_deterministic(self):
        towers = _make_towers()
        user_emb = compute_user_embedding(_make_profile(), towers, _VOCAB)
        item_embs = [
            compute_item_embedding(_make_track(), towers, ["pop"], 60, _VOCAB) for _ in range(5)
        ]
        scores1 = score_candidates(user_emb, item_embs)
        scores2 = score_candidates(user_emb, item_embs)
        assert scores1 == scores2

    def test_500_candidates_under_2_seconds(self):
        # Use a larger vocab to get a more realistic input_dim
        large_vocab = [f"genre_{i}" for i in range(100)]
        input_dim = len(large_vocab) + 20 + 4
        torch.manual_seed(0)
        user_tower = UserTower(input_dim)
        item_tower = ItemTower(input_dim)
        user_tower.eval()
        item_tower.eval()
        towers = TowerPair(user_tower=user_tower, item_tower=item_tower)

        profile = UserProfile(genre_weights={f"genre_{i}": float(i) / 100 for i in range(20)})
        user_emb = compute_user_embedding(profile, towers, large_vocab)
        item_embs = [
            compute_item_embedding(
                _make_track(i % 100),
                towers,
                [f"genre_{i % 100}"],
                i % 100,
                large_vocab,
            )
            for i in range(500)
        ]

        start = time.perf_counter()
        scores = score_candidates(user_emb, item_embs)
        elapsed = time.perf_counter() - start

        assert len(scores) == 500
        assert elapsed < 2.0, f"500-candidate inference took {elapsed:.2f}s (limit: 2s)"
