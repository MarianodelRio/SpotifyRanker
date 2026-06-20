import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Track


class TrackRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, track_id: str) -> Track | None:
        result = await self._session.execute(select(Track).where(Track.id == track_id))
        return result.scalar_one_or_none()

    async def get_by_spotify_id(self, spotify_id: str) -> Track | None:
        result = await self._session.execute(select(Track).where(Track.spotify_id == spotify_id))
        return result.scalar_one_or_none()

    async def upsert(
        self,
        *,
        spotify_id: str,
        title: str,
        album_id: str | None = None,
        duration_ms: int | None = None,
        popularity: int | None = None,
        preview_url: str | None = None,
    ) -> str:
        now = datetime.utcnow()
        stmt = (
            insert(Track)
            .values(
                id=str(uuid.uuid4()),
                spotify_id=spotify_id,
                title=title,
                album_id=album_id,
                duration_ms=duration_ms,
                popularity=popularity,
                preview_url=preview_url,
                created_at=now,
                updated_at=now,
            )
            .on_conflict_do_update(
                index_elements=["spotify_id"],
                set_={
                    "title": title,
                    "album_id": album_id,
                    "duration_ms": duration_ms,
                    "popularity": popularity,
                    "preview_url": preview_url,
                    "updated_at": now,
                },
            )
        )
        await self._session.execute(stmt)
        await self._session.commit()
        row = await self.get_by_spotify_id(spotify_id)
        assert row is not None
        return row.id
