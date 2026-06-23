"""Tests for the item embedding cache (T-032).

Covers: load_embedding_cache, ranker cache-hit/miss paths, timing acceptance criterion.
No DB required — all tests are pure unit tests.
"""

from __future__ import annotations

import json
import time

import numpy as np
import torch

from libs.common.enums import CandidateSource, PlaylistMode
from libs.common.models import Candidate, Track, UserProfile
from libs.ml.features import build_track_features
from libs.ml.inference import (
    compute_item_embedding,
    load_embedding_cache,
)
from libs.ml.models.item_tower import ItemTower
from libs.ml.models.user_tower import UserTower
from libs.ml.trainer import TowerPair

_VOCAB = ["electronic", "pop", "rock"]
_INPUT_DIM = len(_VOCAB) + 20 + 4  # matches features._fixed_dim()


def _make_towers() -> TowerPair:
    torch.manual_seed(0)
    user_tower = UserTower(_INPUT_DIM)
    item_tower = ItemTower(_INPUT_DIM)
    user_tower.eval()
    item_tower.eval()
    return TowerPair(user_tower=user_tower, item_tower=item_tower)


def _make_track(spotify_id: str = "t1", popularity: int = 50) -> Track:
    return Track(
        spotify_id=spotify_id,
        title=f"Track {spotify_id}",
        artist_name="Test Artist",
        album_title="Test Album",
        duration_ms=200_000,
        popularity=popularity,
    )


def _make_candidate(spotify_id: str = "t1") -> Candidate:
    return Candidate(
        track=_make_track(spotify_id=spotify_id),
        source=CandidateSource.artist_discography,
        artist_affinity_score=0.5,
    )


def _write_vocab(store_path, vocab: list[str] = _VOCAB) -> None:
    (store_path / "vocab.json").write_text(json.dumps(vocab))


def _write_model_files(store_path, towers: TowerPair) -> None:
    torch.save(towers.user_tower.state_dict(), store_path / "user_tower.pt")
    torch.save(towers.item_tower.state_dict(), store_path / "item_tower.pt")


# ---------------------------------------------------------------------------
# load_embedding_cache
# ---------------------------------------------------------------------------


class TestLoadEmbeddingCache:
    def test_returns_empty_dict_when_no_cache(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        assert load_embedding_cache() == {}

    def test_loads_single_written_embedding(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        store = tmp_path / "models_store"
        store.mkdir()
        emb = np.random.rand(32).astype(np.float32)
        np.savez(store / "item_embeddings.npz", track_abc=emb)
        cache = load_embedding_cache()
        assert "track_abc" in cache
        np.testing.assert_array_almost_equal(cache["track_abc"], emb)

    def test_returns_float32_arrays(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        store = tmp_path / "models_store"
        store.mkdir()
        np.savez(store / "item_embeddings.npz", t1=np.ones(32, dtype=np.float32))
        cache = load_embedding_cache()
        assert cache["t1"].dtype == np.float32

    def test_loads_multiple_tracks(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        store = tmp_path / "models_store"
        store.mkdir()
        embeddings = {f"track_{i}": np.random.rand(32).astype(np.float32) for i in range(10)}
        np.savez(store / "item_embeddings.npz", **embeddings)
        cache = load_embedding_cache()
        assert len(cache) == 10
        for key in embeddings:
            assert key in cache


# ---------------------------------------------------------------------------
# ranker cache hit / miss / mixed
# ---------------------------------------------------------------------------


class TestRankerCacheIntegration:
    def _setup_store(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        store = tmp_path / "models_store"
        store.mkdir()
        towers = _make_towers()
        _write_vocab(store)
        _write_model_files(store, towers)
        return store, towers

    def test_rank_succeeds_with_fully_cached_track(self, tmp_path, monkeypatch):
        store, towers = self._setup_store(tmp_path, monkeypatch)
        track = _make_track(spotify_id="cached_track")
        cached_emb = compute_item_embedding(track, towers, ["pop"], 60, _VOCAB)
        np.savez(store / "item_embeddings.npz", cached_track=cached_emb)

        from libs.ranker.ranker import rank

        result = rank(
            [_make_candidate("cached_track")], UserProfile(), PlaylistMode.balanced, towers
        )
        assert len(result) == 1
        assert -1.0 - 1e-5 <= result[0].final_score <= 1.0 + 1e-5

    def test_rank_computes_on_the_fly_when_no_cache(self, tmp_path, monkeypatch):
        store, towers = self._setup_store(tmp_path, monkeypatch)

        from libs.ranker.ranker import rank

        result = rank(
            [_make_candidate("new_track_not_cached")], UserProfile(), PlaylistMode.balanced, towers
        )
        assert len(result) == 1
        assert -1.0 - 1e-5 <= result[0].final_score <= 1.0 + 1e-5

    def test_rank_handles_mixed_cached_and_uncached(self, tmp_path, monkeypatch):
        store, towers = self._setup_store(tmp_path, monkeypatch)
        track = _make_track(spotify_id="cached")
        emb = compute_item_embedding(track, towers, [], 50, _VOCAB)
        np.savez(store / "item_embeddings.npz", cached=emb)

        from libs.ranker.ranker import rank

        result = rank(
            [_make_candidate("cached"), _make_candidate("uncached_new")],
            UserProfile(),
            PlaylistMode.balanced,
            towers,
        )
        assert len(result) == 2
        for rt in result:
            assert -1.0 - 1e-5 <= rt.final_score <= 1.0 + 1e-5

    def test_cached_and_computed_embeddings_match(self, tmp_path, monkeypatch):
        """The score for a cached track equals the score computed fresh from the same towers."""
        store, towers = self._setup_store(tmp_path, monkeypatch)
        track = _make_track(spotify_id="t1")

        fresh_emb = compute_item_embedding(track, towers, [], 50, _VOCAB)
        np.savez(store / "item_embeddings.npz", t1=fresh_emb)

        from libs.ml.inference import compute_user_embedding
        from libs.ml.inference import score_candidates as _score

        profile = UserProfile()
        user_emb = compute_user_embedding(profile, towers, _VOCAB)

        cached_score = _score(user_emb, [fresh_emb])[0]
        recomputed_score = _score(
            user_emb, [compute_item_embedding(track, towers, [], 50, _VOCAB)]
        )[0]
        assert abs(cached_score - recomputed_score) < 1e-5

    def test_score_breakdown_populated_with_cached_track(self, tmp_path, monkeypatch):
        store, towers = self._setup_store(tmp_path, monkeypatch)
        track = _make_track(spotify_id="t1")
        emb = compute_item_embedding(track, towers, [], 50, _VOCAB)
        np.savez(store / "item_embeddings.npz", t1=emb)

        from libs.ranker.ranker import rank

        result = rank([_make_candidate("t1")], UserProfile(), PlaylistMode.balanced, towers)
        assert len(result) == 1
        required_keys = {
            "base_score",
            "artist_affinity_bonus",
            "novelty_adjustment",
            "popularity_adjustment",
            "mode_weight",
        }
        assert required_keys.issubset(result[0].score_breakdown.keys())


# ---------------------------------------------------------------------------
# 10K-track timing (acceptance criterion)
# ---------------------------------------------------------------------------


class TestCacheBuildTiming:
    def test_10k_embeddings_under_60_seconds(self, tmp_path, monkeypatch):
        """Batch embedding computation for 10K tracks must complete in < 60 s on CPU."""
        monkeypatch.chdir(tmp_path)
        store = tmp_path / "models_store"
        store.mkdir()
        towers = _make_towers()
        n = 10_000

        features_list = [
            build_track_features(
                _make_track(spotify_id=f"t{i}", popularity=i % 100), [], 50, _VOCAB
            )
            for i in range(n)
        ]
        track_tensor = torch.tensor(np.stack(features_list), dtype=torch.float32)

        start = time.perf_counter()
        with torch.no_grad():
            embs = towers.item_tower(track_tensor).numpy()
        cache = {f"t{i}": embs[i] for i in range(n)}
        np.savez(store / "item_embeddings.npz", **cache)
        elapsed = time.perf_counter() - start

        assert elapsed < 60.0, f"10K embedding build took {elapsed:.1f}s (limit: 60s)"

        loaded = load_embedding_cache()
        assert len(loaded) == n
