from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from db.models import ArtistGenre, Playlist, PlaylistTrack, TrackArtist, UserTrackData


async def compute_like_rate(session: AsyncSession) -> float | None:
    """Fraction of generated-playlist tracks the user eventually liked.

    Returns None if no generated-playlist tracks exist yet.
    """
    total_result = await session.execute(select(func.count()).select_from(PlaylistTrack))
    total: int = total_result.scalar_one()
    if total == 0:
        return None

    # Tracks in any generated playlist that were later liked
    liked_result = await session.execute(
        select(func.count())
        .select_from(PlaylistTrack)
        .join(UserTrackData, UserTrackData.track_id == PlaylistTrack.track_id)
        .where(UserTrackData.feedback == "like")
    )
    liked: int = liked_result.scalar_one()
    return liked / total


async def compute_diversity_score(session: AsyncSession) -> float | None:
    """Avg distinct artists + distinct genres across the last 5 generated playlists.

    Returns None if no playlists exist.
    """
    playlists_result = await session.execute(
        select(Playlist)
        .order_by(Playlist.created_at.desc())
        .limit(5)
        .options(selectinload(Playlist.tracks))
    )
    playlists = list(playlists_result.scalars().all())
    if not playlists:
        return None

    total_score = 0.0
    for playlist in playlists:
        track_ids = [pt.track_id for pt in playlist.tracks]
        if not track_ids:
            continue

        # Distinct artists
        artist_result = await session.execute(
            select(TrackArtist.artist_id).where(TrackArtist.track_id.in_(track_ids)).distinct()
        )
        distinct_artists = len(artist_result.scalars().all())

        # Distinct genres via artist_genres join
        genre_result = await session.execute(
            select(ArtistGenre.genre_id)
            .join(TrackArtist, TrackArtist.artist_id == ArtistGenre.artist_id)
            .where(TrackArtist.track_id.in_(track_ids))
            .distinct()
        )
        distinct_genres = len(genre_result.scalars().all())

        total_score += distinct_artists + distinct_genres

    return total_score / len(playlists)


def append_loss_history(state: dict[str, Any], new_loss: float, max_n: int = 20) -> dict[str, Any]:
    """Append new_loss to state['loss_history'], keeping at most max_n entries."""
    history: list[float] = state.get("loss_history", [])
    history.append(new_loss)
    if len(history) > max_n:
        history = history[-max_n:]
    state["loss_history"] = history
    return state
