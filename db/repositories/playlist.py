import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Playlist


class PlaylistRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, *, name: str, mode: str, size: int) -> Playlist:
        playlist = Playlist(
            id=str(uuid.uuid4()),
            name=name,
            mode=mode,
            size=size,
        )
        self._session.add(playlist)
        await self._session.commit()
        return playlist

    async def get_by_id(self, playlist_id: str) -> Playlist | None:
        result = await self._session.execute(select(Playlist).where(Playlist.id == playlist_id))
        return result.scalar_one_or_none()

    async def get_history(self) -> list[Playlist]:
        result = await self._session.execute(select(Playlist).order_by(Playlist.created_at.desc()))
        return list(result.scalars().all())
