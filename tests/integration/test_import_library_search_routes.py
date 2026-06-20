"""Integration tests for /import/*, /library, and /search endpoints."""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from apps.api.config import Settings, get_settings
from apps.api.main import app
from db.models import Auth, Base, Track, UserTrackData
from db.session import get_db
from libs.common.enums import ImportStatus
from libs.common.models import Artist as ArtistModel
from libs.common.models import Track as TrackModel

# ── Test DB fixture ───────────────────────────────────────────────────────────


@pytest.fixture
async def test_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def test_session(test_engine):
    factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session


@pytest.fixture
def override_settings():
    return Settings(
        SPOTIFY_CLIENT_ID="test_client_id",
        SPOTIFY_CLIENT_SECRET="test_client_secret",
        SPOTIFY_REDIRECT_URI="http://localhost:8000/auth/callback",
        DATABASE_URL="sqlite+aiosqlite:///:memory:",
    )


@pytest.fixture
async def client(test_engine, override_settings):
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
    app.dependency_overrides[get_settings] = lambda: override_settings

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


async def _seed_auth(test_engine, *, access_token: str = "valid_token") -> None:
    factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        session.add(
            Auth(
                spotify_user_id="uid1",
                display_name="Alice",
                access_token=access_token,
                refresh_token="ref_token",
                token_expires_at=datetime.utcnow() + timedelta(hours=1),
                import_status=ImportStatus.idle,
            )
        )
        await session.commit()


# ── POST /import/start ────────────────────────────────────────────────────────


async def test_import_start_unauthenticated(client):
    resp = await client.post("/import/start")
    assert resp.status_code == 401


async def test_import_start_launches_background_task(client, test_engine):
    await _seed_auth(test_engine)

    with patch("apps.api.routers.import_router._run_import", new_callable=AsyncMock) as mock_run:
        resp = await client.post("/import/start")

    assert resp.status_code == 200
    data = resp.json()
    assert "started" in data["message"].lower() or "running" in data.get("status", "")
    # Background task was scheduled (called with correct args)
    mock_run.assert_called_once()


async def test_import_start_already_running(client, test_engine):
    factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        session.add(
            Auth(
                spotify_user_id="uid1",
                display_name="Alice",
                access_token="valid_token",
                refresh_token="ref_token",
                token_expires_at=datetime.utcnow() + timedelta(hours=1),
                import_status=ImportStatus.running,
            )
        )
        await session.commit()

    resp = await client.post("/import/start")
    assert resp.status_code == 200
    assert "already running" in resp.json()["message"].lower()


# ── GET /import/status ────────────────────────────────────────────────────────


async def test_import_status_no_auth(client):
    resp = await client.get("/import/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == ImportStatus.idle
    assert data["tracks_imported"] == 0
    assert data["artists_imported"] == 0


async def test_import_status_reflects_auth_row(client, test_engine):
    factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        session.add(
            Auth(
                spotify_user_id="uid1",
                display_name="Alice",
                access_token="valid_token",
                refresh_token="ref_token",
                token_expires_at=datetime.utcnow() + timedelta(hours=1),
                import_status=ImportStatus.completed,
                import_started_at=datetime.utcnow() - timedelta(minutes=1),
                import_completed_at=datetime.utcnow(),
            )
        )
        await session.commit()

    resp = await client.get("/import/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == ImportStatus.completed
    assert data["started_at"] is not None


async def test_import_status_counts_user_track_data(client, test_engine):
    await _seed_auth(test_engine)

    factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        track = Track(id="t1", spotify_id="sp1", title="Track 1", duration_ms=200000, popularity=70)
        session.add(track)
        await session.flush()
        session.add(UserTrackData(track_id="t1", is_saved=True))
        await session.commit()

    resp = await client.get("/import/status")
    assert resp.status_code == 200
    assert resp.json()["tracks_imported"] == 1


# ── GET /library ──────────────────────────────────────────────────────────────


async def test_library_unauthenticated_returns_empty(client):
    # /library reads from DB — unauthenticated users just get empty results
    resp = await client.get("/library")
    assert resp.status_code == 200
    assert resp.json()["tracks"] == []


async def test_library_returns_saved_tracks(client, test_engine):
    await _seed_auth(test_engine)

    factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        track = Track(
            id="t1", spotify_id="sp1", title="Saved Track", duration_ms=180000, popularity=60
        )
        session.add(track)
        await session.flush()
        session.add(UserTrackData(track_id="t1", is_saved=True))
        await session.commit()

    resp = await client.get("/library")
    assert resp.status_code == 200
    tracks = resp.json()["tracks"]
    assert len(tracks) == 1
    assert tracks[0]["spotify_id"] == "sp1"
    assert tracks[0]["is_saved"] is True


async def test_library_returns_liked_tracks(client, test_engine):
    await _seed_auth(test_engine)

    factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        track = Track(
            id="t2", spotify_id="sp2", title="Liked Track", duration_ms=210000, popularity=55
        )
        session.add(track)
        await session.flush()
        session.add(UserTrackData(track_id="t2", is_saved=False, feedback="like"))
        await session.commit()

    resp = await client.get("/library")
    assert resp.status_code == 200
    tracks = resp.json()["tracks"]
    assert len(tracks) == 1
    assert tracks[0]["feedback"] == "like"


async def test_library_excludes_disliked_unsaved_tracks(client, test_engine):
    await _seed_auth(test_engine)

    factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        track = Track(
            id="t3", spotify_id="sp3", title="Disliked Track", duration_ms=190000, popularity=40
        )
        session.add(track)
        await session.flush()
        session.add(UserTrackData(track_id="t3", is_saved=False, feedback="dislike"))
        await session.commit()

    resp = await client.get("/library")
    assert resp.status_code == 200
    assert resp.json()["tracks"] == []


async def test_library_pagination(client, test_engine):
    await _seed_auth(test_engine)

    factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        for i in range(5):
            track = Track(
                id=f"t{i}",
                spotify_id=f"sp{i}",
                title=f"Track {i}",
                duration_ms=180000,
                popularity=50,
            )
            session.add(track)
            await session.flush()
            session.add(UserTrackData(track_id=f"t{i}", is_saved=True))
        await session.commit()

    resp = await client.get("/library?offset=0&limit=3")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["tracks"]) == 3
    assert data["limit"] == 3
    assert data["offset"] == 0

    resp2 = await client.get("/library?offset=3&limit=3")
    assert resp2.status_code == 200
    assert len(resp2.json()["tracks"]) == 2


# ── GET /search ───────────────────────────────────────────────────────────────


async def test_search_unauthenticated(client):
    resp = await client.get("/search?q=radiohead")
    assert resp.status_code == 401


async def test_search_returns_tracks(client, test_engine):
    await _seed_auth(test_engine)

    mock_tracks = [
        TrackModel(
            spotify_id="sp1",
            title="Creep",
            artist_name="Radiohead",
            album_title="Pablo Honey",
            duration_ms=238000,
            popularity=85,
            image_url=None,
        )
    ]

    with patch(
        "apps.api.routers.library_router.SpotifyFetcher.search",
        new_callable=AsyncMock,
        return_value=mock_tracks,
    ):
        resp = await client.get("/search?q=radiohead&type=track")

    assert resp.status_code == 200
    data = resp.json()
    assert data["type"] == "track"
    assert len(data["results"]) == 1
    assert data["results"][0]["title"] == "Creep"
    assert data["results"][0]["artist_name"] == "Radiohead"


async def test_search_returns_artists(client, test_engine):
    await _seed_auth(test_engine)

    mock_artists = [
        ArtistModel(
            spotify_id="artist1",
            name="Radiohead",
            popularity=90,
            genres=["alternative rock", "art rock"],
            image_url=None,
        )
    ]

    with patch(
        "apps.api.routers.library_router.SpotifyFetcher.search",
        new_callable=AsyncMock,
        return_value=mock_artists,
    ):
        resp = await client.get("/search?q=radiohead&type=artist")

    assert resp.status_code == 200
    data = resp.json()
    assert data["type"] == "artist"
    assert data["results"][0]["name"] == "Radiohead"
    assert "alternative rock" in data["results"][0]["genres"]


async def test_search_invalid_type(client, test_engine):
    await _seed_auth(test_engine)
    resp = await client.get("/search?q=test&type=album")
    assert resp.status_code == 422


async def test_search_empty_query(client, test_engine):
    await _seed_auth(test_engine)
    resp = await client.get("/search?q=")
    assert resp.status_code == 422


async def test_search_does_not_write_to_db(client, test_engine):
    await _seed_auth(test_engine)

    mock_tracks = [
        TrackModel(
            spotify_id="external_track",
            title="External",
            artist_name="Someone",
            album_title="Album",
            duration_ms=200000,
            popularity=50,
            image_url=None,
        )
    ]

    with patch(
        "apps.api.routers.library_router.SpotifyFetcher.search",
        new_callable=AsyncMock,
        return_value=mock_tracks,
    ):
        await client.get("/search?q=external&type=track")

    # DB should have no tracks from search
    factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        from sqlalchemy import func, select

        result = await session.execute(select(func.count()).select_from(Track))
        count = result.scalar_one()
    assert count == 0
