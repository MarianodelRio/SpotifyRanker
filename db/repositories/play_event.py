import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import PlayEvent


class PlayEventRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def append(
        self,
        *,
        track_id: str,
        ms_played: int,
        source: str,
        playlist_id: str | None = None,
    ) -> PlayEvent:
        event = PlayEvent(
            id=str(uuid.uuid4()),
            track_id=track_id,
            ms_played=ms_played,
            source=source,
            playlist_id=playlist_id,
            played_at=datetime.utcnow(),
        )
        self._session.add(event)
        await self._session.commit()
        return event

    async def get_for_track(self, track_id: str) -> list[PlayEvent]:
        result = await self._session.execute(
            select(PlayEvent)
            .where(PlayEvent.track_id == track_id)
            .order_by(PlayEvent.played_at.desc())
        )
        return list(result.scalars().all())
