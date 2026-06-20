import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Artist, TrackArtist, UserTrackData


class ArtistRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, artist_id: str) -> Artist | None:
        result = await self._session.execute(select(Artist).where(Artist.id == artist_id))
        return result.scalar_one_or_none()

    async def get_by_spotify_id(self, spotify_id: str) -> Artist | None:
        result = await self._session.execute(select(Artist).where(Artist.spotify_id == spotify_id))
        return result.scalar_one_or_none()

    async def upsert(
        self,
        *,
        spotify_id: str,
        name: str,
        popularity: int | None = None,
        image_url: str | None = None,
    ) -> str:
        now = datetime.utcnow()
        stmt = (
            insert(Artist)
            .values(
                id=str(uuid.uuid4()),
                spotify_id=spotify_id,
                name=name,
                popularity=popularity,
                image_url=image_url,
                is_blocked=False,
                created_at=now,
                updated_at=now,
            )
            .on_conflict_do_update(
                index_elements=["spotify_id"],
                set_={
                    "name": name,
                    "popularity": popularity,
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

    async def get_top_by_affinity(self, limit: int = 20) -> list[Artist]:
        """Return artists ranked by total play count of their tracks."""
        stmt = (
            select(Artist)
            .join(TrackArtist, TrackArtist.artist_id == Artist.id)
            .join(UserTrackData, UserTrackData.track_id == TrackArtist.track_id)
            .where(Artist.is_blocked.is_(False))
            .group_by(Artist.id)
            .order_by(func.sum(UserTrackData.play_count).desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
