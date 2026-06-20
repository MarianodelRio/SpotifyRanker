from datetime import datetime

from sqlalchemy import delete, select, update
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import DeclaredArtist, DeclaredPlaylist, UserTrackData


class DeclaredArtistRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert(
        self,
        *,
        spotify_id: str,
        name: str,
        image_url: str | None,
        track_count: int,
    ) -> None:
        stmt = (
            insert(DeclaredArtist)
            .values(
                spotify_id=spotify_id,
                name=name,
                image_url=image_url,
                track_count=track_count,
                created_at=datetime.utcnow(),
            )
            .on_conflict_do_update(
                index_elements=["spotify_id"],
                set_={"name": name, "image_url": image_url, "track_count": track_count},
            )
        )
        await self._session.execute(stmt)
        await self._session.commit()

    async def get(self, spotify_id: str) -> DeclaredArtist | None:
        result = await self._session.execute(
            select(DeclaredArtist).where(DeclaredArtist.spotify_id == spotify_id)
        )
        return result.scalar_one_or_none()

    async def get_all(self) -> list[DeclaredArtist]:
        result = await self._session.execute(select(DeclaredArtist))
        return list(result.scalars().all())

    async def delete(self, spotify_id: str) -> None:
        await self._session.execute(
            update(UserTrackData)
            .where(UserTrackData.declared_artist_spotify_id == spotify_id)
            .values(
                declared_artist_label=None,
                declared_artist_weight=None,
                declared_artist_spotify_id=None,
            )
        )
        await self._session.execute(
            delete(DeclaredArtist).where(DeclaredArtist.spotify_id == spotify_id)
        )
        await self._session.commit()


class DeclaredPlaylistRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert(
        self,
        *,
        spotify_id: str,
        name: str,
        track_count: int,
    ) -> None:
        stmt = (
            insert(DeclaredPlaylist)
            .values(
                spotify_id=spotify_id,
                name=name,
                track_count=track_count,
                created_at=datetime.utcnow(),
            )
            .on_conflict_do_update(
                index_elements=["spotify_id"],
                set_={"name": name, "track_count": track_count},
            )
        )
        await self._session.execute(stmt)
        await self._session.commit()

    async def get_all(self) -> list[DeclaredPlaylist]:
        result = await self._session.execute(select(DeclaredPlaylist))
        return list(result.scalars().all())
