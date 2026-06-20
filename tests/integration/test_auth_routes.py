"""Integration tests for GET/POST /auth/* endpoints."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from apps.api.config import Settings
from apps.api.main import app
from db.models import Auth, Base
from db.session import get_db
from libs.common.enums import ImportStatus

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
    """AsyncClient with overridden DB and settings dependencies."""
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

    from apps.api.config import get_settings

    app.dependency_overrides[get_settings] = lambda: override_settings

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


# ── /auth/login ───────────────────────────────────────────────────────────────


async def test_login_redirects_to_spotify(client):
    resp = await client.get("/auth/login", follow_redirects=False)
    assert resp.status_code == 307
    location = resp.headers["location"]
    assert "accounts.spotify.com/authorize" in location
    assert "code_challenge" in location
    assert "state" in location


async def test_login_includes_required_scopes(client):
    resp = await client.get("/auth/login", follow_redirects=False)
    location = resp.headers["location"]
    for scope in ["user-library-read", "user-top-read", "streaming"]:
        assert scope in location


# ── /auth/callback ────────────────────────────────────────────────────────────


def _make_token_mock(access_token="acc123", refresh_token="ref456", expires_in=3600):
    mock = MagicMock()
    mock.json.return_value = {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_in": expires_in,
        "token_type": "Bearer",
    }
    mock.raise_for_status = MagicMock()
    return mock


def _make_me_mock(user_id="user_spotify_id", display_name="Test User"):
    mock = MagicMock()
    mock.json.return_value = {"id": user_id, "display_name": display_name}
    mock.raise_for_status = MagicMock()
    return mock


async def test_callback_stores_tokens_and_redirects(client):
    from urllib.parse import parse_qs, urlparse

    login_resp = await client.get("/auth/login", follow_redirects=False)
    location = login_resp.headers["location"]
    state = parse_qs(urlparse(location).query)["state"][0]

    token_mock = _make_token_mock()
    me_mock = _make_me_mock()

    mock_http = AsyncMock()
    mock_http.__aenter__ = AsyncMock(return_value=mock_http)
    mock_http.__aexit__ = AsyncMock(return_value=False)
    mock_http.post = AsyncMock(return_value=token_mock)
    mock_http.get = AsyncMock(return_value=me_mock)

    with patch("libs.spotify.auth.httpx.AsyncClient", return_value=mock_http):
        resp = await client.get(
            f"/auth/callback?code=auth_code&state={state}",
            follow_redirects=False,
        )

    assert resp.status_code == 307
    assert resp.headers["location"] == "http://localhost:5173"


async def test_callback_bad_state_returns_400(client):
    resp = await client.get("/auth/callback?code=some_code&state=invalid_state")
    assert resp.status_code == 400
    assert "state" in resp.json()["detail"].lower()


# ── /auth/status ──────────────────────────────────────────────────────────────


async def test_status_unauthenticated(client):
    resp = await client.get("/auth/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_authenticated"] is False
    assert data["display_name"] is None


async def test_status_authenticated(client, test_engine):
    factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        session.add(
            Auth(
                spotify_user_id="uid1",
                display_name="Alice",
                access_token="valid_token",
                refresh_token="ref_token",
                token_expires_at=datetime.utcnow() + timedelta(hours=1),
                import_status=ImportStatus.idle,
            )
        )
        await session.commit()

    resp = await client.get("/auth/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_authenticated"] is True
    assert data["display_name"] == "Alice"


# ── /auth/logout ──────────────────────────────────────────────────────────────


async def test_logout_clears_tokens(client, test_engine):
    factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        session.add(
            Auth(
                spotify_user_id="uid1",
                display_name="Alice",
                access_token="valid_token",
                refresh_token="ref_token",
                token_expires_at=datetime.utcnow() + timedelta(hours=1),
                import_status=ImportStatus.idle,
            )
        )
        await session.commit()

    resp = await client.post("/auth/logout")
    assert resp.status_code == 200

    status_resp = await client.get("/auth/status")
    assert status_resp.json()["is_authenticated"] is False


async def test_logout_when_not_logged_in(client):
    resp = await client.post("/auth/logout")
    assert resp.status_code == 200


# ── /auth/token ───────────────────────────────────────────────────────────────


async def test_token_returns_valid_access_token(client, test_engine):
    factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        session.add(
            Auth(
                spotify_user_id="uid1",
                display_name="Alice",
                access_token="current_token",
                refresh_token="ref_token",
                token_expires_at=datetime.utcnow() + timedelta(hours=1),
                import_status=ImportStatus.idle,
            )
        )
        await session.commit()

    resp = await client.get("/auth/token")
    assert resp.status_code == 200
    assert resp.json()["access_token"] == "current_token"


async def test_token_unauthenticated_returns_401(client):
    resp = await client.get("/auth/token")
    assert resp.status_code == 401


async def test_token_auto_refreshes_expired_token(client, test_engine):
    factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        session.add(
            Auth(
                spotify_user_id="uid1",
                display_name="Alice",
                access_token="old_token",
                refresh_token="ref_token",
                token_expires_at=datetime.utcnow() - timedelta(seconds=1),
                import_status=ImportStatus.idle,
            )
        )
        await session.commit()

    mock_response = MagicMock()
    mock_response.json.return_value = {"access_token": "refreshed_token", "expires_in": 3600}
    mock_response.raise_for_status = MagicMock()

    mock_http = AsyncMock()
    mock_http.__aenter__ = AsyncMock(return_value=mock_http)
    mock_http.__aexit__ = AsyncMock(return_value=False)
    mock_http.post = AsyncMock(return_value=mock_response)

    with patch("libs.spotify.auth.httpx.AsyncClient", return_value=mock_http):
        resp = await client.get("/auth/token")

    assert resp.status_code == 200
    assert resp.json()["access_token"] == "refreshed_token"


async def test_token_refresh_failure_returns_401(client, test_engine):
    factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        session.add(
            Auth(
                spotify_user_id="uid1",
                display_name="Alice",
                access_token="old_token",
                refresh_token="bad_ref",
                token_expires_at=datetime.utcnow() - timedelta(seconds=1),
                import_status=ImportStatus.idle,
            )
        )
        await session.commit()

    mock_http = AsyncMock()
    mock_http.__aenter__ = AsyncMock(return_value=mock_http)
    mock_http.__aexit__ = AsyncMock(return_value=False)
    mock_http.post = AsyncMock(side_effect=Exception("Refresh failed"))

    with patch("libs.spotify.auth.httpx.AsyncClient", return_value=mock_http):
        resp = await client.get("/auth/token")

    assert resp.status_code == 401
