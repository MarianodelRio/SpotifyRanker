"""Integration tests for /model/* endpoints."""

import json
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from apps.api.main import app
from db.models import Base
from db.session import get_db

# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
async def client():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def override_db():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
    await engine.dispose()


# ── GET /model/status ─────────────────────────────────────────────────────────


async def test_get_model_status_no_model(client: AsyncClient, tmp_path: Path) -> None:
    """Returns safe defaults when no state file exists."""
    missing = tmp_path / "nonexistent.json"
    with patch("apps.api.routers.model_router._STATE_FILE", missing):
        resp = await client.get("/model/status")

    assert resp.status_code == 200
    body = resp.json()
    assert body["trained_at"] is None
    assert body["examples_count"] == 0
    assert body["training_in_progress"] is False
    assert body["last_loss"] is None
    assert body["like_rate"] is None
    assert body["diversity_score"] is None
    assert body["loss_history"] == []


async def test_get_model_status_with_model(client: AsyncClient, tmp_path: Path) -> None:
    """Returns all fields when state file has full data."""
    trained_at = "2026-01-15T10:30:00"
    state = {
        "last_trained_at": trained_at,
        "training_in_progress": False,
        "examples_count": 250,
        "last_loss": 0.3142,
    }
    state_file = tmp_path / "training_state.json"
    state_file.write_text(json.dumps(state))

    with patch("apps.api.routers.model_router._STATE_FILE", state_file):
        resp = await client.get("/model/status")

    assert resp.status_code == 200
    body = resp.json()
    assert body["trained_at"] == "2026-01-15T10:30:00"
    assert body["examples_count"] == 250
    assert body["training_in_progress"] is False
    assert abs(body["last_loss"] - 0.3142) < 1e-6
    assert body["loss_history"] == []


async def test_get_model_status_training_in_progress(client: AsyncClient, tmp_path: Path) -> None:
    """Reflects training_in_progress flag while training runs."""
    state = {
        "last_trained_at": None,
        "training_in_progress": True,
        "examples_count": 0,
        "last_loss": None,
    }
    state_file = tmp_path / "training_state.json"
    state_file.write_text(json.dumps(state))

    with patch("apps.api.routers.model_router._STATE_FILE", state_file):
        resp = await client.get("/model/status")

    assert resp.status_code == 200
    body = resp.json()
    assert body["training_in_progress"] is True


async def test_get_model_status_corrupt_file(client: AsyncClient, tmp_path: Path) -> None:
    """Returns safe defaults when state file is corrupt."""
    state_file = tmp_path / "training_state.json"
    state_file.write_text("not valid json {{{")

    with patch("apps.api.routers.model_router._STATE_FILE", state_file):
        resp = await client.get("/model/status")

    assert resp.status_code == 200
    body = resp.json()
    assert body["trained_at"] is None
    assert body["examples_count"] == 0
    assert body["training_in_progress"] is False


# ── POST /model/train ─────────────────────────────────────────────────────────


async def test_post_model_train_starts(client: AsyncClient, tmp_path: Path) -> None:
    """Returns {status: started} immediately and sets training_in_progress flag."""
    state_file = tmp_path / "training_state.json"
    state_file.write_text(json.dumps({"training_in_progress": False}))

    with (
        patch("apps.api.routers.model_router._STATE_FILE", state_file),
        patch("apps.api.routers.model_router._run_manual_retrain", new_callable=AsyncMock),
    ):
        resp = await client.post("/model/train")

    assert resp.status_code == 200
    assert resp.json() == {"status": "started"}
    saved = json.loads(state_file.read_text())
    assert saved["training_in_progress"] is True


async def test_post_model_train_already_running(client: AsyncClient, tmp_path: Path) -> None:
    """Returns {status: already_running} and does not queue another task."""
    state_file = tmp_path / "training_state.json"
    state_file.write_text(json.dumps({"training_in_progress": True}))

    with patch("apps.api.routers.model_router._STATE_FILE", state_file):
        resp = await client.post("/model/train")

    assert resp.status_code == 200
    assert resp.json() == {"status": "already_running"}


async def test_post_model_train_no_state_file(client: AsyncClient, tmp_path: Path) -> None:
    """Works when no state file exists yet (first-ever train)."""
    missing = tmp_path / "nonexistent.json"

    with (
        patch("apps.api.routers.model_router._STATE_FILE", missing),
        patch("apps.api.routers.model_router._run_manual_retrain", new_callable=AsyncMock),
    ):
        resp = await client.post("/model/train")

    assert resp.status_code == 200
    assert resp.json() == {"status": "started"}


# ── _run_manual_retrain ───────────────────────────────────────────────────────


async def test_run_manual_retrain_success(tmp_path: Path) -> None:
    """After successful training, state file has all fields updated."""
    from apps.api.routers.model_router import _run_manual_retrain

    state_file = tmp_path / "training_state.json"
    state_file.write_text(json.dumps({"training_in_progress": True}))

    trained_at = datetime(2026, 6, 1, 12, 0, 0)
    mock_result = MagicMock(trained_at=trained_at, examples_count=100, final_loss=0.25)

    mock_train = AsyncMock(return_value=mock_result)
    mock_build_profile = AsyncMock(return_value=MagicMock())
    mock_session = AsyncMock()
    mock_session_ctx = MagicMock()
    mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_ctx.__aexit__ = AsyncMock(return_value=None)
    mock_session_local = MagicMock(return_value=mock_session_ctx)

    with (
        patch("apps.api.routers.model_router._STATE_FILE", state_file),
        patch(
            "apps.api.routers.model_router._load_state",
            return_value=json.loads(state_file.read_text()),
        ),
        patch("apps.api.routers.model_router._save_state") as mock_save,
        patch("db.engine.AsyncSessionLocal", mock_session_local),
        patch("libs.ml.trainer.train", mock_train),
        patch("libs.profile.builder.build_profile", mock_build_profile),
    ):
        await _run_manual_retrain()

    saved_state = mock_save.call_args[0][0]
    assert saved_state["training_in_progress"] is False
    assert saved_state["examples_count"] == 100
    assert abs(saved_state["last_loss"] - 0.25) < 1e-6
    assert saved_state["last_trained_at"] == trained_at.isoformat()


async def test_run_manual_retrain_failure_clears_flag(tmp_path: Path) -> None:
    """On training failure, training_in_progress is reset to False."""
    from apps.api.routers.model_router import _run_manual_retrain

    state_file = tmp_path / "training_state.json"
    initial_state = {"training_in_progress": True, "last_trained_at": None}
    state_file.write_text(json.dumps(initial_state))

    mock_session = AsyncMock()
    mock_session_ctx = MagicMock()
    mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_ctx.__aexit__ = AsyncMock(return_value=None)
    mock_session_local = MagicMock(return_value=mock_session_ctx)

    with (
        patch("apps.api.routers.model_router._STATE_FILE", state_file),
        patch("apps.api.routers.model_router._load_state", return_value=dict(initial_state)),
        patch("apps.api.routers.model_router._save_state") as mock_save,
        patch("db.engine.AsyncSessionLocal", mock_session_local),
        patch("libs.ml.trainer.train", AsyncMock(side_effect=RuntimeError("no data"))),
        patch("libs.profile.builder.build_profile", AsyncMock(return_value=MagicMock())),
    ):
        await _run_manual_retrain()

    saved_state = mock_save.call_args[0][0]
    assert saved_state["training_in_progress"] is False
