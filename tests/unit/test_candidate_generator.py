"""Unit tests for libs/candidates/ — sources, deduplicator, and generator."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from db.models import Base
from db.repositories.artist import ArtistRepository
from libs.candidates.deduplicator import deduplicate_and_upsert
from libs.candidates.generator import CandidateGenerator
from libs.candidates.sources.artist_discography import fetch_artist_discography_candidates
from libs.candidates.sources.genre_search import fetch_genre_search_candidates
from libs.common.enums import CandidateSource
from libs.common.models import Candidate, Track, UserProfile
from libs.spotify.fetcher import SpotifyFetcher

# ── Helpers ───────────────────────────────────────────────────────────────────


def _track(spotify_id: str, title: str = "T") -> Track:
    return Track(
        spotify_id=spotify_id,
        title=title,
        artist_name="A",
        album_title="AL",
        duration_ms=200_000,
        popularity=50,
    )


def _make_fetcher(*, search_tracks: list[Track] | None = None) -> SpotifyFetcher:
    fetcher = MagicMock(spec=SpotifyFetcher)
    fetcher.search = AsyncMock(return_value=search_tracks or [])
    return fetcher


async def _seed_artist(session: AsyncSession, spotify_id: str, name: str) -> None:
    await ArtistRepository(session).upsert(spotify_id=spotify_id, name=name)


@pytest.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as s:
        yield s
    await engine.dispose()


# ── artist_discography source ─────────────────────────────────────────────────


async def test_artist_discography_returns_unknown_tracks():
    profile = UserProfile(
        artist_affinities={"artist1": 0.9},
        known_track_ids={"known_track"},
    )
    fetcher = _make_fetcher(search_tracks=[_track("known_track"), _track("new_track")])

    result = await fetch_artist_discography_candidates(
        profile, fetcher, {"artist1": "Artist One"}
    )

    assert len(result) == 1
    assert result[0].track.spotify_id == "new_track"
    assert result[0].source == CandidateSource.artist_discography


async def test_artist_discography_empty_affinities():
    profile = UserProfile()
    fetcher = _make_fetcher()

    result = await fetch_artist_discography_candidates(profile, fetcher, {})

    assert result == []
    fetcher.search.assert_not_called()


async def test_artist_discography_skips_artist_missing_from_db():
    profile = UserProfile(artist_affinities={"unknown_id": 0.9})
    fetcher = _make_fetcher(search_tracks=[_track("t1")])

    result = await fetch_artist_discography_candidates(profile, fetcher, {})

    assert result == []
    fetcher.search.assert_not_called()


async def test_artist_discography_affinity_score_propagated():
    profile = UserProfile(artist_affinities={"a1": 0.7})
    fetcher = _make_fetcher(search_tracks=[_track("t1")])

    result = await fetch_artist_discography_candidates(profile, fetcher, {"a1": "Artist One"})

    assert result[0].artist_affinity_score == pytest.approx(0.7)


async def test_artist_discography_top_n_artists_selected():
    affinities = {f"artist{i}": float(i) / 100 for i in range(15)}
    names = {f"artist{i}": f"Name {i}" for i in range(15)}
    profile = UserProfile(artist_affinities=affinities)
    fetcher = _make_fetcher(search_tracks=[])

    await fetch_artist_discography_candidates(profile, fetcher, names)

    assert fetcher.search.call_count == 10


# ── genre_search source ───────────────────────────────────────────────────────


async def test_genre_search_returns_unknown_tracks():
    profile = UserProfile(
        genre_weights={"pop": 0.8},
        known_track_ids={"known"},
    )
    fetcher = _make_fetcher(search_tracks=[_track("known"), _track("fresh")])

    result = await fetch_genre_search_candidates(profile, fetcher)

    assert len(result) == 1
    assert result[0].track.spotify_id == "fresh"
    assert result[0].source == CandidateSource.genre_search


async def test_genre_search_empty_genre_weights():
    profile = UserProfile()
    fetcher = _make_fetcher()

    result = await fetch_genre_search_candidates(profile, fetcher)

    assert result == []
    fetcher.search.assert_not_called()


async def test_genre_search_top_5_genres_only():
    genre_weights = {f"genre{i}": float(i) / 10 for i in range(8)}
    profile = UserProfile(genre_weights=genre_weights)
    fetcher = _make_fetcher(search_tracks=[])

    await fetch_genre_search_candidates(profile, fetcher)

    assert fetcher.search.call_count == 5


# ── deduplicator ─────────────────────────────────────────────────────────────


async def test_deduplicator_removes_duplicates(session: AsyncSession):
    t = _track("dup_id")
    candidates = [
        Candidate(track=t, source=CandidateSource.artist_discography),
        Candidate(track=t, source=CandidateSource.genre_search),
    ]

    result = await deduplicate_and_upsert(candidates, session)

    assert len(result) == 1
    assert result[0].track.spotify_id == "dup_id"


async def test_deduplicator_upserts_to_db(session: AsyncSession):
    candidates = [
        Candidate(track=_track("t1"), source=CandidateSource.artist_discography),
        Candidate(track=_track("t2"), source=CandidateSource.genre_search),
    ]

    result = await deduplicate_and_upsert(candidates, session)

    assert len(result) == 2
    from db.repositories.track import TrackRepository

    repo = TrackRepository(session)
    assert await repo.get_by_spotify_id("t1") is not None
    assert await repo.get_by_spotify_id("t2") is not None


async def test_deduplicator_empty_input(session: AsyncSession):
    result = await deduplicate_and_upsert([], session)
    assert result == []


# ── CandidateGenerator ────────────────────────────────────────────────────────


async def test_generator_empty_profile_returns_empty(session: AsyncSession):
    generator = CandidateGenerator()
    profile = UserProfile()
    fetcher = _make_fetcher()

    result = await generator.generate(profile, fetcher, session)

    assert result == []


async def test_generator_no_known_tracks_in_output(session: AsyncSession):
    await _seed_artist(session, "a1", "Artist One")
    profile = UserProfile(
        artist_affinities={"a1": 0.9},
        known_track_ids={"known1"},
    )
    fetcher = _make_fetcher(search_tracks=[_track("known1"), _track("new1")])
    generator = CandidateGenerator()

    result = await generator.generate(profile, fetcher, session)

    ids = {c.track.spotify_id for c in result}
    assert "known1" not in ids
    assert "new1" in ids


async def test_generator_deduplicates_across_sources(session: AsyncSession):
    await _seed_artist(session, "a1", "Artist One")
    shared_track = _track("shared")
    profile = UserProfile(
        artist_affinities={"a1": 0.8},
        genre_weights={"pop": 0.7},
    )
    fetcher = _make_fetcher(search_tracks=[shared_track])
    generator = CandidateGenerator()

    result = await generator.generate(profile, fetcher, session)

    ids = [c.track.spotify_id for c in result]
    assert ids.count("shared") == 1


async def test_generator_respects_total_cap(session: AsyncSession):
    await _seed_artist(session, "a1", "Artist One")
    profile = UserProfile(artist_affinities={"a1": 1.0})
    many_tracks = [_track(f"t{i}") for i in range(600)]
    fetcher = _make_fetcher(search_tracks=many_tracks)
    generator = CandidateGenerator()

    result = await generator.generate(profile, fetcher, session)

    assert len(result) <= 500


async def test_generator_skips_artists_not_in_db(session: AsyncSession):
    profile = UserProfile(artist_affinities={"unknown_id": 0.9})
    fetcher = _make_fetcher(search_tracks=[_track("t1")])
    generator = CandidateGenerator()

    result = await generator.generate(profile, fetcher, session)

    assert result == []
    fetcher.search.assert_not_called()
