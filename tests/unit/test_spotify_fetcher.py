"""Unit tests for libs/spotify/fetcher.py — SpotifyFetcher."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from libs.common.models import Artist, Track
from libs.spotify.client import SpotifyClient
from libs.spotify.fetcher import SpotifyFetcher

# ── Shared fixtures ───────────────────────────────────────────────────────────

_TRACK_RAW = {
    "id": "track_abc",
    "name": "Song A",
    "artists": [{"name": "Artist X"}],
    "album": {"name": "Album Z", "images": [{"url": "http://img.example.com/a.jpg"}]},
    "duration_ms": 180000,
    "popularity": 75,
}

_ARTIST_RAW = {
    "id": "artist_123",
    "name": "Artist X",
    "popularity": 80,
    "genres": ["pop", "indie"],
    "images": [{"url": "http://img.example.com/b.jpg"}],
}

_SAVED_TRACK_RAW = {"track": _TRACK_RAW, "added_at": "2024-01-01T00:00:00Z"}


def _make_client(get_return=None, paginated_return=None):  # type: ignore[no-untyped-def]
    client = MagicMock(spec=SpotifyClient)
    client.get = AsyncMock(return_value=get_return or {})
    client.get_paginated = AsyncMock(return_value=paginated_return or [])
    return client


# ── fetch_saved_tracks ────────────────────────────────────────────────────────


async def test_fetch_saved_tracks_returns_tracks():
    client = _make_client(paginated_return=[_SAVED_TRACK_RAW])
    fetcher = SpotifyFetcher(client)
    result = await fetcher.fetch_saved_tracks()

    assert len(result) == 1
    assert isinstance(result[0], Track)
    assert result[0].spotify_id == "track_abc"
    assert result[0].title == "Song A"
    assert result[0].artist_name == "Artist X"
    assert result[0].album_title == "Album Z"
    assert result[0].image_url == "http://img.example.com/a.jpg"


async def test_fetch_saved_tracks_empty():
    client = _make_client(paginated_return=[])
    fetcher = SpotifyFetcher(client)
    result = await fetcher.fetch_saved_tracks()
    assert result == []


# ── fetch_top_tracks ──────────────────────────────────────────────────────────


async def test_fetch_top_tracks_returns_tracks():
    client = _make_client(paginated_return=[_TRACK_RAW])
    fetcher = SpotifyFetcher(client)
    result = await fetcher.fetch_top_tracks("short_term")

    assert len(result) == 1
    assert isinstance(result[0], Track)
    assert result[0].spotify_id == "track_abc"


async def test_fetch_top_tracks_calls_correct_endpoint():
    client = _make_client(paginated_return=[])
    fetcher = SpotifyFetcher(client)
    await fetcher.fetch_top_tracks("long_term")

    client.get_paginated.assert_awaited_once_with(
        "/me/top/tracks", time_range="long_term", limit=50
    )


async def test_fetch_top_tracks_invalid_time_range():
    client = _make_client()
    fetcher = SpotifyFetcher(client)
    with pytest.raises(ValueError, match="time_range"):
        await fetcher.fetch_top_tracks("invalid_range")


# ── fetch_top_artists ─────────────────────────────────────────────────────────


async def test_fetch_top_artists_returns_artists():
    client = _make_client(paginated_return=[_ARTIST_RAW])
    fetcher = SpotifyFetcher(client)
    result = await fetcher.fetch_top_artists("medium_term")

    assert len(result) == 1
    assert isinstance(result[0], Artist)
    assert result[0].spotify_id == "artist_123"
    assert result[0].name == "Artist X"
    assert result[0].genres == ["pop", "indie"]
    assert result[0].image_url == "http://img.example.com/b.jpg"


async def test_fetch_top_artists_invalid_time_range():
    client = _make_client()
    fetcher = SpotifyFetcher(client)
    with pytest.raises(ValueError, match="time_range"):
        await fetcher.fetch_top_artists("bad_range")


# ── fetch_artist_albums ───────────────────────────────────────────────────────


async def test_fetch_artist_albums_returns_raw_dicts():
    album_raw = {"id": "album_1", "name": "Album One", "album_type": "album"}
    client = _make_client(paginated_return=[album_raw])
    fetcher = SpotifyFetcher(client)
    result = await fetcher.fetch_artist_albums("artist_123")

    assert result == [album_raw]
    client.get_paginated.assert_awaited_once_with(
        "/artists/artist_123/albums",
        include_groups="album,single",
        limit=50,
    )


# ── fetch_album_tracks ────────────────────────────────────────────────────────


async def test_fetch_album_tracks_returns_tracks():
    album_data = {
        "name": "Album Z",
        "images": [{"url": "http://img.example.com/c.jpg"}],
    }
    track_raw = {
        "id": "t1",
        "name": "Track One",
        "artists": [{"name": "Artist Y"}],
        "duration_ms": 200000,
        "popularity": 60,
    }

    client = MagicMock(spec=SpotifyClient)
    client.get = AsyncMock(return_value=album_data)
    client.get_paginated = AsyncMock(return_value=[track_raw])

    fetcher = SpotifyFetcher(client)
    result = await fetcher.fetch_album_tracks("album_xyz")

    assert len(result) == 1
    assert isinstance(result[0], Track)
    assert result[0].spotify_id == "t1"
    assert result[0].album_title == "Album Z"
    assert result[0].image_url == "http://img.example.com/c.jpg"
    assert result[0].artist_name == "Artist Y"


async def test_fetch_album_tracks_no_image():
    album_data = {"name": "Album B", "images": []}
    track_raw = {
        "id": "t2",
        "name": "Track Two",
        "artists": [{"name": "Band"}],
        "duration_ms": 100000,
        "popularity": 30,
    }

    client = MagicMock(spec=SpotifyClient)
    client.get = AsyncMock(return_value=album_data)
    client.get_paginated = AsyncMock(return_value=[track_raw])

    fetcher = SpotifyFetcher(client)
    result = await fetcher.fetch_album_tracks("album_b")

    assert result[0].image_url is None


# ── fetch_playlist_tracks ─────────────────────────────────────────────────────


async def test_fetch_playlist_tracks_returns_tracks():
    playlist_item = {"track": _TRACK_RAW, "added_at": "2024-01-01"}
    client = _make_client(paginated_return=[playlist_item])
    fetcher = SpotifyFetcher(client)
    result = await fetcher.fetch_playlist_tracks("playlist_xyz")

    assert len(result) == 1
    assert isinstance(result[0], Track)
    assert result[0].spotify_id == "track_abc"


async def test_fetch_playlist_tracks_skips_null_tracks():
    items = [{"track": None}, {"track": _TRACK_RAW}]
    client = _make_client(paginated_return=items)
    fetcher = SpotifyFetcher(client)
    result = await fetcher.fetch_playlist_tracks("p1")

    assert len(result) == 1


async def test_fetch_playlist_tracks_skips_items_without_id():
    items = [{"track": {"id": None, "name": "Ghost"}}, {"track": _TRACK_RAW}]
    client = _make_client(paginated_return=items)
    fetcher = SpotifyFetcher(client)
    result = await fetcher.fetch_playlist_tracks("p2")

    assert len(result) == 1


# ── search ────────────────────────────────────────────────────────────────────


async def test_search_tracks_returns_tracks():
    search_response = {"tracks": {"items": [_TRACK_RAW], "next": None}}
    client = _make_client(get_return=search_response)
    fetcher = SpotifyFetcher(client)
    result = await fetcher.search("happy", type="track", limit=10)

    assert len(result) == 1
    assert isinstance(result[0], Track)
    assert result[0].title == "Song A"


async def test_search_artists_returns_artists():
    search_response = {"artists": {"items": [_ARTIST_RAW], "next": None}}
    client = _make_client(get_return=search_response)
    fetcher = SpotifyFetcher(client)
    result = await fetcher.search("artist x", type="artist", limit=10)

    assert len(result) == 1
    assert isinstance(result[0], Artist)
    assert result[0].name == "Artist X"


async def test_search_invalid_type():
    client = _make_client()
    fetcher = SpotifyFetcher(client)
    with pytest.raises(ValueError, match="type"):
        await fetcher.search("q", type="playlist")


async def test_search_clamps_limit_to_50():
    search_response = {"tracks": {"items": [], "next": None}}
    client = _make_client(get_return=search_response)
    fetcher = SpotifyFetcher(client)
    await fetcher.search("q", type="track", limit=200)

    client.get.assert_awaited_once_with("/search", q="q", type="track", limit=50)
