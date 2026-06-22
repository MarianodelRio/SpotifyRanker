from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator, Callable
from typing import Any

import httpx

_SPOTIFY_API_BASE = "https://api.spotify.com/v1"
_MAX_RETRIES = 3


class SpotifyClient:
    """Async Spotify API client with auth, 401 refresh, and 429 backoff."""

    def __init__(
        self,
        access_token: str,
        refresh_fn: Callable[[], Any] | None = None,
    ) -> None:
        self._access_token = access_token
        self._refresh_fn = refresh_fn
        self._http = httpx.AsyncClient(base_url=_SPOTIFY_API_BASE, timeout=30.0)

    @property
    def access_token(self) -> str:
        return self._access_token

    def _auth_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._access_token}"}

    async def get(self, path: str, **params: Any) -> dict[str, Any]:
        for attempt in range(_MAX_RETRIES + 1):
            resp = await self._http.get(path, headers=self._auth_headers(), params=params)

            if resp.status_code == 401 and self._refresh_fn is not None:
                new_token = await self._refresh_fn()
                self._access_token = new_token
                resp = await self._http.get(path, headers=self._auth_headers(), params=params)
                resp.raise_for_status()
                return resp.json()  # type: ignore[no-any-return]

            if resp.status_code == 429:
                if attempt == _MAX_RETRIES:
                    resp.raise_for_status()
                retry_after = int(resp.headers.get("Retry-After", 1))
                backoff = min(retry_after * (2**attempt), 30)
                await asyncio.sleep(backoff)
                continue

            resp.raise_for_status()
            return resp.json()  # type: ignore[no-any-return]

        resp.raise_for_status()
        return {}  # unreachable but satisfies mypy

    async def get_pages(
        self, path: str, **params: Any
    ) -> AsyncGenerator[list[dict[str, Any]], None]:
        """Yield each page's items list one at a time (streaming alternative to get_paginated)."""
        url: str | None = path
        first = True

        while url is not None:
            if first:
                data = await self.get(url, **params)
                first = False
            else:
                resp = await self._http.get(url, headers=self._auth_headers())
                resp.raise_for_status()
                data = resp.json()

            page = _unwrap_page(data)
            items = [item for item in page.get("items", []) if item]
            if items:
                yield items
            url = page.get("next")

    async def get_paginated(self, path: str, **params: Any) -> list[dict[str, Any]]:
        """Fetch all pages of a cursor-based paginated Spotify endpoint."""
        items: list[dict[str, Any]] = []
        url: str | None = path
        first = True

        while url is not None:
            if first:
                data = await self.get(url, **params)
                first = False
            else:
                # Subsequent pages: url is absolute from Spotify's `next` field
                resp = await self._http.get(url, headers=self._auth_headers())
                resp.raise_for_status()
                data = resp.json()

            # Spotify wraps paged results in a single key (e.g. "items")
            # The top-level object is the page; it may be nested under a key.
            page = _unwrap_page(data)
            items.extend(page.get("items", []))
            url = page.get("next")

        return items

    async def close(self) -> None:
        await self._http.aclose()


def _unwrap_page(data: dict[str, Any]) -> dict[str, Any]:
    """Spotify sometimes nests the page under a single dict key (e.g. tracks, artists)."""
    # If the top-level dict has 'items' or 'next', it's already the page.
    if "items" in data or "next" in data:
        return data
    # Otherwise, try the first dict value that looks like a page.
    for value in data.values():
        if isinstance(value, dict) and ("items" in value or "next" in value):
            return value
    return data
