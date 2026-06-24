"""Unit tests for edge-case hardening in _run_import."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx

from libs.common.enums import ImportStatus

# ── helpers ──────────────────────────────────────────────────────────────────


def _make_session_local(session: AsyncMock) -> MagicMock:
    """Return a mock AsyncSessionLocal whose context manager yields `session`."""
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=session)
    ctx.__aexit__ = AsyncMock(return_value=None)
    local = MagicMock(return_value=ctx)
    return local


# ── partial import: artist fetch fails, tracks succeed → partial ──────────────


async def test_run_import_partial_when_artist_fetch_fails() -> None:
    """If artist fetch raises, status ends up as `partial` (not failed)."""
    from apps.api.routers.import_router import _run_import

    session = AsyncMock()
    session_local = _make_session_local(session)

    auth_repo = AsyncMock()
    auth_repo.update_import_status = AsyncMock()
    auth_repo.update_token = AsyncMock()

    fetcher = AsyncMock()
    fetcher.fetch_top_artists = AsyncMock(
        side_effect=httpx.HTTPStatusError(
            "503", request=MagicMock(), response=MagicMock(status_code=503)
        )
    )

    async def _empty_paged(*args, **kwargs):
        return
        yield  # pragma: no cover

    fetcher.fetch_saved_tracks_with_artists_paged = MagicMock(return_value=_empty_paged())
    fetcher.fetch_top_tracks_with_artists_paged = MagicMock(return_value=_empty_paged())

    client = AsyncMock()
    client.close = AsyncMock()

    with (
        patch("apps.api.routers.import_router.AsyncSessionLocal", session_local),
        patch("apps.api.routers.import_router.AuthRepository", return_value=auth_repo),
        patch("apps.api.routers.import_router.ArtistRepository", return_value=AsyncMock()),
        patch("apps.api.routers.import_router.GenreRepository", return_value=AsyncMock()),
        patch("apps.api.routers.import_router.TrackRepository", return_value=AsyncMock()),
        patch("apps.api.routers.import_router.UserTrackDataRepository", return_value=AsyncMock()),
        patch("apps.api.routers.import_router.SpotifyClient", return_value=client),
        patch("apps.api.routers.import_router.SpotifyFetcher", return_value=fetcher),
        patch("apps.api.routers.import_router.refresh_access_token", AsyncMock()),
    ):
        await _run_import("user1", "token", "refresh", "client_id")

    status_calls = [c.args[1] for c in auth_repo.update_import_status.call_args_list]
    assert ImportStatus.running in status_calls
    assert ImportStatus.partial in status_calls
    assert ImportStatus.failed not in status_calls


async def test_run_import_failed_when_tracks_also_fail() -> None:
    """If both artist fetch and saved-tracks fetch fail, status is `failed`."""
    from apps.api.routers.import_router import _run_import

    session = AsyncMock()
    session_local = _make_session_local(session)

    auth_repo = AsyncMock()
    auth_repo.update_import_status = AsyncMock()
    auth_repo.update_token = AsyncMock()

    fetcher = AsyncMock()
    fetcher.fetch_top_artists = AsyncMock(side_effect=RuntimeError("500"))
    fetcher.fetch_saved_tracks_with_artists_paged = MagicMock(side_effect=RuntimeError("also failed"))

    client = AsyncMock()
    client.close = AsyncMock()

    with (
        patch("apps.api.routers.import_router.AsyncSessionLocal", session_local),
        patch("apps.api.routers.import_router.AuthRepository", return_value=auth_repo),
        patch("apps.api.routers.import_router.ArtistRepository", return_value=AsyncMock()),
        patch("apps.api.routers.import_router.GenreRepository", return_value=AsyncMock()),
        patch("apps.api.routers.import_router.TrackRepository", return_value=AsyncMock()),
        patch("apps.api.routers.import_router.UserTrackDataRepository", return_value=AsyncMock()),
        patch("apps.api.routers.import_router.SpotifyClient", return_value=client),
        patch("apps.api.routers.import_router.SpotifyFetcher", return_value=fetcher),
        patch("apps.api.routers.import_router.refresh_access_token", AsyncMock()),
    ):
        await _run_import("user1", "token", "refresh", "client_id")

    status_calls = [c.args[1] for c in auth_repo.update_import_status.call_args_list]
    assert ImportStatus.failed in status_calls
    assert ImportStatus.partial not in status_calls
    assert ImportStatus.completed not in status_calls


async def test_run_import_completed_when_all_phases_succeed() -> None:
    """Full success → status is `completed`."""
    from apps.api.routers.import_router import _run_import

    session = AsyncMock()
    session_local = _make_session_local(session)

    auth_repo = AsyncMock()
    auth_repo.update_import_status = AsyncMock()
    auth_repo.update_token = AsyncMock()

    fetcher = AsyncMock()
    fetcher.fetch_top_artists = AsyncMock(return_value=[])

    async def _empty_paged(*args, **kwargs):
        return
        yield  # pragma: no cover

    fetcher.fetch_saved_tracks_with_artists_paged = MagicMock(return_value=_empty_paged())
    fetcher.fetch_top_tracks_with_artists_paged = MagicMock(return_value=_empty_paged())

    client = AsyncMock()
    client.close = AsyncMock()

    with (
        patch("apps.api.routers.import_router.AsyncSessionLocal", session_local),
        patch("apps.api.routers.import_router.AuthRepository", return_value=auth_repo),
        patch("apps.api.routers.import_router.ArtistRepository", return_value=AsyncMock()),
        patch("apps.api.routers.import_router.GenreRepository", return_value=AsyncMock()),
        patch("apps.api.routers.import_router.TrackRepository", return_value=AsyncMock()),
        patch("apps.api.routers.import_router.UserTrackDataRepository", return_value=AsyncMock()),
        patch("apps.api.routers.import_router.SpotifyClient", return_value=client),
        patch("apps.api.routers.import_router.SpotifyFetcher", return_value=fetcher),
        patch("apps.api.routers.import_router.refresh_access_token", AsyncMock()),
    ):
        await _run_import("user1", "token", "refresh", "client_id")

    status_calls = [c.args[1] for c in auth_repo.update_import_status.call_args_list]
    assert ImportStatus.completed in status_calls
    assert ImportStatus.partial not in status_calls
    assert ImportStatus.failed not in status_calls
