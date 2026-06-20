from datetime import datetime

from sqlalchemy import text
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import PlayEvent, UserTrackData
from libs.common.models import FeedbackEntry


async def record_feedback(entry: FeedbackEntry, session: AsyncSession) -> None:
    now = datetime.utcnow()
    stmt = (
        insert(UserTrackData)
        .values(
            track_id=entry.track_id,
            feedback=entry.feedback_type.value,
            feedback_at=now,
        )
        .on_conflict_do_update(
            index_elements=["track_id"],
            set_={
                "feedback": entry.feedback_type.value,
                "feedback_at": now,
            },
        )
    )
    await session.execute(stmt)
    await session.commit()


async def record_play_event(
    track_id: str,
    ms_played: int,
    source: str,
    playlist_id: str | None,
    session: AsyncSession,
) -> None:
    now = datetime.utcnow()

    event = PlayEvent(
        track_id=track_id,
        ms_played=ms_played,
        source=source,
        playlist_id=playlist_id,
        played_at=now,
    )
    session.add(event)

    upsert_stmt = (
        insert(UserTrackData)
        .values(
            track_id=track_id,
            play_count=1,
            last_played_at=now,
        )
        .on_conflict_do_update(
            index_elements=["track_id"],
            set_={
                "play_count": text("user_track_data.play_count + 1"),
                "last_played_at": now,
            },
        )
    )
    await session.execute(upsert_stmt)
    await session.commit()
