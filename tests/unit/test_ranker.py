"""Tests for libs/ranker/ — modes, diversifier, and rank orchestration."""

from __future__ import annotations

import pytest

from libs.common.enums import CandidateSource, PlaylistMode
from libs.common.models import Candidate, RankedTrack, Track, UserProfile
from libs.ranker.diversifier import diversify
from libs.ranker.modes import apply_mode

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_track(
    spotify_id: str = "t1",
    artist: str = "Artist A",
    popularity: int = 50,
) -> Track:
    return Track(
        spotify_id=spotify_id,
        title=f"Track {spotify_id}",
        artist_name=artist,
        album_title="Album",
        duration_ms=200_000,
        popularity=popularity,
    )


def _make_candidate(
    spotify_id: str = "t1",
    artist: str = "Artist A",
    popularity: int = 50,
    artist_affinity_score: float = 0.0,
) -> Candidate:
    return Candidate(
        track=_make_track(spotify_id=spotify_id, artist=artist, popularity=popularity),
        source=CandidateSource.artist_discography,
        artist_affinity_score=artist_affinity_score,
    )


def _make_ranked(
    spotify_id: str,
    artist: str,
    final_score: float,
) -> RankedTrack:
    return RankedTrack(
        candidate=_make_candidate(spotify_id=spotify_id, artist=artist),
        final_score=final_score,
        score_breakdown={
            "base_score": final_score,
            "artist_affinity_bonus": 0.0,
            "novelty_adjustment": 0.0,
            "popularity_adjustment": 0.0,
            "mode_weight": 1.0,
        },
    )


# ---------------------------------------------------------------------------
# modes.py
# ---------------------------------------------------------------------------


class TestApplyMode:
    def test_score_breakdown_populated(self) -> None:
        candidate = _make_candidate()
        profile = UserProfile()
        _, breakdown = apply_mode(candidate, 0.5, profile, PlaylistMode.balanced)
        required_keys = {
            "base_score",
            "artist_affinity_bonus",
            "novelty_adjustment",
            "popularity_adjustment",
            "mode_weight",
        }
        assert required_keys.issubset(breakdown.keys())

    def test_score_breakdown_not_empty(self) -> None:
        candidate = _make_candidate()
        _, breakdown = apply_mode(candidate, 0.5, UserProfile(), PlaylistMode.adventurous)
        assert len(breakdown) >= 5

    def test_adventurous_boosts_unknown_artist(self) -> None:
        """Unknown artist gets a positive novelty_adjustment in adventurous mode."""
        unknown_candidate = _make_candidate(artist_affinity_score=0.0)
        _, breakdown = apply_mode(unknown_candidate, 0.5, UserProfile(), PlaylistMode.adventurous)
        assert breakdown["novelty_adjustment"] > 0.0

    def test_safe_penalises_unknown_artist(self) -> None:
        """Unknown artist gets a negative novelty_adjustment in safe mode."""
        unknown_candidate = _make_candidate(artist_affinity_score=0.0)
        _, breakdown = apply_mode(unknown_candidate, 0.5, UserProfile(), PlaylistMode.safe)
        assert breakdown["novelty_adjustment"] < 0.0

    def test_balanced_neutral_novelty(self) -> None:
        """Balanced mode applies zero novelty adjustment."""
        unknown_candidate = _make_candidate(artist_affinity_score=0.0)
        _, breakdown = apply_mode(unknown_candidate, 0.5, UserProfile(), PlaylistMode.balanced)
        assert breakdown["novelty_adjustment"] == 0.0

    def test_adventurous_higher_unknown_score_than_safe(self) -> None:
        """Core acceptance criterion: unknown artist ranks higher in adventurous vs safe."""
        unknown_candidate = _make_candidate(artist="Unknown Artist", artist_affinity_score=0.0)
        base = 0.5
        profile = UserProfile()

        adv_score, _ = apply_mode(unknown_candidate, base, profile, PlaylistMode.adventurous)
        safe_score, _ = apply_mode(unknown_candidate, base, profile, PlaylistMode.safe)
        assert adv_score > safe_score, (
            f"Adventurous score {adv_score:.4f} should exceed safe score {safe_score:.4f} "
            "for an unknown artist"
        )

    def test_safe_boosts_known_artist(self) -> None:
        """Known artist affinity bonus is larger in safe than adventurous."""
        profile = UserProfile(artist_affinities={"Artist A": 0.8})
        candidate = _make_candidate(artist="Artist A", artist_affinity_score=0.8)
        safe_score, _ = apply_mode(candidate, 0.5, profile, PlaylistMode.safe)
        adv_score, _ = apply_mode(candidate, 0.5, profile, PlaylistMode.adventurous)
        assert safe_score > adv_score

    def test_base_score_preserved_in_breakdown(self) -> None:
        candidate = _make_candidate()
        base = 0.7
        _, breakdown = apply_mode(candidate, base, UserProfile(), PlaylistMode.balanced)
        assert breakdown["base_score"] == pytest.approx(base)


# ---------------------------------------------------------------------------
# diversifier.py
# ---------------------------------------------------------------------------


class TestDiversify:
    def _pool_of(self, count: int) -> list[RankedTrack]:
        """100 candidates spread across many artists, each with a unique score."""
        tracks = []
        artists = [f"Artist_{i}" for i in range(count // 3 + 1)]
        for i in range(count):
            artist = artists[i % len(artists)]
            tracks.append(_make_ranked(f"t{i}", artist, final_score=1.0 - i * 0.001))
        return tracks

    def test_artist_cap_respected(self) -> None:
        """Acceptance criterion: 20-track playlist from 100 never has > 3 from same artist."""
        pool = self._pool_of(100)
        result = diversify(pool, n=20)
        assert len(result) == 20
        artist_counts: dict[str, int] = {}
        for rt in result:
            artist = rt.candidate.track.artist_name
            artist_counts[artist] = artist_counts.get(artist, 0) + 1
        for artist, count in artist_counts.items():
            assert count <= 3, f"{artist} appears {count} times (max 3)"

    def test_artist_cap_with_concentrated_pool(self) -> None:
        """Even when pool is dominated by one artist, cap applies."""
        dominant_artist = [
            _make_ranked(f"t{i}", "Dominant", final_score=1.0 - i * 0.01) for i in range(50)
        ]
        other = [
            _make_ranked(f"o{i}", f"Other_{i}", final_score=0.5 - i * 0.001) for i in range(50)
        ]
        pool = dominant_artist + other
        result = diversify(pool, n=20)
        dominant_count = sum(1 for rt in result if rt.candidate.track.artist_name == "Dominant")
        assert dominant_count <= 3

    def test_returns_at_most_n(self) -> None:
        pool = self._pool_of(100)
        result = diversify(pool, n=20)
        assert len(result) <= 20

    def test_preserves_order_within_artist_cap(self) -> None:
        """Higher-scored tracks are selected first."""
        tracks = [_make_ranked(f"t{i}", f"A_{i}", final_score=1.0 - i * 0.1) for i in range(10)]
        result = diversify(tracks, n=5)
        scores = [rt.final_score for rt in result]
        assert scores == sorted(scores, reverse=True)

    def test_genre_cap_respected(self) -> None:
        """When genres_map provided, no genre exceeds 40% of the playlist."""
        pool = [_make_ranked(f"t{i}", f"Artist_{i}", final_score=1.0 - i * 0.01) for i in range(30)]
        # First 20 tracks are all "pop", rest are "rock"
        genres_map = {f"t{i}": ["pop"] for i in range(20)}
        genres_map.update({f"t{i}": ["rock"] for i in range(20, 30)})
        result = diversify(pool, n=20, genres_map=genres_map)
        pop_count = sum(
            1 for rt in result if genres_map.get(rt.candidate.track.spotify_id, []) == ["pop"]
        )
        assert pop_count <= int(20 * 0.4)

    def test_empty_pool(self) -> None:
        assert diversify([], n=20) == []

    def test_n_zero(self) -> None:
        pool = self._pool_of(10)
        assert diversify(pool, n=0) == []

    def test_fewer_candidates_than_n(self) -> None:
        pool = self._pool_of(5)
        result = diversify(pool, n=20)
        assert len(result) == 5


# ---------------------------------------------------------------------------
# modes.py — RankedTrack schema compliance
# ---------------------------------------------------------------------------


class TestRankedTrackSchema:
    def test_ranked_track_matches_schema(self) -> None:
        """RankedTrack objects must match common.models.RankedTrack exactly."""
        candidate = _make_candidate()
        profile = UserProfile()
        final_score, breakdown = apply_mode(candidate, 0.5, profile, PlaylistMode.balanced)
        rt = RankedTrack(
            candidate=candidate,
            final_score=final_score,
            score_breakdown=breakdown,
        )
        assert isinstance(rt.candidate, Candidate)
        assert isinstance(rt.final_score, float)
        assert isinstance(rt.score_breakdown, dict)
        assert len(rt.score_breakdown) > 0
