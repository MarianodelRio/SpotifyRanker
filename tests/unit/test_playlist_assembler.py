"""Unit tests for libs/playlist/assembler.py."""

import uuid
from datetime import datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from db.models import Base, Playlist, PlaylistTrack
from db.models import Track as DBTrack
from libs.common.enums import CandidateSource, PlaylistMode
from libs.common.models import Candidate, RankedTrack, Track
from libs.playlist.assembler import assemble


def _track(spotify_id: str) -> Track:
    return Track(
        spotify_id=spotify_id,
        title="Song",
        artist_name="Artist",
        album_title="Album",
        duration_ms=180_000,
        popularity=60,
    )


def _ranked(spotify_id: str, score: float = 0.9) -> RankedTrack:
    return RankedTrack(
        candidate=Candidate(
            track=_track(spotify_id),
            source=CandidateSource.artist_discography,
            artist_affinity_score=0.8,
        ),
        final_score=score,
        score_breakdown={"two_tower": score},
    )


async def _seed_db_track(session: AsyncSession, spotify_id: str) -> DBTrack:
    now = datetime.utcnow()
    db_track = DBTrack(
        id=str(uuid.uuid4()),
        spotify_id=spotify_id,
        title="Song",
        artist_name="Artist",
        album_title="Album",
        duration_ms=180_000,
        popularity=60,
        created_at=now,
        updated_at=now,
    )
    session.add(db_track)
    await session.flush()
    return db_track


@pytest.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as s:
        yield s
    await engine.dispose()


async def test_assemble_returns_exactly_size_tracks(session):
    ranked = [_ranked(f"t{i}", score=1.0 - i * 0.01) for i in range(10)]
    playlist = await assemble(ranked, PlaylistMode.balanced, 5, session)
    assert len(playlist.tracks) == 5


async def test_assemble_returns_fewer_when_pool_smaller(session):
    ranked = [_ranked("t1"), _ranked("t2")]
    playlist = await assemble(ranked, PlaylistMode.balanced, 10, session)
    assert len(playlist.tracks) == 2


async def test_assemble_preserves_rank_order(session):
    ranked = [_ranked(f"t{i}", score=1.0 - i * 0.1) for i in range(5)]
    playlist = await assemble(ranked, PlaylistMode.safe, 5, session)
    ids = [rt.candidate.track.spotify_id for rt in playlist.tracks]
    assert ids == ["t0", "t1", "t2", "t3", "t4"]


async def test_assemble_persists_playlist_row(session):
    ranked = [_ranked("ta"), _ranked("tb")]
    playlist = await assemble(ranked, PlaylistMode.adventurous, 2, session)

    from sqlalchemy import select

    result = await session.execute(select(Playlist).where(Playlist.id == playlist.id))
    db_row = result.scalar_one_or_none()
    assert db_row is not None
    assert db_row.size == 2
    assert db_row.mode == PlaylistMode.adventurous


async def test_assemble_persists_playlist_track_rows(session):
    await _seed_db_track(session, "tx")
    await _seed_db_track(session, "ty")
    ranked = [_ranked("tx"), _ranked("ty")]
    playlist = await assemble(ranked, PlaylistMode.balanced, 2, session)

    from sqlalchemy import select

    result = await session.execute(
        select(PlaylistTrack).where(PlaylistTrack.playlist_id == playlist.id)
    )
    rows = list(result.scalars().all())
    assert len(rows) == 2
    ranks = sorted(r.rank for r in rows)
    assert ranks == [1, 2]


async def test_assemble_stores_score_in_track_rows(session):
    await _seed_db_track(session, "ts")
    ranked = [_ranked("ts", score=0.75)]
    playlist = await assemble(ranked, PlaylistMode.balanced, 1, session)

    from sqlalchemy import select

    result = await session.execute(
        select(PlaylistTrack).where(PlaylistTrack.playlist_id == playlist.id)
    )
    row = result.scalar_one()
    assert row.final_score == pytest.approx(0.75)
    assert row.score_breakdown == {"two_tower": 0.75}


async def test_assemble_empty_ranked_list(session):
    playlist = await assemble([], PlaylistMode.balanced, 5, session)
    assert playlist.tracks == []
    assert playlist.mode == PlaylistMode.balanced


async def test_assemble_custom_name(session):
    ranked = [_ranked("t1")]
    playlist = await assemble(ranked, PlaylistMode.safe, 1, session, name="My Custom Playlist")
    assert playlist.name == "My Custom Playlist"
