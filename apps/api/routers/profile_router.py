from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response

logger = logging.getLogger(__name__)
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.config import Settings, get_settings
from db.engine import AsyncSessionLocal
from db.models import Auth, DeclaredArtist, DeclaredPlaylist, UserTrackData
from db.repositories import (
    AlbumRepository,
    ArtistRepository,
    AuthRepository,
    DeclaredArtistRepository,
    DeclaredPlaylistRepository,
    GenreRepository,
    TrackRepository,
    UserTrackDataRepository,
)
from db.session import get_db
from libs.profile.builder import build_profile
from libs.spotify.auth import refresh_access_token
from libs.spotify.client import SpotifyClient
from libs.spotify.fetcher import SpotifyFetcher

router = APIRouter(prefix="/profile", tags=["profile"])

_ARTIST_POPULAR_LABEL = 0.90
_ARTIST_POPULAR_WEIGHT = 0.8
_ARTIST_REST_LABEL = 0.60
_ARTIST_REST_WEIGHT = 0.6
_PLAYLIST_LABEL = 0.80
_PLAYLIST_WEIGHT = 0.7


class DeclareArtistRequest(BaseModel):
    spotify_id: str


class DeclarePlaylistRequest(BaseModel):
    spotify_id: str


async def _get_spotify_client(db: AsyncSession, settings: Settings) -> SpotifyClient:
    result = await db.execute(select(Auth))
    auth = result.scalars().first()
    if auth is None or auth.access_token is None:
        raise HTTPException(status_code=401, detail="Not authenticated")

    spotify_user_id = auth.spotify_user_id
    refresh_token = auth.refresh_token
    client_id = settings.SPOTIFY_CLIENT_ID

    async def _refresh_fn() -> str:
        if not refresh_token:
            raise RuntimeError("No refresh token available")
        data = await refresh_access_token(refresh_token, client_id)
        new_token: str = data["access_token"]
        new_refresh: str = data.get("refresh_token", refresh_token)
        expires_in: int = data.get("expires_in", 3600)
        async with AsyncSessionLocal() as s:
            await AuthRepository(s).update_token(
                spotify_user_id,
                access_token=new_token,
                refresh_token=new_refresh,
                token_expires_at=datetime.utcnow() + timedelta(seconds=expires_in),
            )
        return new_token

    return SpotifyClient(auth.access_token, refresh_fn=_refresh_fn)


@router.get("")
async def get_profile(session: AsyncSession = Depends(get_db)) -> dict[str, Any]:  # noqa: B008
    profile = await build_profile(session)

    tracks_count = (
        await session.execute(select(func.count()).select_from(UserTrackData))
    ).scalar_one()
    declared_artists_count = (
        await session.execute(select(func.count()).select_from(DeclaredArtist))
    ).scalar_one()
    declared_playlists_count = (
        await session.execute(select(func.count()).select_from(DeclaredPlaylist))
    ).scalar_one()

    top_artists = sorted(profile.artist_affinities.items(), key=lambda x: x[1], reverse=True)[:20]

    return {
        "genre_weights": profile.genre_weights,
        "top_artists": dict(top_artists),
        "stats": {
            "total_tracks": tracks_count,
            "global_like_ratio": profile.global_like_ratio,
            "diversity_score": profile.diversity_score,
            "declared_artists": declared_artists_count,
            "declared_playlists": declared_playlists_count,
        },
    }


@router.post("/artist", status_code=201)
async def declare_artist(
    body: DeclareArtistRequest,
    session: AsyncSession = Depends(get_db),  # noqa: B008
    settings: Settings = Depends(get_settings),  # noqa: B008
) -> dict[str, Any]:
    client = await _get_spotify_client(session, settings)
    try:
        fetcher = SpotifyFetcher(client)

        artist = await fetcher.fetch_artist(body.spotify_id)

        artist_repo = ArtistRepository(session)
        album_repo = AlbumRepository(session)
        track_repo = TrackRepository(session)
        user_data_repo = UserTrackDataRepository(session)
        genre_repo = GenreRepository(session)
        declared_repo = DeclaredArtistRepository(session)

        # Upsert the artist and their genres
        artist_id = await artist_repo.upsert(
            spotify_id=artist.spotify_id,
            name=artist.name,
            popularity=artist.popularity,
            image_url=artist.image_url,
        )
        for genre_name in artist.genres:
            await genre_repo.get_or_create(genre_name)

        # Fetch tracks via search (catalog endpoint /artists/{id}/albums is
        # restricted in Spotify dev mode since Nov 2024).
        raw_tracks = await fetcher.fetch_artist_tracks_via_search(body.spotify_id, artist.name)
        imported_count = 0
        seen_album_ids: dict[str, str] = {}

        for raw_track in raw_tracks:
            album_raw = raw_track.get("album", {})
            album_spotify_id = album_raw.get("id", "")

            if album_spotify_id and album_spotify_id not in seen_album_ids:
                images = album_raw.get("images", [])
                db_album_id = await album_repo.upsert(
                    spotify_id=album_spotify_id,
                    title=album_raw.get("name", ""),
                    artist_id=artist_id,
                    release_year=_extract_year(album_raw.get("release_date", "")),
                    total_tracks=album_raw.get("total_tracks"),
                    image_url=images[0]["url"] if images else None,
                )
                seen_album_ids[album_spotify_id] = db_album_id

            track_artists = raw_track.get("artists", [])
            track_id = await track_repo.upsert(
                spotify_id=raw_track["id"],
                title=raw_track["name"],
                album_id=seen_album_ids.get(album_spotify_id),
                duration_ms=raw_track.get("duration_ms", 0),
                artist_name=track_artists[0]["name"] if track_artists else "",
                album_title=album_raw.get("name", ""),
                image_url=album_raw.get("images", [{}])[0].get("url"),
            )

            is_main_album = album_raw.get("album_type") == "album"
            label = _ARTIST_POPULAR_LABEL if is_main_album else _ARTIST_REST_LABEL
            weight = _ARTIST_POPULAR_WEIGHT if is_main_album else _ARTIST_REST_WEIGHT

            await user_data_repo.upsert(
                track_id=track_id,
                declared_artist_label=label,
                declared_artist_weight=weight,
                declared_artist_spotify_id=body.spotify_id,
            )
            imported_count += 1

        await declared_repo.upsert(
            spotify_id=artist.spotify_id,
            name=artist.name,
            image_url=artist.image_url,
            track_count=imported_count,
        )

        return {
            "spotify_id": artist.spotify_id,
            "name": artist.name,
            "tracks_imported": imported_count,
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("declare_artist failed for %s", body.spotify_id)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        await client.close()


@router.post("/playlist", status_code=201)
async def declare_playlist(
    body: DeclarePlaylistRequest,
    session: AsyncSession = Depends(get_db),  # noqa: B008
    settings: Settings = Depends(get_settings),  # noqa: B008
) -> dict[str, Any]:
    client = await _get_spotify_client(session, settings)
    try:
        fetcher = SpotifyFetcher(client)

        info = await fetcher.fetch_playlist_info(body.spotify_id)
        tracks = await fetcher.fetch_playlist_tracks(body.spotify_id)

        track_repo = TrackRepository(session)
        user_data_repo = UserTrackDataRepository(session)
        declared_repo = DeclaredPlaylistRepository(session)

        for track in tracks:
            track_id = await track_repo.upsert(
                spotify_id=track.spotify_id,
                title=track.title,
                duration_ms=track.duration_ms,
                popularity=track.popularity,
            )
            await user_data_repo.upsert(
                track_id=track_id,
                declared_playlist_label=_PLAYLIST_LABEL,
                declared_playlist_weight=_PLAYLIST_WEIGHT,
            )

        await declared_repo.upsert(
            spotify_id=info["spotify_id"],
            name=info["name"],
            track_count=len(tracks),
        )

        return {
            "spotify_id": info["spotify_id"],
            "name": info["name"],
            "tracks_imported": len(tracks),
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        await client.close()


@router.get("/declared")
async def get_declared(session: AsyncSession = Depends(get_db)) -> dict[str, Any]:  # noqa: B008
    artist_repo = DeclaredArtistRepository(session)
    playlist_repo = DeclaredPlaylistRepository(session)

    artists = await artist_repo.get_all()
    playlists = await playlist_repo.get_all()

    return {
        "artists": [
            {
                "spotify_id": a.spotify_id,
                "name": a.name,
                "image_url": a.image_url,
                "track_count": a.track_count,
                "created_at": a.created_at.isoformat(),
            }
            for a in artists
        ],
        "playlists": [
            {
                "spotify_id": p.spotify_id,
                "name": p.name,
                "track_count": p.track_count,
                "created_at": p.created_at.isoformat(),
            }
            for p in playlists
        ],
    }


@router.delete("/artist/{spotify_id}")
async def remove_declared_artist(
    spotify_id: str,
    session: AsyncSession = Depends(get_db),  # noqa: B008
) -> Response:
    repo = DeclaredArtistRepository(session)
    existing = await repo.get(spotify_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Declared artist not found")
    await repo.delete(spotify_id)
    return Response(status_code=204)


def _extract_year(release_date: str) -> int | None:
    if release_date and len(release_date) >= 4:
        try:
            return int(release_date[:4])
        except ValueError:
            pass
    return None
