from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Playlist, PlaylistTrack
from libs.common.enums import PlaylistMode
from libs.common.models import GeneratedPlaylist, RankedTrack


async def assemble(
    ranked_tracks: list[RankedTrack],
    mode: PlaylistMode,
    size: int,
    session: AsyncSession,
    name: str | None = None,
) -> GeneratedPlaylist:
    selected = ranked_tracks[:size]

    playlist_id = str(uuid.uuid4())
    now = datetime.utcnow()
    playlist_name = name or f"TasteRanker · {mode.value} · {now.strftime('%Y-%m-%d')}"

    db_playlist = Playlist(
        id=playlist_id,
        name=playlist_name,
        mode=mode,
        size=len(selected),
        created_at=now,
    )
    session.add(db_playlist)

    for rank, ranked in enumerate(selected, start=1):
        session.add(
            PlaylistTrack(
                id=str(uuid.uuid4()),
                playlist_id=playlist_id,
                track_id=ranked.candidate.track.spotify_id,
                rank=rank,
                final_score=ranked.final_score,
                score_breakdown=ranked.score_breakdown,
            )
        )

    await session.commit()

    return GeneratedPlaylist(
        id=playlist_id,
        name=playlist_name,
        mode=mode,
        tracks=selected,
        created_at=now,
    )
