import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from db.models import Playlist, PlaylistTrack


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

    async def get_by_id_with_tracks(self, playlist_id: str) -> Playlist | None:
        result = await self._session.execute(
            select(Playlist)
            .where(Playlist.id == playlist_id)
            .options(selectinload(Playlist.tracks).selectinload(PlaylistTrack.track))
        )
        return result.scalar_one_or_none()

    async def get_history(self) -> list[Playlist]:
        result = await self._session.execute(select(Playlist).order_by(Playlist.created_at.desc()))
        return list(result.scalars().all())

    async def update_export(
        self,
        playlist_id: str,
        *,
        spotify_playlist_id: str,
        spotify_url: str,
    ) -> None:
        result = await self._session.execute(select(Playlist).where(Playlist.id == playlist_id))
        playlist = result.scalar_one_or_none()
        if playlist is None:
            return
        playlist.spotify_playlist_id = spotify_playlist_id
        playlist.spotify_url = spotify_url
        playlist.exported_at = datetime.utcnow()
        await self._session.commit()
