from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Playlist
from libs.common.models import GeneratedPlaylist
from libs.spotify.fetcher import SpotifyFetcher


async def export_to_spotify(
    playlist: GeneratedPlaylist,
    fetcher: SpotifyFetcher,
    session: AsyncSession,
) -> str:
    user_id = await fetcher.get_current_user_id()
    spotify_playlist_id = await fetcher.create_playlist(user_id, playlist.name)

    track_uris = [f"spotify:track:{rt.candidate.track.spotify_id}" for rt in playlist.tracks]
    if track_uris:
        await fetcher.add_tracks_to_playlist(spotify_playlist_id, track_uris)

    spotify_url = f"https://open.spotify.com/playlist/{spotify_playlist_id}"

    result = await session.execute(select(Playlist).where(Playlist.id == playlist.id))
    db_playlist = result.scalar_one_or_none()
    if db_playlist is not None:
        db_playlist.spotify_playlist_id = spotify_playlist_id
        db_playlist.spotify_url = spotify_url
        db_playlist.exported_at = datetime.utcnow()
        await session.commit()

    return spotify_url
