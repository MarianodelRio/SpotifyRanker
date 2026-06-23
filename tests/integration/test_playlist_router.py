"""Integration tests for /playlist/* endpoints."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from apps.api.main import app
from db.models import Base, Track, UserTrackData
from db.session import get_db

# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
async def test_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def client(test_engine):
    factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

    async def override_db():
        async with factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


# ── POST /playlist/generate — model not trained ───────────────────────────────


async def test_generate_no_model_returns_400(client: AsyncClient, tmp_path: Path) -> None:
    """Returns 400 with model_not_trained when model files are missing."""
    missing = tmp_path / "user_tower.pt"
    with (
        patch("apps.api.routers.playlist_router._USER_TOWER_PATH", missing),
        patch("apps.api.routers.playlist_router._ITEM_TOWER_PATH", tmp_path / "item_tower.pt"),
    ):
        resp = await client.post("/playlist/generate", json={"mode": "balanced", "size": 20})

    assert resp.status_code == 400
    detail = resp.json()["detail"]
    assert detail["error"] == "model_not_trained"
    assert "hint" in detail
    assert "/model/train" in detail["hint"]


async def test_generate_item_tower_missing_returns_400(client: AsyncClient, tmp_path: Path) -> None:
    """Returns 400 even if only one model file is present."""
    user_tower = tmp_path / "user_tower.pt"
    user_tower.write_bytes(b"fake")
    missing_item = tmp_path / "item_tower.pt"

    with (
        patch("apps.api.routers.playlist_router._USER_TOWER_PATH", user_tower),
        patch("apps.api.routers.playlist_router._ITEM_TOWER_PATH", missing_item),
    ):
        resp = await client.post("/playlist/generate", json={"mode": "balanced", "size": 20})

    assert resp.status_code == 400
    assert resp.json()["detail"]["error"] == "model_not_trained"


# ── POST /playlist/generate — empty library ───────────────────────────────────


async def test_generate_empty_library_returns_400(
    client: AsyncClient, tmp_path: Path, test_engine
) -> None:
    """Returns 400 with empty_library when no tracks in DB (model is present)."""
    user_tower = tmp_path / "user_tower.pt"
    user_tower.write_bytes(b"fake")
    item_tower = tmp_path / "item_tower.pt"
    item_tower.write_bytes(b"fake")

    with (
        patch("apps.api.routers.playlist_router._USER_TOWER_PATH", user_tower),
        patch("apps.api.routers.playlist_router._ITEM_TOWER_PATH", item_tower),
    ):
        resp = await client.post("/playlist/generate", json={"mode": "balanced", "size": 20})

    assert resp.status_code == 400
    detail = resp.json()["detail"]
    assert detail["error"] == "empty_library"
    assert "hint" in detail
    assert "/import/start" in detail["hint"]


async def test_generate_with_tracks_returns_501(
    client: AsyncClient, tmp_path: Path, test_engine
) -> None:
    """With model + library, returns 501 until T-025 implements the pipeline."""
    factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        track = Track(id="t1", spotify_id="sp1", title="A Track", duration_ms=200000, popularity=60)
        session.add(track)
        await session.flush()
        session.add(UserTrackData(track_id="t1", is_saved=True))
        await session.commit()

    user_tower = tmp_path / "user_tower.pt"
    user_tower.write_bytes(b"fake")
    item_tower = tmp_path / "item_tower.pt"
    item_tower.write_bytes(b"fake")

    with (
        patch("apps.api.routers.playlist_router._USER_TOWER_PATH", user_tower),
        patch("apps.api.routers.playlist_router._ITEM_TOWER_PATH", item_tower),
    ):
        resp = await client.post("/playlist/generate", json={"mode": "balanced", "size": 20})

    assert resp.status_code == 501
