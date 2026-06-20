"""Tests for libs/feedback/processor.py using in-memory SQLite."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from db.models import Base, PlayEvent, UserTrackData
from db.repositories import TrackRepository
from libs.common.enums import FeedbackType, PlaySource
from libs.common.models import FeedbackEntry
from libs.feedback.processor import record_feedback, record_play_event


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
async def track_id(session: AsyncSession) -> str:
    repo = TrackRepository(session)
    return await repo.upsert(spotify_id="sp_track_1", title="Test Track")


# ── record_feedback ───────────────────────────────────────────────────────────


async def test_record_feedback_creates_row(session: AsyncSession, track_id: str) -> None:
    entry = FeedbackEntry(
        track_id=track_id,
        feedback_type=FeedbackType.like,
        source=PlaySource.my_music,
    )
    await record_feedback(entry, session)

    result = await session.get(UserTrackData, track_id)
    assert result is not None
    assert result.feedback == FeedbackType.like.value


async def test_record_feedback_dislike_overwrites_like(
    session: AsyncSession, track_id: str
) -> None:
    like_entry = FeedbackEntry(
        track_id=track_id,
        feedback_type=FeedbackType.like,
        source=PlaySource.my_music,
    )
    await record_feedback(like_entry, session)

    dislike_entry = FeedbackEntry(
        track_id=track_id,
        feedback_type=FeedbackType.dislike,
        source=PlaySource.my_music,
    )
    await record_feedback(dislike_entry, session)

    result = await session.get(UserTrackData, track_id)
    assert result is not None
    assert result.feedback == FeedbackType.dislike.value


async def test_record_feedback_like_overwrites_dislike(
    session: AsyncSession, track_id: str
) -> None:
    await record_feedback(
        FeedbackEntry(
            track_id=track_id,
            feedback_type=FeedbackType.dislike,
            source=PlaySource.discover,
        ),
        session,
    )
    await record_feedback(
        FeedbackEntry(
            track_id=track_id,
            feedback_type=FeedbackType.like,
            source=PlaySource.discover,
        ),
        session,
    )

    result = await session.get(UserTrackData, track_id)
    assert result is not None
    assert result.feedback == FeedbackType.like.value


async def test_record_feedback_sets_feedback_at(session: AsyncSession, track_id: str) -> None:
    entry = FeedbackEntry(
        track_id=track_id,
        feedback_type=FeedbackType.like,
        source=PlaySource.search,
    )
    await record_feedback(entry, session)

    result = await session.get(UserTrackData, track_id)
    assert result is not None
    assert result.feedback_at is not None


# ── record_play_event ─────────────────────────────────────────────────────────


async def test_record_play_event_appends_event(session: AsyncSession, track_id: str) -> None:
    await record_play_event(
        track_id=track_id,
        ms_played=30000,
        source=PlaySource.my_music.value,
        playlist_id=None,
        session=session,
    )

    from sqlalchemy import select

    rows = (
        (await session.execute(select(PlayEvent).where(PlayEvent.track_id == track_id)))
        .scalars()
        .all()
    )
    assert len(rows) == 1
    assert rows[0].ms_played == 30000


async def test_record_play_event_increments_play_count(
    session: AsyncSession, track_id: str
) -> None:
    for _ in range(3):
        await record_play_event(
            track_id=track_id,
            ms_played=10000,
            source=PlaySource.discover.value,
            playlist_id=None,
            session=session,
        )

    result = await session.get(UserTrackData, track_id)
    assert result is not None
    assert result.play_count == 3


async def test_record_play_event_multiple_events_all_stored(
    session: AsyncSession, track_id: str
) -> None:
    durations = [5000, 15000, 30000]
    for ms in durations:
        await record_play_event(
            track_id=track_id,
            ms_played=ms,
            source=PlaySource.my_music.value,
            playlist_id=None,
            session=session,
        )

    from sqlalchemy import select

    rows = (
        (await session.execute(select(PlayEvent).where(PlayEvent.track_id == track_id)))
        .scalars()
        .all()
    )
    assert len(rows) == 3
    stored_durations = {r.ms_played for r in rows}
    assert stored_durations == set(durations)


async def test_record_play_event_updates_last_played_at(
    session: AsyncSession, track_id: str
) -> None:
    await record_play_event(
        track_id=track_id,
        ms_played=20000,
        source=PlaySource.my_music.value,
        playlist_id=None,
        session=session,
    )

    result = await session.get(UserTrackData, track_id)
    assert result is not None
    assert result.last_played_at is not None
