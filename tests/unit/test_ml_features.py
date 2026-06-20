import numpy as np

from libs.common.models import Track, UserProfile
from libs.ml.features import (
    _fixed_dim,
    build_genre_vocab,
    build_track_features,
    build_user_features,
    load_vocab,
    save_vocab,
)

# ── Fixtures ────────────────────────────────────────────────────────────────

VOCAB = ["electronic", "hip-hop", "indie", "jazz", "pop", "rock"]


def _track(popularity: int = 60) -> Track:
    return Track(
        spotify_id="tid1",
        title="Song",
        artist_name="Artist",
        album_title="Album",
        duration_ms=200_000,
        popularity=popularity,
    )


def _profile(
    genre_weights: dict | None = None,
    artist_affinities: dict | None = None,
    global_like_ratio: float = 0.7,
    diversity_score: float = 0.5,
) -> UserProfile:
    return UserProfile(
        genre_weights=genre_weights or {"pop": 0.9, "rock": 0.6},
        artist_affinities=artist_affinities or {"artist_a": 0.8, "artist_b": 0.4},
        known_track_ids=set(),
        global_like_ratio=global_like_ratio,
        diversity_score=diversity_score,
    )


# ── Vocabulary helpers ───────────────────────────────────────────────────────


class TestBuildGenreVocab:
    def test_deduplicates(self):
        vocab = build_genre_vocab(["pop", "rock", "pop", "jazz"])
        assert vocab == sorted({"pop", "rock", "jazz"})

    def test_sorted(self):
        vocab = build_genre_vocab(["rock", "indie", "electronic"])
        assert vocab == sorted(["rock", "indie", "electronic"])

    def test_empty(self):
        assert build_genre_vocab([]) == []


class TestVocabIO:
    def test_roundtrip(self, tmp_path):
        path = tmp_path / "vocab.json"
        save_vocab(VOCAB, path)
        loaded = load_vocab(path)
        assert loaded == VOCAB

    def test_creates_parent_dir(self, tmp_path):
        path = tmp_path / "subdir" / "vocab.json"
        save_vocab(VOCAB, path)
        assert path.exists()


# ── build_user_features ──────────────────────────────────────────────────────


class TestBuildUserFeatures:
    def test_returns_ndarray(self):
        vec = build_user_features(_profile(), VOCAB)
        assert isinstance(vec, np.ndarray)

    def test_correct_dimension(self):
        vec = build_user_features(_profile(), VOCAB)
        assert vec.shape == (_fixed_dim(VOCAB),)

    def test_dtype_float32(self):
        vec = build_user_features(_profile(), VOCAB)
        assert vec.dtype == np.float32

    def test_all_values_in_01(self):
        vec = build_user_features(_profile(), VOCAB)
        assert vec.min() >= 0.0
        assert vec.max() <= 1.0

    def test_known_genre_mapped(self):
        profile = _profile(genre_weights={"pop": 0.9})
        vec = build_user_features(profile, VOCAB)
        pop_idx = VOCAB.index("pop")
        assert abs(vec[pop_idx] - 0.9) < 1e-6

    def test_unknown_genre_maps_to_zero(self):
        profile = _profile(genre_weights={"unknown-genre-xyz": 0.9})
        vec = build_user_features(profile, VOCAB)
        assert vec[: len(VOCAB)].sum() == 0.0

    def test_deterministic(self):
        profile = _profile()
        vec1 = build_user_features(profile, VOCAB)
        vec2 = build_user_features(profile, VOCAB)
        np.testing.assert_array_equal(vec1, vec2)

    def test_cold_start_all_zeros(self):
        empty_profile = UserProfile()
        vec = build_user_features(empty_profile, VOCAB)
        assert vec.sum() == 0.0

    def test_artist_affinity_slots(self):
        affinities = {f"artist_{i}": float(i) / 25 for i in range(25)}
        profile = _profile(artist_affinities=affinities)
        vec = build_user_features(profile, VOCAB)
        artist_slots = vec[len(VOCAB) : len(VOCAB) + 20]
        # All filled slots must be in [0, 1]
        assert artist_slots.min() >= 0.0
        assert artist_slots.max() <= 1.0
        # Exactly 20 artist slots (rest truncated)
        assert len(artist_slots) == 20

    def test_global_like_ratio_and_diversity_score(self):
        profile = _profile(global_like_ratio=0.65, diversity_score=0.42)
        vec = build_user_features(profile, VOCAB)
        scalar_offset = len(VOCAB) + 20
        assert abs(vec[scalar_offset] - 0.65) < 1e-6
        assert abs(vec[scalar_offset + 1] - 0.42) < 1e-6

    def test_values_clamped_to_01(self):
        profile = _profile(
            genre_weights={"pop": 1.5},
            global_like_ratio=2.0,
            diversity_score=-0.3,
        )
        vec = build_user_features(profile, VOCAB)
        assert vec.min() >= 0.0
        assert vec.max() <= 1.0


# ── build_track_features ─────────────────────────────────────────────────────


class TestBuildTrackFeatures:
    def test_returns_ndarray(self):
        vec = build_track_features(_track(), ["pop"], 70, VOCAB)
        assert isinstance(vec, np.ndarray)

    def test_correct_dimension(self):
        vec = build_track_features(_track(), ["pop"], 70, VOCAB)
        assert vec.shape == (_fixed_dim(VOCAB),)

    def test_dtype_float32(self):
        vec = build_track_features(_track(), ["pop"], 70, VOCAB)
        assert vec.dtype == np.float32

    def test_all_values_in_01(self):
        vec = build_track_features(_track(popularity=80), ["rock", "pop"], 50, VOCAB)
        assert vec.min() >= 0.0
        assert vec.max() <= 1.0

    def test_known_genre_multi_hot(self):
        vec = build_track_features(_track(), ["pop", "rock"], 50, VOCAB)
        pop_idx = VOCAB.index("pop")
        rock_idx = VOCAB.index("rock")
        assert vec[pop_idx] == 1.0
        assert vec[rock_idx] == 1.0
        # All other genre slots are 0
        other_genre_slots = [vec[i] for i, g in enumerate(VOCAB) if g not in ("pop", "rock")]
        assert all(v == 0.0 for v in other_genre_slots)

    def test_unknown_genre_maps_to_zero(self):
        vec = build_track_features(_track(), ["totally-unknown-genre"], 50, VOCAB)
        assert vec[: len(VOCAB)].sum() == 0.0

    def test_normalized_track_popularity(self):
        vec = build_track_features(_track(popularity=60), [], 0, VOCAB)
        scalar_offset = len(VOCAB) + 20
        assert abs(vec[scalar_offset] - 0.6) < 1e-6

    def test_normalized_artist_popularity(self):
        vec = build_track_features(_track(), [], 80, VOCAB)
        scalar_offset = len(VOCAB) + 20
        assert abs(vec[scalar_offset + 1] - 0.8) < 1e-6

    def test_is_unknown_artist_flag_when_zero_popularity(self):
        vec = build_track_features(_track(), [], 0, VOCAB)
        scalar_offset = len(VOCAB) + 20
        assert vec[scalar_offset + 2] == 1.0

    def test_is_unknown_artist_flag_when_known(self):
        vec = build_track_features(_track(), [], 50, VOCAB)
        scalar_offset = len(VOCAB) + 20
        assert vec[scalar_offset + 2] == 0.0

    def test_deterministic(self):
        track = _track()
        vec1 = build_track_features(track, ["pop"], 70, VOCAB)
        vec2 = build_track_features(track, ["pop"], 70, VOCAB)
        np.testing.assert_array_equal(vec1, vec2)

    def test_no_genres_all_genre_slots_zero(self):
        vec = build_track_features(_track(), [], 50, VOCAB)
        assert vec[: len(VOCAB)].sum() == 0.0


# ── Cross-function: same dimension ───────────────────────────────────────────


class TestSameDimension:
    def test_user_and_track_vectors_have_same_shape(self):
        user_vec = build_user_features(_profile(), VOCAB)
        track_vec = build_track_features(_track(), ["pop"], 60, VOCAB)
        assert user_vec.shape == track_vec.shape

    def test_dimension_scales_with_vocab(self):
        small_vocab = ["pop", "rock"]
        large_vocab = ["electronic", "hip-hop", "indie", "jazz", "pop", "rock"]
        small_user = build_user_features(_profile(), small_vocab)
        large_user = build_user_features(_profile(), large_vocab)
        assert small_user.shape[0] < large_user.shape[0]
        assert small_user.shape == (_fixed_dim(small_vocab),)
        assert large_user.shape == (_fixed_dim(large_vocab),)
