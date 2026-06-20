import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Album


class AlbumRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_spotify_id(self, spotify_id: str) -> Album | None:
        result = await self._session.execute(select(Album).where(Album.spotify_id == spotify_id))
        return result.scalar_one_or_none()

    async def upsert(
        self,
        *,
        spotify_id: str,
        title: str,
        artist_id: str | None = None,
        release_year: int | None = None,
        total_tracks: int | None = None,
        image_url: str | None = None,
    ) -> str:
        now = datetime.utcnow()
        stmt = (
            insert(Album)
            .values(
                id=str(uuid.uuid4()),
                spotify_id=spotify_id,
                title=title,
                artist_id=artist_id,
                release_year=release_year,
                total_tracks=total_tracks,
                image_url=image_url,
                created_at=now,
                updated_at=now,
            )
            .on_conflict_do_update(
                index_elements=["spotify_id"],
                set_={
                    "title": title,
                    "artist_id": artist_id,
                    "release_year": release_year,
                    "total_tracks": total_tracks,
                    "image_url": image_url,
                    "updated_at": now,
                },
            )
        )
        await self._session.execute(stmt)
        await self._session.commit()
        row = await self.get_by_spotify_id(spotify_id)
        assert row is not None
        return row.id
