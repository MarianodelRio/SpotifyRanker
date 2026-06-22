from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

from fastapi import BackgroundTasks
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import UserTrackData

logger = logging.getLogger(__name__)

RETRAIN_THRESHOLD = 20
_STATE_FILE = Path("models_store/training_state.json")


def _load_state() -> dict[str, object]:
    if not _STATE_FILE.exists():
        return {"last_trained_at": None, "training_in_progress": False}
    try:
        data: dict[str, object] = json.loads(_STATE_FILE.read_text())
        return data
    except (json.JSONDecodeError, OSError):
        return {"last_trained_at": None, "training_in_progress": False}


def _save_state(state: dict[str, object]) -> None:
    _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    _STATE_FILE.write_text(json.dumps(state, default=str))


async def _count_feedback_since(session: AsyncSession, since: datetime | None) -> int:
    stmt = select(func.count()).select_from(UserTrackData).where(UserTrackData.feedback.isnot(None))
    if since is not None:
        stmt = stmt.where(UserTrackData.feedback_at > since)
    result = await session.execute(stmt)
    return result.scalar() or 0


async def _run_retrain() -> None:
    from db.engine import AsyncSessionLocal
    from libs.ml.trainer import train
    from libs.profile.builder import build_profile

    state = _load_state()
    try:
        async with AsyncSessionLocal() as session:
            profile = await build_profile(session)
            await train(session, profile)
        state["last_trained_at"] = datetime.utcnow().isoformat()
        logger.info("Retraining completed successfully.")
    except Exception:
        logger.exception("Retraining failed.")
    finally:
        state["training_in_progress"] = False
        _save_state(state)


async def check_and_trigger(session: AsyncSession, background_tasks: BackgroundTasks) -> None:
    state = _load_state()

    if state.get("training_in_progress", False):
        return

    last_trained_str = state.get("last_trained_at")
    last_trained: datetime | None = (
        datetime.fromisoformat(str(last_trained_str)) if last_trained_str else None
    )

    count = await _count_feedback_since(session, last_trained)
    if count < RETRAIN_THRESHOLD:
        return

    state["training_in_progress"] = True
    _save_state(state)

    background_tasks.add_task(_run_retrain)
    logger.info("Retraining triggered after %d feedback events.", count)
