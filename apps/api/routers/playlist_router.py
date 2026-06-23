from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import UserTrackData
from db.session import get_db

_MODELS_STORE = Path("models_store")
_USER_TOWER_PATH = _MODELS_STORE / "user_tower.pt"
_ITEM_TOWER_PATH = _MODELS_STORE / "item_tower.pt"

router = APIRouter(prefix="/playlist", tags=["playlist"])


class GenerateRequest(BaseModel):
    mode: str = "balanced"
    size: int = 20


def _model_is_trained() -> bool:
    return _USER_TOWER_PATH.exists() and _ITEM_TOWER_PATH.exists()


@router.post("/generate")
async def generate_playlist(
    body: GenerateRequest,
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> dict[str, Any]:
    if not _model_is_trained():
        raise HTTPException(
            status_code=400,
            detail={
                "error": "model_not_trained",
                "hint": "Trigger training first via POST /model/train, then retry.",
            },
        )

    count_result = await db.execute(select(func.count()).select_from(UserTrackData))
    track_count: int = count_result.scalar_one()
    if track_count == 0:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "empty_library",
                "hint": "Your library is empty. Run POST /import/start to import your Spotify tracks first.",
            },
        )

    # Full pipeline implemented in T-025. Until then, return 501.
    raise HTTPException(status_code=501, detail="Playlist generation pipeline not yet implemented.")
