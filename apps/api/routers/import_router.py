from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.config import Settings, get_settings
from db.engine import AsyncSessionLocal
from db.models import Artist, ArtistGenre, Auth, UserTrackData
from db.repositories import (
    ArtistRepository,
    AuthRepository,
    GenreRepository,
    TrackRepository,
    UserTrackDataRepository,
)
from db.session import get_db
from libs.common.enums import ImportStatus, SaveSource
from libs.spotify.auth import refresh_access_token
from libs.spotify.client import SpotifyClient
from libs.spotify.fetcher import SpotifyFetcher

router = APIRouter(prefix="/import", tags=["import"])


async def _run_import(
    spotify_user_id: str,
    access_token: str,
    refresh_token: str | None,
    client_id: str,
) -> None:
    async with AsyncSessionLocal() as session:
        auth_repo = AuthRepository(session)
        await auth_repo.update_import_status(
            spotify_user_id,
            ImportStatus.running,
            started_at=datetime.utcnow(),
        )

    async def refresh_fn() -> str:
        if refresh_token is None:
            raise RuntimeError("No refresh token available")
        data = await refresh_access_token(refresh_token, client_id)
        new_token: str = data["access_token"]
        new_refresh_token: str = data.get("refresh_token", refresh_token)
        expires_in: int = data.get("expires_in", 3600)
        async with AsyncSessionLocal() as s:
            await AuthRepository(s).update_token(
                spotify_user_id,
                access_token=new_token,
                refresh_token=new_refresh_token,
                token_expires_at=datetime.utcnow() + timedelta(seconds=expires_in),
            )
        return new_token

    client = SpotifyClient(
        access_token,
        refresh_fn=refresh_fn if refresh_token else None,
    )
    try:
        fetcher = SpotifyFetcher(client)
        async with AsyncSessionLocal() as session:
            track_repo = TrackRepository(session)
            user_data_repo = UserTrackDataRepository(session)
            artist_repo = ArtistRepository(session)
            genre_repo = GenreRepository(session)

            # Fetch and upsert artists with genres
            for time_range in ("short_term", "medium_term", "long_term"):
                artists = await fetcher.fetch_top_artists(time_range)
                for artist in artists:
                    artist_id = await artist_repo.upsert(
                        spotify_id=artist.spotify_id,
                        name=artist.name,
                        popularity=artist.popularity,
                        image_url=artist.image_url,
                    )
                    for genre_name in artist.genres:
                        genre = await genre_repo.get_or_create(genre_name)
                        stmt = (
                            insert(ArtistGenre)
                            .values(artist_id=artist_id, genre_id=genre.id)
                            .on_conflict_do_nothing()
                        )
                        await session.execute(stmt)
                    await session.commit()

            # Stream saved tracks page-by-page so progress is visible immediately
            now = datetime.utcnow()
            async for batch in fetcher.fetch_saved_tracks_paged():
                for track in batch:
                    track_id = await track_repo.upsert(
                        spotify_id=track.spotify_id,
                        title=track.title,
                        duration_ms=track.duration_ms,
                        popularity=track.popularity,
                        artist_name=track.artist_name,
                        album_title=track.album_title,
                        image_url=track.image_url,
                    )
                    await user_data_repo.upsert(
                        track_id=track_id,
                        is_saved=True,
                        save_source=SaveSource.spotify.value,
                        saved_at=now,
                    )

            # Stream top tracks page-by-page for each time range
            for time_range in ("short_term", "medium_term", "long_term"):
                async for batch in fetcher.fetch_top_tracks_paged(time_range):
                    for position, track in enumerate(batch, start=1):
                        track_id = await track_repo.upsert(
                            spotify_id=track.spotify_id,
                            title=track.title,
                            duration_ms=track.duration_ms,
                            popularity=track.popularity,
                            artist_name=track.artist_name,
                            album_title=track.album_title,
                            image_url=track.image_url,
                        )
                        if time_range == "short_term":
                            await user_data_repo.upsert(
                                track_id=track_id, top_position_short=position
                            )
                        elif time_range == "medium_term":
                            await user_data_repo.upsert(
                                track_id=track_id, top_position_medium=position
                            )
                        else:
                            await user_data_repo.upsert(
                                track_id=track_id, top_position_long=position
                            )

        async with AsyncSessionLocal() as session:
            auth_repo = AuthRepository(session)
            await auth_repo.update_import_status(
                spotify_user_id,
                ImportStatus.completed,
                completed_at=datetime.utcnow(),
            )

    except Exception:
        async with AsyncSessionLocal() as session:
            await AuthRepository(session).update_import_status(spotify_user_id, ImportStatus.failed)
        raise
    finally:
        await client.close()


@router.post("/start")
async def start_import(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),  # noqa: B008
    settings: Settings = Depends(get_settings),  # noqa: B008
) -> dict[str, Any]:
    result = await db.execute(select(Auth))
    auth = result.scalars().first()
    if auth is None or auth.access_token is None:
        raise HTTPException(status_code=401, detail="Not authenticated")

    if auth.import_status == ImportStatus.running:
        return {"message": "Import already running", "status": ImportStatus.running}

    background_tasks.add_task(
        _run_import,
        spotify_user_id=auth.spotify_user_id,
        access_token=auth.access_token,
        refresh_token=auth.refresh_token,
        client_id=settings.SPOTIFY_CLIENT_ID,
    )
    return {"message": "Import started", "status": ImportStatus.running}


@router.get("/status")
async def import_status(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:  # noqa: B008
    result = await db.execute(select(Auth))
    auth = result.scalars().first()
    if auth is None:
        return {
            "status": ImportStatus.idle,
            "tracks_imported": 0,
            "artists_imported": 0,
            "started_at": None,
        }

    tracks_count_result = await db.execute(select(func.count()).select_from(UserTrackData))
    tracks_imported = tracks_count_result.scalar_one()

    artists_count_result = await db.execute(select(func.count()).select_from(Artist))
    artists_imported = artists_count_result.scalar_one()

    return {
        "status": auth.import_status,
        "tracks_imported": tracks_imported,
        "artists_imported": artists_imported,
        "started_at": auth.import_started_at,
    }
