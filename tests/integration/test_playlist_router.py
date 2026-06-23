"""Integration tests for /playlist/* endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from apps.api.config import Settings, get_settings
from apps.api.main import app
from db.models import Auth, Base, Playlist, PlaylistTrack, Track
from db.session import get_db
from libs.common.enums import CandidateSource, ImportStatus, PlaylistMode
from libs.common.models import Candidate, GeneratedPlaylist, RankedTrack, UserProfile
from libs.common.models import Track as TrackModel

# ── Fixtures ──────────────────────────────────────────────────────────────────


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

    settings = Settings(
        SPOTIFY_CLIENT_ID="test_id",
        SPOTIFY_CLIENT_SECRET="test_secret",
        SPOTIFY_REDIRECT_URI="http://localhost:8000/auth/callback",
        DATABASE_URL="sqlite+aiosqlite:///:memory:",
    )

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_settings] = lambda: settings

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


async def _seed_auth(test_engine: object, *, access_token: str = "valid_token") -> None:
    from sqlalchemy.ext.asyncio import async_sessionmaker  # noqa: F811

    factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)  # type: ignore[arg-type]
    async with factory() as session:
        session.add(
            Auth(
                spotify_user_id="uid1",
                display_name="Test User",
                access_token=access_token,
                refresh_token="refresh_token",
                token_expires_at=datetime.utcnow() + timedelta(hours=1),
                import_status=ImportStatus.idle,
            )
        )
        await session.commit()


async def _seed_playlist_with_track(
    test_engine: object,
    *,
    playlist_id: str = "pl-001",
    spotify_url: str | None = None,
    track_spotify_id: str = "spotify_track_abc",
) -> tuple[str, str]:
    """Seed a Playlist + Track + PlaylistTrack. Returns (playlist_id, track_db_id)."""
    from sqlalchemy.ext.asyncio import async_sessionmaker  # noqa: F811

    factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)  # type: ignore[arg-type]
    track_db_id = str(uuid.uuid4())
    async with factory() as session:
        session.add(
            Track(
                id=track_db_id,
                spotify_id=track_spotify_id,
                title="Test Track",
                artist_name="Test Artist",
                album_title="Test Album",
                duration_ms=200000,
                popularity=70,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
        )
        session.add(
            Playlist(
                id=playlist_id,
                name="TasteRanker · balanced · 2026-01-01",
                mode=PlaylistMode.balanced,
                size=1,
                created_at=datetime.utcnow(),
                spotify_url=spotify_url,
            )
        )
        await session.flush()
        session.add(
            PlaylistTrack(
                id=str(uuid.uuid4()),
                playlist_id=playlist_id,
                track_id=track_db_id,
                rank=1,
                final_score=0.85,
                score_breakdown={"two_tower": 0.7, "affinity": 0.15},
            )
        )
        await session.commit()
    return playlist_id, track_db_id


def _make_ranked_track() -> RankedTrack:
    track = TrackModel(
        spotify_id="spotify_track_abc",
        title="Test Track",
        artist_name="Test Artist",
        album_title="Test Album",
        duration_ms=200000,
        popularity=70,
    )
    candidate = Candidate(track=track, source=CandidateSource.artist_discography)
    return RankedTrack(
        candidate=candidate,
        final_score=0.85,
        score_breakdown={"two_tower": 0.7, "affinity": 0.15},
    )


def _make_generated_playlist() -> GeneratedPlaylist:
    return GeneratedPlaylist(
        id="pl-generated",
        name="TasteRanker · balanced · 2026-01-01",
        mode=PlaylistMode.balanced,
        tracks=[_make_ranked_track()],
        created_at=datetime.utcnow(),
    )


# ── POST /playlist/generate ───────────────────────────────────────────────────


async def test_generate_unauthenticated(client):
    with patch("apps.api.routers.playlist_router.load_model"), patch(
        "apps.api.routers.playlist_router.build_profile",
        new_callable=AsyncMock,
        return_value=UserProfile(),
    ):
        resp = await client.post("/playlist/generate", json={"mode": "balanced", "size": 5})
    assert resp.status_code == 401


async def test_generate_model_not_trained(client, test_engine):
    await _seed_auth(test_engine)

    from libs.ml.inference import ModelNotTrainedError

    with patch(
        "apps.api.routers.playlist_router.load_model",
        side_effect=ModelNotTrainedError("Model not trained"),
    ):
        resp = await client.post("/playlist/generate", json={"mode": "balanced", "size": 5})

    assert resp.status_code == 422
    assert "Model not trained" in resp.json()["detail"]


async def test_generate_success(client, test_engine):
    await _seed_auth(test_engine)

    generated = _make_generated_playlist()

    with patch("apps.api.routers.playlist_router.load_model", return_value=MagicMock()), patch(
        "apps.api.routers.playlist_router.build_profile",
        new_callable=AsyncMock,
        return_value=UserProfile(),
    ):
        mock_gen_instance = MagicMock()
        mock_gen_instance.generate = AsyncMock(return_value=[_make_ranked_track().candidate])
        with patch(
            "apps.api.routers.playlist_router.CandidateGenerator",
            return_value=mock_gen_instance,
        ), patch(
            "apps.api.routers.playlist_router.rank",
            return_value=[_make_ranked_track()],
        ), patch(
            "apps.api.routers.playlist_router.assemble",
            new_callable=AsyncMock,
            return_value=generated,
        ):
            resp = await client.post(
                "/playlist/generate", json={"mode": "balanced", "size": 5}
            )

    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "pl-generated"
    assert data["mode"] == "balanced"
    assert len(data["tracks"]) == 1


async def test_generate_no_candidates(client, test_engine):
    await _seed_auth(test_engine)

    with patch("apps.api.routers.playlist_router.load_model", return_value=MagicMock()), patch(
        "apps.api.routers.playlist_router.build_profile",
        new_callable=AsyncMock,
        return_value=UserProfile(),
    ):
        mock_gen_instance = MagicMock()
        mock_gen_instance.generate = AsyncMock(return_value=[])
        with patch(
            "apps.api.routers.playlist_router.CandidateGenerator",
            return_value=mock_gen_instance,
        ):
            resp = await client.post(
                "/playlist/generate", json={"mode": "balanced", "size": 5}
            )

    assert resp.status_code == 422
    assert "No candidates" in resp.json()["detail"]


# ── GET /playlist/history ─────────────────────────────────────────────────────


async def test_history_empty(client):
    resp = await client.get("/playlist/history")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_history_returns_playlists(client, test_engine):
    await _seed_playlist_with_track(test_engine, playlist_id="pl-001", track_spotify_id="spotify_track_abc")
    await _seed_playlist_with_track(test_engine, playlist_id="pl-002", track_spotify_id="spotify_track_def")

    resp = await client.get("/playlist/history")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    ids = {p["id"] for p in data}
    assert ids == {"pl-001", "pl-002"}


# ── GET /playlist/{id} ────────────────────────────────────────────────────────


async def test_get_playlist_not_found(client):
    resp = await client.get("/playlist/nonexistent-id")
    assert resp.status_code == 404


async def test_get_playlist_returns_detail(client, test_engine):
    await _seed_playlist_with_track(test_engine, playlist_id="pl-001")

    resp = await client.get("/playlist/pl-001")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "pl-001"
    assert data["mode"] == "balanced"
    assert len(data["tracks"]) == 1
    track = data["tracks"][0]
    assert track["rank"] == 1
    assert track["final_score"] == pytest.approx(0.85)
    assert "two_tower" in track["score_breakdown"]
    assert track["track"]["spotify_id"] == "spotify_track_abc"


# ── POST /playlist/{id}/export ────────────────────────────────────────────────


async def test_export_playlist_not_found(client, test_engine):
    await _seed_auth(test_engine)
    resp = await client.post("/playlist/nonexistent-id/export")
    assert resp.status_code == 404


async def test_export_playlist_unauthenticated(client, test_engine):
    await _seed_playlist_with_track(test_engine, playlist_id="pl-001")
    resp = await client.post("/playlist/pl-001/export")
    assert resp.status_code == 401


async def test_export_playlist_success(client, test_engine):
    await _seed_auth(test_engine)
    await _seed_playlist_with_track(test_engine, playlist_id="pl-001")

    mock_fetcher = MagicMock()
    mock_fetcher.get_current_user_id = AsyncMock(return_value="spotify_user_id")
    mock_fetcher.create_playlist = AsyncMock(return_value="new_spotify_playlist_id")
    mock_fetcher.add_tracks_to_playlist = AsyncMock(return_value=None)

    with patch("apps.api.routers.playlist_router.SpotifyFetcher", return_value=mock_fetcher):
        resp = await client.post("/playlist/pl-001/export")

    assert resp.status_code == 200
    data = resp.json()
    assert "spotify_url" in data
    assert "new_spotify_playlist_id" in data["spotify_url"]

    mock_fetcher.create_playlist.assert_called_once()
    mock_fetcher.add_tracks_to_playlist.assert_called_once()
