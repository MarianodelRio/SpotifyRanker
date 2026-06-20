from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.dependencies import get_db
from libs.common.enums import FeedbackType, PlaySource
from libs.common.models import FeedbackEntry
from libs.feedback.processor import record_feedback, record_play_event

router = APIRouter()


class FeedbackRequest(BaseModel):
    track_id: str
    feedback_type: FeedbackType
    source: PlaySource
    playlist_id: str | None = None


class PlayEventRequest(BaseModel):
    track_id: str
    ms_played: int
    source: PlaySource
    playlist_id: str | None = None


@router.post("/feedback", status_code=204)
async def post_feedback(
    body: FeedbackRequest,
    session: AsyncSession = Depends(get_db),  # noqa: B008
) -> None:
    entry = FeedbackEntry(
        track_id=body.track_id,
        feedback_type=body.feedback_type,
        source=body.source,
        playlist_id=body.playlist_id,
    )
    await record_feedback(entry, session)


@router.post("/player/event", status_code=204)
async def post_play_event(
    body: PlayEventRequest,
    session: AsyncSession = Depends(get_db),  # noqa: B008
) -> None:
    await record_play_event(
        track_id=body.track_id,
        ms_played=body.ms_played,
        source=body.source.value,
        playlist_id=body.playlist_id,
        session=session,
    )
