from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from db.repositories.track import TrackRepository
from libs.common.models import Candidate


async def deduplicate_and_upsert(
    candidates: list[Candidate],
    session: AsyncSession,
) -> list[Candidate]:
    seen: set[str] = set()
    unique: list[Candidate] = []
    for candidate in candidates:
        sid = candidate.track.spotify_id
        if sid not in seen:
            seen.add(sid)
            unique.append(candidate)

    repo = TrackRepository(session)
    for candidate in unique:
        t = candidate.track
        await repo.upsert(
            spotify_id=t.spotify_id,
            title=t.title,
            duration_ms=t.duration_ms,
            popularity=t.popularity,
        )

    return unique
