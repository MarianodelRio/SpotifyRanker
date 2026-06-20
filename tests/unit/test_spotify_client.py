"""Unit tests for libs/spotify/client.py — SpotifyClient."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from libs.spotify.client import SpotifyClient, _unwrap_page

# ── Helpers ───────────────────────────────────────────────────────────────────


def _mock_response(status_code: int, json_data: dict) -> MagicMock:
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.headers = {}
    if status_code >= 400:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            message="error", request=MagicMock(), response=resp
        )
    else:
        resp.raise_for_status.return_value = None
    return resp


# ── _unwrap_page ──────────────────────────────────────────────────────────────


def test_unwrap_page_already_flat():
    data = {"items": [1, 2], "next": None}
    assert _unwrap_page(data) is data


def test_unwrap_page_nested():
    inner = {"items": [1], "next": None}
    data = {"tracks": inner}
    assert _unwrap_page(data) is inner


def test_unwrap_page_fallback():
    data = {"foo": "bar"}
    assert _unwrap_page(data) is data


# ── auth header ───────────────────────────────────────────────────────────────


def test_access_token_property():
    client = SpotifyClient("tok_abc")
    assert client.access_token == "tok_abc"


# ── get — happy path ──────────────────────────────────────────────────────────


async def test_get_returns_json_on_200():
    ok_resp = _mock_response(200, {"id": "track_1"})

    client = SpotifyClient("tok")
    with patch.object(client._http, "get", new=AsyncMock(return_value=ok_resp)):
        result = await client.get("/tracks/track_1")

    assert result == {"id": "track_1"}


# ── get — 401 refresh ─────────────────────────────────────────────────────────


async def test_get_refreshes_token_on_401():
    unauthorized = _mock_response(401, {"error": "Unauthorized"})
    unauthorized.raise_for_status.side_effect = None  # don't raise on first 401 check
    ok_resp = _mock_response(200, {"id": "ok"})

    refresh_fn = AsyncMock(return_value="new_token")
    client = SpotifyClient("old_token", refresh_fn=refresh_fn)

    responses = [unauthorized, ok_resp]
    mock_get = AsyncMock(side_effect=responses)
    with patch.object(client._http, "get", new=mock_get):
        result = await client.get("/me")

    refresh_fn.assert_awaited_once()
    assert client.access_token == "new_token"
    assert result == {"id": "ok"}


async def test_get_no_refresh_fn_raises_on_401():
    unauthorized = _mock_response(401, {"error": "Unauthorized"})

    client = SpotifyClient("tok")
    with (
        patch.object(client._http, "get", new=AsyncMock(return_value=unauthorized)),
        pytest.raises(httpx.HTTPStatusError),
    ):
        await client.get("/me")


# ── get — 429 backoff ─────────────────────────────────────────────────────────


async def test_get_retries_on_429_then_succeeds():
    rate_limited = _mock_response(429, {})
    rate_limited.raise_for_status.side_effect = None
    rate_limited.headers = {"Retry-After": "0"}
    ok_resp = _mock_response(200, {"data": "ok"})

    client = SpotifyClient("tok")
    responses = [rate_limited, ok_resp]
    mock_get = AsyncMock(side_effect=responses)

    with (
        patch.object(client._http, "get", new=mock_get),
        patch("libs.spotify.client.asyncio.sleep", new=AsyncMock()),
    ):
        result = await client.get("/tracks/x")

    assert result == {"data": "ok"}
    assert mock_get.call_count == 2


async def test_get_raises_after_max_retries_on_429():
    rate_limited = _mock_response(429, {})
    rate_limited.headers = {"Retry-After": "0"}

    client = SpotifyClient("tok")

    call_count = 0

    async def get_side_effect(*args, **kwargs):  # type: ignore[no-untyped-def]
        nonlocal call_count
        call_count += 1
        r = _mock_response(429, {})
        r.headers = {"Retry-After": "0"}
        if call_count > 3:
            r.raise_for_status.side_effect = httpx.HTTPStatusError(
                "429", request=MagicMock(), response=r
            )
        else:
            r.raise_for_status.side_effect = None
        return r

    with (
        patch.object(client._http, "get", new=AsyncMock(side_effect=get_side_effect)),
        patch("libs.spotify.client.asyncio.sleep", new=AsyncMock()),
        pytest.raises(httpx.HTTPStatusError),
    ):
        await client.get("/tracks/x")


# ── get_paginated ─────────────────────────────────────────────────────────────


async def test_get_paginated_fetches_all_pages():
    page1 = {"items": [{"id": "a"}], "next": "https://api.spotify.com/v1/me/tracks?offset=1"}
    page2 = {"items": [{"id": "b"}], "next": None}

    client = SpotifyClient("tok")

    call_count = 0

    async def fake_get(url, **kwargs):  # type: ignore[no-untyped-def]
        nonlocal call_count
        call_count += 1
        resp = _mock_response(200, page1 if call_count == 1 else page2)
        return resp

    with patch.object(client._http, "get", new=AsyncMock(side_effect=fake_get)):
        items = await client.get_paginated("/me/tracks", limit=1)

    assert len(items) == 2
    assert items[0]["id"] == "a"
    assert items[1]["id"] == "b"


async def test_get_paginated_single_page():
    page = {"items": [{"id": "x"}, {"id": "y"}], "next": None}

    client = SpotifyClient("tok")
    ok_resp = _mock_response(200, page)

    with patch.object(client._http, "get", new=AsyncMock(return_value=ok_resp)):
        items = await client.get_paginated("/me/top/tracks", limit=50)

    assert len(items) == 2


# ── close ─────────────────────────────────────────────────────────────────────


async def test_close_calls_aclose():
    client = SpotifyClient("tok")
    with patch.object(client._http, "aclose", new=AsyncMock()) as mock_close:
        await client.close()
    mock_close.assert_awaited_once()
