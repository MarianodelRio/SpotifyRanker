from __future__ import annotations

from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Auth, Track, UserTrackData
from db.session import get_db
from libs.common.models import Artist
from libs.common.models import Track as TrackModel
from libs.spotify.client import SpotifyClient
from libs.spotify.fetcher import SpotifyFetcher

router = APIRouter(tags=["library"])


async def _get_spotify_client(db: AsyncSession) -> SpotifyClient:
    result = await db.execute(select(Auth))
    auth = result.scalars().first()
    if auth is None or auth.access_token is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return SpotifyClient(auth.access_token)


@router.get("/library")
async def library(
    page: int = Query(1, ge=1),  # noqa: B008
    per_page: int = Query(50, ge=1, le=200),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> dict[str, Any]:
    base_filter = or_(
        UserTrackData.is_saved.is_(True),
        UserTrackData.feedback == "like",
    )

    count_stmt = (
        select(func.count())
        .select_from(Track)
        .join(UserTrackData, UserTrackData.track_id == Track.id)
        .where(base_filter)
    )
    total = (await db.execute(count_stmt)).scalar_one()

    offset = (page - 1) * per_page
    stmt = (
        select(Track, UserTrackData)
        .join(UserTrackData, UserTrackData.track_id == Track.id)
        .where(base_filter)
        .order_by(Track.title)
        .offset(offset)
        .limit(per_page)
    )
    result = await db.execute(stmt)
    rows = result.all()

    tracks = []
    for track, user_data in rows:
        tracks.append(
            {
                "spotify_id": track.spotify_id,
                "title": track.title,
                "artist_name": track.artist_name,
                "album_title": track.album_title,
                "image_url": track.image_url,
                "duration_ms": track.duration_ms,
                "popularity": track.popularity,
                "is_saved": user_data.is_saved,
                "feedback": user_data.feedback,
                "top_position_short": user_data.top_position_short,
                "top_position_medium": user_data.top_position_medium,
                "top_position_long": user_data.top_position_long,
            }
        )

    return {"tracks": tracks, "total": total, "page": page, "per_page": per_page}


@router.get("/search")
async def search(
    q: str = Query(..., min_length=1),  # noqa: B008
    type: str = Query("track", pattern="^(track|artist)$"),  # noqa: B008, A002
    limit: int = Query(10, ge=1, le=10),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> dict[str, Any]:
    client = await _get_spotify_client(db)
    fetcher = SpotifyFetcher(client)
    try:
        results = await fetcher.search(q=q, type=type, limit=limit)
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=str(e)) from e
    finally:
        await client.close()

    items: list[dict[str, Any]]
    if type == "track":
        items = [
            {
                "spotify_id": t.spotify_id,
                "title": t.title,
                "artist_name": t.artist_name,
                "album_title": t.album_title,
                "duration_ms": t.duration_ms,
                "popularity": t.popularity,
                "image_url": t.image_url,
            }
            for t in results
            if isinstance(t, TrackModel)
        ]
    else:
        items = [
            {
                "spotify_id": a.spotify_id,
                "name": a.name,
                "popularity": a.popularity,
                "genres": a.genres,
                "image_url": a.image_url,
            }
            for a in results
            if isinstance(a, Artist)
        ]

    return {"tracks": items, "type": type, "count": len(items)}
