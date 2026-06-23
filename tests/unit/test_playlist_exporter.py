"""Unit tests for libs/playlist/exporter.py."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from db.models import Base, Playlist
from libs.common.enums import CandidateSource, PlaylistMode
from libs.common.models import Candidate, GeneratedPlaylist, RankedTrack, Track
from libs.playlist.exporter import export_to_spotify
from libs.spotify.fetcher import SpotifyFetcher


def _track(spotify_id: str) -> Track:
    return Track(
        spotify_id=spotify_id,
        title="Song",
        artist_name="Artist",
        album_title="Album",
        duration_ms=180_000,
        popularity=60,
    )


def _ranked(spotify_id: str) -> RankedTrack:
    return RankedTrack(
        candidate=Candidate(
            track=_track(spotify_id),
            source=CandidateSource.artist_discography,
            artist_affinity_score=0.8,
        ),
        final_score=0.9,
        score_breakdown={"two_tower": 0.9},
    )


def _make_fetcher(user_id: str = "user1", new_playlist_id: str = "sp_pl_001") -> SpotifyFetcher:
    fetcher = MagicMock(spec=SpotifyFetcher)
    fetcher.get_current_user_id = AsyncMock(return_value=user_id)
    fetcher.create_playlist = AsyncMock(return_value=new_playlist_id)
    fetcher.add_tracks_to_playlist = AsyncMock(return_value=None)
    return fetcher


@pytest.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as s:
        yield s
    await engine.dispose()


@pytest.fixture
async def persisted_playlist(session):
    """A Playlist row already in the DB (as assembler would create)."""
    db_row = Playlist(
        id="pl-001",
        name="Test Playlist",
        mode=PlaylistMode.balanced,
        size=2,
        created_at=datetime.utcnow(),
    )
    session.add(db_row)
    await session.commit()

    return GeneratedPlaylist(
        id="pl-001",
        name="Test Playlist",
        mode=PlaylistMode.balanced,
        tracks=[_ranked("t1"), _ranked("t2")],
        created_at=datetime.utcnow(),
    )


async def test_export_returns_spotify_url(session, persisted_playlist):
    fetcher = _make_fetcher(new_playlist_id="abc123")
    url = await export_to_spotify(persisted_playlist, fetcher, session)
    assert url == "https://open.spotify.com/playlist/abc123"


async def test_export_updates_db_row(session, persisted_playlist):
    fetcher = _make_fetcher(new_playlist_id="sp999")
    await export_to_spotify(persisted_playlist, fetcher, session)

    result = await session.execute(select(Playlist).where(Playlist.id == "pl-001"))
    row = result.scalar_one()
    assert row.spotify_playlist_id == "sp999"
    assert row.spotify_url == "https://open.spotify.com/playlist/sp999"
    assert row.exported_at is not None


async def test_export_calls_create_playlist_with_name(session, persisted_playlist):
    fetcher = _make_fetcher()
    await export_to_spotify(persisted_playlist, fetcher, session)
    fetcher.create_playlist.assert_awaited_once_with("user1", "Test Playlist")


async def test_export_sends_correct_uris(session, persisted_playlist):
    fetcher = _make_fetcher(new_playlist_id="pl_x")
    await export_to_spotify(persisted_playlist, fetcher, session)
    fetcher.add_tracks_to_playlist.assert_awaited_once_with(
        "pl_x", ["spotify:track:t1", "spotify:track:t2"]
    )


async def test_export_idempotent_creates_new_playlist(session, persisted_playlist):
    fetcher = _make_fetcher(new_playlist_id="first")
    await export_to_spotify(persisted_playlist, fetcher, session)

    fetcher2 = _make_fetcher(new_playlist_id="second")
    url2 = await export_to_spotify(persisted_playlist, fetcher2, session)

    assert url2 == "https://open.spotify.com/playlist/second"
    assert fetcher2.create_playlist.await_count == 1


async def test_export_skips_add_tracks_when_empty(session):
    db_row = Playlist(
        id="pl-empty",
        name="Empty",
        mode=PlaylistMode.balanced,
        size=0,
        created_at=datetime.utcnow(),
    )
    session.add(db_row)
    await session.commit()

    empty_playlist = GeneratedPlaylist(
        id="pl-empty",
        name="Empty",
        mode=PlaylistMode.balanced,
        tracks=[],
        created_at=datetime.utcnow(),
    )
    fetcher = _make_fetcher()
    await export_to_spotify(empty_playlist, fetcher, session)
    fetcher.add_tracks_to_playlist.assert_not_awaited()


async def test_export_no_db_row_still_returns_url(session):
    """Export works even if the playlist isn't in the DB (just skips DB update)."""
    orphan = GeneratedPlaylist(
        id="nonexistent",
        name="Orphan",
        mode=PlaylistMode.safe,
        tracks=[_ranked("t9")],
        created_at=datetime.utcnow(),
    )
    fetcher = _make_fetcher(new_playlist_id="orphan_pl")
    url = await export_to_spotify(orphan, fetcher, session)
    assert url == "https://open.spotify.com/playlist/orphan_pl"
