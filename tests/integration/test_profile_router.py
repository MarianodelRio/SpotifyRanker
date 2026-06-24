"""Integration tests for /profile/* endpoints."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from apps.api.config import Settings
from apps.api.main import app
from db.models import Auth, Base, TrackArtist
from db.session import get_db
from libs.common.enums import ImportStatus
from libs.common.models import Artist, Track

# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
async def test_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


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

    from apps.api.config import get_settings

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_settings] = lambda: override_settings

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
async def authed_engine(test_engine):
    """Engine with an authenticated Auth row pre-seeded."""
    factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        session.add(
            Auth(
                spotify_user_id="uid1",
                display_name="Mariano",
                access_token="valid_token",
                refresh_token="ref",
                import_status=ImportStatus.idle,
            )
        )
        await session.commit()
    return test_engine


@pytest.fixture
async def authed_client(authed_engine, override_settings):
    factory = async_sessionmaker(authed_engine, class_=AsyncSession, expire_on_commit=False)

    async def override_db():
        async with factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    from apps.api.config import get_settings

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_settings] = lambda: override_settings

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


# ── Helpers ────────────────────────────────────────────────────────────────────


def _mock_artist(spotify_id: str = "artist_123", name: str = "Test Artist") -> Artist:
    return Artist(
        spotify_id=spotify_id,
        name=name,
        popularity=70,
        genres=["pop", "indie"],
        image_url="https://example.com/img.jpg",
    )


def _mock_track(spotify_id: str, title: str = "Track", popularity: int = 60) -> Track:
    return Track(
        spotify_id=spotify_id,
        title=title,
        artist_name="Test Artist",
        album_title="Test Album",
        duration_ms=210_000,
        popularity=popularity,
        image_url=None,
    )


# ── GET /profile ───────────────────────────────────────────────────────────────


async def test_get_profile_empty_db(client):
    resp = await client.get("/profile")
    assert resp.status_code == 200
    data = resp.json()
    assert "genre_weights" in data
    assert "top_artists" in data
    assert "stats" in data
    assert data["stats"]["total_tracks"] == 0


# ── GET /profile/declared (empty) ─────────────────────────────────────────────


async def test_get_declared_empty(client):
    resp = await client.get("/profile/declared")
    assert resp.status_code == 200
    data = resp.json()
    assert data["artists"] == []
    assert data["playlists"] == []


# ── POST /profile/artist ───────────────────────────────────────────────────────


async def test_declare_artist_unauthenticated(client):
    resp = await client.post("/profile/artist", json={"spotify_id": "artist_123"})
    assert resp.status_code == 401


async def test_declare_artist_imports_tracks(authed_client):
    mock_fetcher = MagicMock()
    mock_fetcher.fetch_artist = AsyncMock(return_value=_mock_artist())
    mock_fetcher.fetch_artist_tracks_via_search = AsyncMock(
        return_value=[
            {
                "id": "track_top_1",
                "name": "Top Hit",
                "duration_ms": 200_000,
                "artists": [{"id": "artist_123", "name": "Test Artist"}],
                "album": {
                    "id": "album_1",
                    "name": "Album One",
                    "album_type": "album",
                    "release_date": "2022-05-01",
                    "total_tracks": 2,
                    "images": [{"url": "https://img.example.com/a1.jpg"}],
                },
            },
            {
                "id": "track_other_1",
                "name": "Deep Cut",
                "duration_ms": 180_000,
                "artists": [{"id": "artist_123", "name": "Test Artist"}],
                "album": {
                    "id": "album_1",
                    "name": "Album One",
                    "album_type": "album",
                    "release_date": "2022-05-01",
                    "total_tracks": 2,
                    "images": [{"url": "https://img.example.com/a1.jpg"}],
                },
            },
        ]
    )

    mock_client_instance = AsyncMock()
    mock_client_instance.close = AsyncMock()

    with (
        patch("apps.api.routers.profile_router.SpotifyClient", return_value=mock_client_instance),
        patch("apps.api.routers.profile_router.SpotifyFetcher", return_value=mock_fetcher),
    ):
        resp = await authed_client.post("/profile/artist", json={"spotify_id": "artist_123"})

    assert resp.status_code == 201
    data = resp.json()
    assert data["spotify_id"] == "artist_123"
    assert data["tracks_imported"] == 2


async def test_declare_artist_appears_in_declared_list(authed_client):
    mock_fetcher = MagicMock()
    mock_fetcher.fetch_artist = AsyncMock(return_value=_mock_artist())
    mock_fetcher.fetch_artist_tracks_via_search = AsyncMock(return_value=[])

    mock_client_instance = AsyncMock()
    mock_client_instance.close = AsyncMock()

    with (
        patch("apps.api.routers.profile_router.SpotifyClient", return_value=mock_client_instance),
        patch("apps.api.routers.profile_router.SpotifyFetcher", return_value=mock_fetcher),
    ):
        await authed_client.post("/profile/artist", json={"spotify_id": "artist_123"})

    resp = await authed_client.get("/profile/declared")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["artists"]) == 1
    assert data["artists"][0]["spotify_id"] == "artist_123"
    assert data["artists"][0]["name"] == "Test Artist"


# ── DELETE /profile/artist/{spotify_id} ───────────────────────────────────────


async def test_delete_declared_artist_not_found(authed_client):
    resp = await authed_client.delete("/profile/artist/nonexistent")
    assert resp.status_code == 404


async def test_delete_declared_artist_removes_it(authed_client):
    mock_fetcher = MagicMock()
    mock_fetcher.fetch_artist = AsyncMock(return_value=_mock_artist())
    mock_fetcher.fetch_artist_tracks_via_search = AsyncMock(return_value=[])

    mock_client_instance = AsyncMock()
    mock_client_instance.close = AsyncMock()

    with (
        patch("apps.api.routers.profile_router.SpotifyClient", return_value=mock_client_instance),
        patch("apps.api.routers.profile_router.SpotifyFetcher", return_value=mock_fetcher),
    ):
        await authed_client.post("/profile/artist", json={"spotify_id": "artist_123"})

    resp = await authed_client.delete("/profile/artist/artist_123")
    assert resp.status_code == 204

    declared = await authed_client.get("/profile/declared")
    assert declared.json()["artists"] == []


# ── POST /profile/playlist ─────────────────────────────────────────────────────


async def test_declare_playlist_imports_tracks(authed_client):
    mock_fetcher = MagicMock()
    mock_fetcher.fetch_playlist_info = AsyncMock(
        return_value={"spotify_id": "pl_abc", "name": "My Playlist"}
    )
    mock_fetcher.fetch_playlist_tracks = AsyncMock(
        return_value=[
            _mock_track("track_pl_1"),
            _mock_track("track_pl_2"),
            _mock_track("track_pl_3"),
        ]
    )

    mock_client_instance = AsyncMock()
    mock_client_instance.close = AsyncMock()

    with (
        patch("apps.api.routers.profile_router.SpotifyClient", return_value=mock_client_instance),
        patch("apps.api.routers.profile_router.SpotifyFetcher", return_value=mock_fetcher),
    ):
        resp = await authed_client.post("/profile/playlist", json={"spotify_id": "pl_abc"})

    assert resp.status_code == 201
    data = resp.json()
    assert data["tracks_imported"] == 3
    assert data["name"] == "My Playlist"


async def test_declare_playlist_appears_in_declared_list(authed_client):
    mock_fetcher = MagicMock()
    mock_fetcher.fetch_playlist_info = AsyncMock(
        return_value={"spotify_id": "pl_abc", "name": "My Playlist"}
    )
    mock_fetcher.fetch_playlist_tracks = AsyncMock(return_value=[])

    mock_client_instance = AsyncMock()
    mock_client_instance.close = AsyncMock()

    with (
        patch("apps.api.routers.profile_router.SpotifyClient", return_value=mock_client_instance),
        patch("apps.api.routers.profile_router.SpotifyFetcher", return_value=mock_fetcher),
    ):
        await authed_client.post("/profile/playlist", json={"spotify_id": "pl_abc"})

    resp = await authed_client.get("/profile/declared")
    data = resp.json()
    assert len(data["playlists"]) == 1
    assert data["playlists"][0]["spotify_id"] == "pl_abc"


# ── declare_artist: track_artists linking ─────────────────────────────────────


async def test_declare_artist_creates_track_artist_links(authed_engine, override_settings):
    """Tracks fetched for a declared artist must be linked in track_artists."""
    factory = async_sessionmaker(authed_engine, class_=AsyncSession, expire_on_commit=False)

    async def override_db():
        async with factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    from apps.api.config import get_settings

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_settings] = lambda: override_settings

    mock_fetcher = MagicMock()
    mock_fetcher.fetch_artist = AsyncMock(return_value=_mock_artist(spotify_id="artist_123"))
    mock_fetcher.fetch_artist_tracks_via_search = AsyncMock(
        return_value=[
            {
                "id": "track_t1",
                "name": "Hit",
                "duration_ms": 200_000,
                "artists": [
                    {"id": "artist_123", "name": "Test Artist"},
                    {"id": "feat_456", "name": "Featured"},
                ],
                "album": {
                    "id": "album_1",
                    "name": "Album One",
                    "album_type": "album",
                    "release_date": "2022-01-01",
                    "total_tracks": 1,
                    "images": [],
                },
            }
        ]
    )

    mock_client_instance = AsyncMock()
    mock_client_instance.close = AsyncMock()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        with (
            patch(
                "apps.api.routers.profile_router.SpotifyClient",
                return_value=mock_client_instance,
            ),
            patch("apps.api.routers.profile_router.SpotifyFetcher", return_value=mock_fetcher),
        ):
            resp = await ac.post("/profile/artist", json={"spotify_id": "artist_123"})

    app.dependency_overrides.clear()

    assert resp.status_code == 201

    async with factory() as s:
        links = (await s.execute(select(TrackArtist))).scalars().all()

    assert len(links) == 2
    primary_links = [lk for lk in links if lk.is_primary]
    assert len(primary_links) == 1
