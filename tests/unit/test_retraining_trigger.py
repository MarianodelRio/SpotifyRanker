"""Tests for libs/feedback/trigger.py using in-memory SQLite."""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import libs.feedback.trigger as trigger_module
from db.models import Base, UserTrackData
from db.repositories import TrackRepository
from libs.common.enums import FeedbackType
from libs.feedback.trigger import RETRAIN_THRESHOLD, _run_retrain, check_and_trigger


@pytest.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as s:
        yield s
    await engine.dispose()


@pytest.fixture
def state_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect _STATE_FILE to a temp path for each test."""
    path = tmp_path / "training_state.json"
    monkeypatch.setattr(trigger_module, "_STATE_FILE", path)
    return path


async def _insert_feedback_rows(session: AsyncSession, count: int) -> None:
    """Insert `count` distinct tracks each with a like feedback."""
    repo = TrackRepository(session)
    now = datetime.utcnow()
    for i in range(count):
        track_id = await repo.upsert(spotify_id=f"sp_{i}", title=f"Track {i}")
        row = UserTrackData(
            track_id=track_id,
            feedback=FeedbackType.like.value,
            feedback_at=now - timedelta(seconds=i),
        )
        session.add(row)
    await session.commit()


# ── below-threshold does not trigger ─────────────────────────────────────────


async def test_no_trigger_below_threshold(session: AsyncSession, state_file: Path) -> None:
    await _insert_feedback_rows(session, RETRAIN_THRESHOLD - 1)
    bt = BackgroundTasks()
    await check_and_trigger(session, bt)
    assert bt.tasks == []


# ── exactly threshold triggers ────────────────────────────────────────────────


async def test_trigger_at_threshold(session: AsyncSession, state_file: Path) -> None:
    await _insert_feedback_rows(session, RETRAIN_THRESHOLD)
    bt = BackgroundTasks()
    await check_and_trigger(session, bt)
    assert len(bt.tasks) == 1


# ── state file marks training_in_progress ────────────────────────────────────


async def test_state_file_written_on_trigger(session: AsyncSession, state_file: Path) -> None:
    await _insert_feedback_rows(session, RETRAIN_THRESHOLD)
    bt = BackgroundTasks()
    await check_and_trigger(session, bt)
    state = json.loads(state_file.read_text())
    assert state["training_in_progress"] is True


# ── debounce: second call while in_progress is ignored ───────────────────────


async def test_debounce_while_in_progress(session: AsyncSession, state_file: Path) -> None:
    state_file.write_text(json.dumps({"last_trained_at": None, "training_in_progress": True}))
    await _insert_feedback_rows(session, RETRAIN_THRESHOLD)
    bt = BackgroundTasks()
    await check_and_trigger(session, bt)
    assert bt.tasks == []


# ── counter resets after training completes ───────────────────────────────────


async def test_counter_resets_after_training(session: AsyncSession, state_file: Path) -> None:
    now = datetime.utcnow()
    state_file.write_text(
        json.dumps(
            {
                "last_trained_at": now.isoformat(),
                "training_in_progress": False,
            }
        )
    )
    repo = TrackRepository(session)
    for i in range(RETRAIN_THRESHOLD):
        track_id = await repo.upsert(spotify_id=f"old_{i}", title=f"Old {i}")
        row = UserTrackData(
            track_id=track_id,
            feedback=FeedbackType.like.value,
            feedback_at=now - timedelta(hours=1),
        )
        session.add(row)
    await session.commit()

    bt = BackgroundTasks()
    await check_and_trigger(session, bt)
    assert bt.tasks == []


# ── above threshold triggers exactly once ────────────────────────────────────


async def test_trigger_exactly_once_above_threshold(
    session: AsyncSession, state_file: Path
) -> None:
    await _insert_feedback_rows(session, RETRAIN_THRESHOLD + 5)
    bt = BackgroundTasks()
    await check_and_trigger(session, bt)
    assert len(bt.tasks) == 1


# ── _run_retrain resets flag on success ──────────────────────────────────────


async def test_run_retrain_resets_flag_on_success(state_file: Path) -> None:
    state_file.write_text(json.dumps({"last_trained_at": None, "training_in_progress": True}))

    mock_db_session = AsyncMock()

    @asynccontextmanager
    async def _fake_session_factory():
        yield mock_db_session

    with (
        patch("libs.feedback.trigger._load_state", side_effect=trigger_module._load_state),
        patch("libs.feedback.trigger._save_state", side_effect=trigger_module._save_state),
        patch("db.engine.AsyncSessionLocal", _fake_session_factory),
        patch("libs.profile.builder.build_profile", AsyncMock(return_value=MagicMock())),
        patch("libs.ml.trainer.train", AsyncMock()),
    ):
        await _run_retrain()

    state = json.loads(state_file.read_text())
    assert state["training_in_progress"] is False
    assert state["last_trained_at"] is not None


# ── _run_retrain resets flag on failure ──────────────────────────────────────


async def test_run_retrain_resets_flag_on_failure(state_file: Path) -> None:
    state_file.write_text(json.dumps({"last_trained_at": None, "training_in_progress": True}))

    mock_db_session = AsyncMock()

    @asynccontextmanager
    async def _fake_session_factory():
        yield mock_db_session

    with (
        patch("db.engine.AsyncSessionLocal", _fake_session_factory),
        patch("libs.profile.builder.build_profile", AsyncMock(return_value=MagicMock())),
        patch("libs.ml.trainer.train", AsyncMock(side_effect=RuntimeError("boom"))),
    ):
        await _run_retrain()

    state = json.loads(state_file.read_text())
    assert state["training_in_progress"] is False
