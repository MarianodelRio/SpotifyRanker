from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel

logger = logging.getLogger(__name__)

_STATE_FILE = Path("models_store/training_state.json")

router = APIRouter(prefix="/model", tags=["model"])


class TrainResponse(BaseModel):
    status: str


class ModelStatus(BaseModel):
    trained_at: datetime | None
    examples_count: int
    training_in_progress: bool
    last_loss: float | None


def _load_state() -> dict[str, Any]:
    if not _STATE_FILE.exists():
        return {
            "last_trained_at": None,
            "training_in_progress": False,
            "examples_count": 0,
            "last_loss": None,
        }
    try:
        data: dict[str, Any] = json.loads(_STATE_FILE.read_text())
        return data
    except (json.JSONDecodeError, OSError):
        return {
            "last_trained_at": None,
            "training_in_progress": False,
            "examples_count": 0,
            "last_loss": None,
        }


def _save_state(state: dict[str, Any]) -> None:
    _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    _STATE_FILE.write_text(json.dumps(state, default=str))


async def _run_manual_retrain() -> None:
    from db.engine import AsyncSessionLocal
    from libs.ml.trainer import train
    from libs.profile.builder import build_profile

    state = _load_state()
    try:
        async with AsyncSessionLocal() as session:
            profile = await build_profile(session)
            result = await train(session, profile)
        state["last_trained_at"] = result.trained_at.isoformat()
        state["examples_count"] = result.examples_count
        state["last_loss"] = result.final_loss
        logger.info(
            "Manual retraining completed: loss=%.4f, examples=%d",
            result.final_loss,
            result.examples_count,
        )
    except Exception:
        logger.exception("Manual retraining failed.")
    finally:
        state["training_in_progress"] = False
        _save_state(state)


@router.post("/train", response_model=TrainResponse)
async def trigger_training(background_tasks: BackgroundTasks) -> TrainResponse:
    state = _load_state()
    if state.get("training_in_progress", False):
        return TrainResponse(status="already_running")
    state["training_in_progress"] = True
    _save_state(state)
    background_tasks.add_task(_run_manual_retrain)
    return TrainResponse(status="started")


@router.get("/status", response_model=ModelStatus)
async def get_model_status() -> ModelStatus:
    state = _load_state()
    trained_at_raw = state.get("last_trained_at")
    trained_at: datetime | None = (
        datetime.fromisoformat(str(trained_at_raw)) if trained_at_raw else None
    )
    last_loss_raw = state.get("last_loss")
    last_loss: float | None = float(last_loss_raw) if last_loss_raw is not None else None
    return ModelStatus(
        trained_at=trained_at,
        examples_count=int(state.get("examples_count", 0)),
        training_in_progress=bool(state.get("training_in_progress", False)),
        last_loss=last_loss,
    )
