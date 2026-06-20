from __future__ import annotations

from typing import Any

from libs.common.models import Artist, Track
from libs.spotify.client import SpotifyClient

_TIME_RANGES = ("short_term", "medium_term", "long_term")


class SpotifyFetcher:
    """Fetches Spotify data and maps responses to domain models."""

    def __init__(self, client: SpotifyClient) -> None:
        self._client = client

    # ── Saved tracks ─────────────────────────────────────────────────────────

    async def fetch_saved_tracks(self) -> list[Track]:
        items = await self._client.get_paginated("/me/tracks", limit=50)
        return [_parse_saved_track(item) for item in items if item]

    # ── Top tracks ────────────────────────────────────────────────────────────

    async def fetch_top_tracks(self, time_range: str = "medium_term") -> list[Track]:
        if time_range not in _TIME_RANGES:
            raise ValueError(f"time_range must be one of {_TIME_RANGES}")
        items = await self._client.get_paginated("/me/top/tracks", time_range=time_range, limit=50)
        return [_parse_track(item) for item in items if item]

    # ── Top artists ───────────────────────────────────────────────────────────

    async def fetch_top_artists(self, time_range: str = "medium_term") -> list[Artist]:
        if time_range not in _TIME_RANGES:
            raise ValueError(f"time_range must be one of {_TIME_RANGES}")
        items = await self._client.get_paginated("/me/top/artists", time_range=time_range, limit=50)
        return [_parse_artist(item) for item in items if item]

    # ── Artist metadata ───────────────────────────────────────────────────────

    async def fetch_artist(self, artist_id: str) -> Artist:
        data = await self._client.get(f"/artists/{artist_id}")
        return _parse_artist(data)

    async def fetch_artist_top_tracks(self, artist_id: str) -> list[Track]:
        data = await self._client.get(f"/artists/{artist_id}/top-tracks", market="from_token")
        return [_parse_track(item) for item in data.get("tracks", []) if item]

    # ── Playlist metadata ─────────────────────────────────────────────────────

    async def fetch_playlist_info(self, playlist_id: str) -> dict[str, Any]:
        data = await self._client.get(f"/playlists/{playlist_id}", fields="id,name")
        return {"spotify_id": data.get("id", playlist_id), "name": data.get("name", "")}

    # ── Artist albums ─────────────────────────────────────────────────────────

    async def fetch_artist_albums(self, artist_id: str) -> list[dict[str, Any]]:
        items = await self._client.get_paginated(
            f"/artists/{artist_id}/albums",
            include_groups="album,single",
            limit=50,
        )
        return items

    # ── Album tracks ──────────────────────────────────────────────────────────

    async def fetch_album_tracks(self, album_id: str) -> list[Track]:
        album_data = await self._client.get(f"/albums/{album_id}")
        album_title = album_data.get("name", "")
        image_url = _extract_image(album_data.get("images", []))

        items = await self._client.get_paginated(f"/albums/{album_id}/tracks", limit=50)
        tracks: list[Track] = []
        for item in items:
            if not item:
                continue
            artists = item.get("artists", [])
            artist_name = artists[0]["name"] if artists else ""
            tracks.append(
                Track(
                    spotify_id=item["id"],
                    title=item["name"],
                    artist_name=artist_name,
                    album_title=album_title,
                    duration_ms=item.get("duration_ms", 0),
                    popularity=item.get("popularity", 0),
                    image_url=image_url,
                )
            )
        return tracks

    # ── Playlist tracks ───────────────────────────────────────────────────────

    async def fetch_playlist_tracks(self, playlist_id: str) -> list[Track]:
        items = await self._client.get_paginated(f"/playlists/{playlist_id}/tracks", limit=100)
        tracks: list[Track] = []
        for item in items:
            if not item:
                continue
            track = item.get("track")
            if track and track.get("id"):
                tracks.append(_parse_track(track))
        return tracks

    # ── Search ────────────────────────────────────────────────────────────────

    async def search(
        self, q: str, type: str = "track", limit: int = 20
    ) -> list[Track] | list[Artist]:
        if type not in ("track", "artist"):
            raise ValueError("type must be 'track' or 'artist'")

        data = await self._client.get("/search", q=q, type=type, limit=min(limit, 50))

        if type == "track":
            page = data.get("tracks", {})
            return [_parse_track(item) for item in page.get("items", []) if item]
        else:
            page = data.get("artists", {})
            return [_parse_artist(item) for item in page.get("items", []) if item]


# ── Parsers ───────────────────────────────────────────────────────────────────


def _parse_track(raw: dict[str, Any]) -> Track:
    artists = raw.get("artists", [])
    artist_name = artists[0]["name"] if artists else ""
    album = raw.get("album", {})
    album_title = album.get("name", "")
    image_url = _extract_image(album.get("images", []))
    return Track(
        spotify_id=raw["id"],
        title=raw["name"],
        artist_name=artist_name,
        album_title=album_title,
        duration_ms=raw.get("duration_ms", 0),
        popularity=raw.get("popularity", 0),
        image_url=image_url,
    )


def _parse_saved_track(raw: dict[str, Any]) -> Track:
    return _parse_track(raw["track"])


def _parse_artist(raw: dict[str, Any]) -> Artist:
    images = raw.get("images", [])
    return Artist(
        spotify_id=raw["id"],
        name=raw["name"],
        popularity=raw.get("popularity", 0),
        genres=raw.get("genres", []),
        image_url=_extract_image(images),
    )


def _extract_image(images: list[dict[str, Any]]) -> str | None:
    return images[0]["url"] if images else None
