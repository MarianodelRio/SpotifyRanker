"""Tests for all repository classes against in-memory SQLite."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from db.models import Base, TrackArtist, UserTrackData
from db.repositories import (
    AlbumRepository,
    ArtistRepository,
    AuthRepository,
    GenreRepository,
    PlayEventRepository,
    PlaylistRepository,
    TrackRepository,
    UserTrackDataRepository,
)
from libs.common.enums import ImportStatus, PlaySource


@pytest.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as s:
        yield s
    await engine.dispose()


# ── TrackRepository ───────────────────────────────────────────────────────────


async def test_track_upsert_creates_row(session):
    repo = TrackRepository(session)
    track_id = await repo.upsert(spotify_id="sp_t1", title="Song A")
    assert track_id is not None

    track = await repo.get_by_spotify_id("sp_t1")
    assert track is not None
    assert track.title == "Song A"
    assert track.id == track_id


async def test_track_upsert_is_idempotent(session):
    repo = TrackRepository(session)
    id1 = await repo.upsert(spotify_id="sp_t1", title="Song A")
    id2 = await repo.upsert(spotify_id="sp_t1", title="Song A updated")

    assert id1 == id2
    track = await repo.get_by_spotify_id("sp_t1")
    assert track is not None
    assert track.title == "Song A updated"


async def test_track_get_by_id(session):
    repo = TrackRepository(session)
    track_id = await repo.upsert(spotify_id="sp_t2", title="Song B")
    track = await repo.get_by_id(track_id)
    assert track is not None
    assert track.spotify_id == "sp_t2"


async def test_track_get_by_id_missing(session):
    repo = TrackRepository(session)
    assert await repo.get_by_id("nonexistent") is None


async def test_track_get_by_spotify_id_missing(session):
    repo = TrackRepository(session)
    assert await repo.get_by_spotify_id("missing") is None


# ── ArtistRepository ──────────────────────────────────────────────────────────


async def test_artist_upsert_creates_row(session):
    repo = ArtistRepository(session)
    artist_id = await repo.upsert(spotify_id="sp_a1", name="Artist One", popularity=80)
    assert artist_id is not None

    artist = await repo.get_by_spotify_id("sp_a1")
    assert artist is not None
    assert artist.name == "Artist One"
    assert artist.popularity == 80


async def test_artist_upsert_is_idempotent(session):
    repo = ArtistRepository(session)
    id1 = await repo.upsert(spotify_id="sp_a1", name="Artist One")
    id2 = await repo.upsert(spotify_id="sp_a1", name="Artist One v2", popularity=90)

    assert id1 == id2
    artist = await repo.get_by_spotify_id("sp_a1")
    assert artist is not None
    assert artist.name == "Artist One v2"
    assert artist.popularity == 90


async def test_artist_get_by_id(session):
    repo = ArtistRepository(session)
    artist_id = await repo.upsert(spotify_id="sp_a2", name="Artist Two")
    artist = await repo.get_by_id(artist_id)
    assert artist is not None
    assert artist.spotify_id == "sp_a2"


async def test_artist_get_by_id_missing(session):
    repo = ArtistRepository(session)
    assert await repo.get_by_id("nonexistent") is None


async def test_artist_upsert_track_artist_creates_link(session):
    artist_repo = ArtistRepository(session)
    track_repo = TrackRepository(session)

    artist_id = await artist_repo.upsert(spotify_id="sp_a1", name="Artist One")
    track_id = await track_repo.upsert(spotify_id="sp_t1", title="Song A")

    await artist_repo.upsert_track_artist(track_id=track_id, artist_id=artist_id, is_primary=True)

    from sqlalchemy import select as sa_select

    result = await session.execute(sa_select(TrackArtist).where(TrackArtist.track_id == track_id))
    links = result.scalars().all()
    assert len(links) == 1
    assert links[0].artist_id == artist_id
    assert links[0].is_primary is True


async def test_artist_upsert_track_artist_is_idempotent(session):
    artist_repo = ArtistRepository(session)
    track_repo = TrackRepository(session)

    artist_id = await artist_repo.upsert(spotify_id="sp_a1", name="Artist One")
    track_id = await track_repo.upsert(spotify_id="sp_t1", title="Song A")

    await artist_repo.upsert_track_artist(track_id=track_id, artist_id=artist_id, is_primary=True)
    await artist_repo.upsert_track_artist(track_id=track_id, artist_id=artist_id, is_primary=True)

    from sqlalchemy import select as sa_select

    result = await session.execute(sa_select(TrackArtist).where(TrackArtist.track_id == track_id))
    assert len(result.scalars().all()) == 1


async def test_artist_upsert_track_artist_multiple_artists(session):
    artist_repo = ArtistRepository(session)
    track_repo = TrackRepository(session)

    a1_id = await artist_repo.upsert(spotify_id="sp_a1", name="Primary Artist")
    a2_id = await artist_repo.upsert(spotify_id="sp_a2", name="Featured Artist")
    track_id = await track_repo.upsert(spotify_id="sp_t1", title="Collab Track")

    await artist_repo.upsert_track_artist(track_id=track_id, artist_id=a1_id, is_primary=True)
    await artist_repo.upsert_track_artist(track_id=track_id, artist_id=a2_id, is_primary=False)

    from sqlalchemy import select as sa_select

    result = await session.execute(sa_select(TrackArtist).where(TrackArtist.track_id == track_id))
    links = result.scalars().all()
    assert len(links) == 2
    primary = next(lk for lk in links if lk.is_primary)
    assert primary.artist_id == a1_id


async def test_artist_get_top_by_affinity_empty(session):
    repo = ArtistRepository(session)
    result = await repo.get_top_by_affinity(limit=5)
    assert result == []


async def test_artist_get_top_by_affinity_ranks_by_play_count(session):
    artist_repo = ArtistRepository(session)
    track_repo = TrackRepository(session)

    a1_id = await artist_repo.upsert(spotify_id="sp_a1", name="Popular Artist")
    a2_id = await artist_repo.upsert(spotify_id="sp_a2", name="Niche Artist")

    t1_id = await track_repo.upsert(spotify_id="sp_t1", title="Hit")
    t2_id = await track_repo.upsert(spotify_id="sp_t2", title="Deep Cut")

    session.add(TrackArtist(track_id=t1_id, artist_id=a1_id, is_primary=True))
    session.add(TrackArtist(track_id=t2_id, artist_id=a2_id, is_primary=True))
    await session.commit()

    # Manually set play counts via ORM (UserTrackDataRepository.upsert doesn't expose play_count)
    session.add(UserTrackData(track_id=t1_id, is_saved=False, play_count=50))
    session.add(UserTrackData(track_id=t2_id, is_saved=False, play_count=5))
    await session.commit()

    top = await artist_repo.get_top_by_affinity(limit=2)
    assert len(top) == 2
    assert top[0].spotify_id == "sp_a1"
    assert top[1].spotify_id == "sp_a2"


# ── AlbumRepository ───────────────────────────────────────────────────────────


async def test_album_upsert_creates_row(session):
    repo = AlbumRepository(session)
    album_id = await repo.upsert(spotify_id="sp_al1", title="Album One", release_year=2020)
    assert album_id is not None

    album = await repo.get_by_spotify_id("sp_al1")
    assert album is not None
    assert album.title == "Album One"
    assert album.release_year == 2020


async def test_album_upsert_is_idempotent(session):
    repo = AlbumRepository(session)
    id1 = await repo.upsert(spotify_id="sp_al1", title="Album One")
    id2 = await repo.upsert(spotify_id="sp_al1", title="Album One Updated")

    assert id1 == id2
    album = await repo.get_by_spotify_id("sp_al1")
    assert album is not None
    assert album.title == "Album One Updated"


async def test_album_get_by_spotify_id_missing(session):
    repo = AlbumRepository(session)
    assert await repo.get_by_spotify_id("missing") is None


# ── GenreRepository ───────────────────────────────────────────────────────────


async def test_genre_get_or_create_creates(session):
    repo = GenreRepository(session)
    genre = await repo.get_or_create("rock")
    assert genre.name == "rock"
    assert genre.id is not None


async def test_genre_get_or_create_is_idempotent(session):
    repo = GenreRepository(session)
    g1 = await repo.get_or_create("rock")
    g2 = await repo.get_or_create("rock")
    assert g1.id == g2.id


async def test_genre_get_all(session):
    repo = GenreRepository(session)
    await repo.get_or_create("rock")
    await repo.get_or_create("pop")
    await repo.get_or_create("jazz")
    genres = await repo.get_all()
    names = [g.name for g in genres]
    assert "rock" in names
    assert "pop" in names
    assert "jazz" in names
    assert len(genres) == 3


# ── UserTrackDataRepository ───────────────────────────────────────────────────


async def test_utd_upsert_creates_row(session):
    track_repo = TrackRepository(session)
    t_id = await track_repo.upsert(spotify_id="sp_t1", title="T")

    repo = UserTrackDataRepository(session)
    await repo.upsert(track_id=t_id, is_saved=True)

    saved = await repo.get_saved_tracks()
    assert len(saved) == 1
    assert saved[0].track_id == t_id


async def test_utd_upsert_is_idempotent(session):
    track_repo = TrackRepository(session)
    t_id = await track_repo.upsert(spotify_id="sp_t1", title="T")

    repo = UserTrackDataRepository(session)
    await repo.upsert(track_id=t_id, is_saved=True)
    await repo.upsert(track_id=t_id, is_saved=False)

    all_ids = await repo.get_all_known_ids()
    assert all_ids.count(t_id) == 1


async def test_utd_get_liked_tracks(session):
    track_repo = TrackRepository(session)
    t1 = await track_repo.upsert(spotify_id="sp_t1", title="T1")
    t2 = await track_repo.upsert(spotify_id="sp_t2", title="T2")

    repo = UserTrackDataRepository(session)
    await repo.upsert(track_id=t1, feedback="like")
    await repo.upsert(track_id=t2, feedback="dislike")

    liked = await repo.get_liked_tracks()
    assert len(liked) == 1
    assert liked[0].track_id == t1


async def test_utd_get_all_known_ids(session):
    track_repo = TrackRepository(session)
    t1 = await track_repo.upsert(spotify_id="sp_t1", title="T1")
    t2 = await track_repo.upsert(spotify_id="sp_t2", title="T2")

    repo = UserTrackDataRepository(session)
    await repo.upsert(track_id=t1, is_saved=True)
    await repo.upsert(track_id=t2, is_saved=True)

    ids = await repo.get_all_known_ids()
    assert set(ids) == {t1, t2}


# ── PlayEventRepository ───────────────────────────────────────────────────────


async def test_play_event_append(session):
    track_repo = TrackRepository(session)
    t_id = await track_repo.upsert(spotify_id="sp_t1", title="T")

    repo = PlayEventRepository(session)
    event = await repo.append(track_id=t_id, ms_played=45000, source=PlaySource.my_music)
    assert event.id is not None
    assert event.ms_played == 45000
    assert event.track_id == t_id


async def test_play_event_get_for_track(session):
    track_repo = TrackRepository(session)
    t_id = await track_repo.upsert(spotify_id="sp_t1", title="T")

    repo = PlayEventRepository(session)
    await repo.append(track_id=t_id, ms_played=10000, source=PlaySource.search)
    await repo.append(track_id=t_id, ms_played=20000, source=PlaySource.discover)

    events = await repo.get_for_track(t_id)
    assert len(events) == 2


async def test_play_event_append_never_overwrites(session):
    track_repo = TrackRepository(session)
    t_id = await track_repo.upsert(spotify_id="sp_t1", title="T")

    repo = PlayEventRepository(session)
    e1 = await repo.append(track_id=t_id, ms_played=1000, source=PlaySource.my_music)
    e2 = await repo.append(track_id=t_id, ms_played=2000, source=PlaySource.my_music)

    assert e1.id != e2.id
    events = await repo.get_for_track(t_id)
    assert len(events) == 2


# ── PlaylistRepository ────────────────────────────────────────────────────────


async def test_playlist_create(session):
    repo = PlaylistRepository(session)
    playlist = await repo.create(name="My Playlist", mode="safe", size=20)
    assert playlist.id is not None
    assert playlist.name == "My Playlist"


async def test_playlist_get_by_id(session):
    repo = PlaylistRepository(session)
    p = await repo.create(name="P1", mode="balanced", size=10)
    found = await repo.get_by_id(p.id)
    assert found is not None
    assert found.name == "P1"


async def test_playlist_get_by_id_missing(session):
    repo = PlaylistRepository(session)
    assert await repo.get_by_id("nonexistent") is None


async def test_playlist_get_history(session):
    repo = PlaylistRepository(session)
    await repo.create(name="Old", mode="safe", size=10)
    await repo.create(name="New", mode="adventurous", size=20)

    history = await repo.get_history()
    assert len(history) == 2
    assert history[0].name == "New"


# ── AuthRepository ────────────────────────────────────────────────────────────


async def test_auth_upsert_creates_row(session):
    repo = AuthRepository(session)
    auth = await repo.upsert_auth(
        spotify_user_id="user1",
        display_name="Alice",
        access_token="tok_access",
        refresh_token="tok_refresh",
    )
    assert auth.spotify_user_id == "user1"
    assert auth.display_name == "Alice"
    assert auth.import_status == ImportStatus.idle


async def test_auth_upsert_is_idempotent(session):
    repo = AuthRepository(session)
    await repo.upsert_auth(spotify_user_id="user1", display_name="Alice")
    auth2 = await repo.upsert_auth(spotify_user_id="user1", display_name="Alice B")

    assert auth2.display_name == "Alice B"
    assert auth2.import_status == ImportStatus.idle


async def test_auth_get_auth_returns_none_when_empty(session):
    repo = AuthRepository(session)
    assert await repo.get_auth() is None


async def test_auth_update_import_status(session):
    repo = AuthRepository(session)
    await repo.upsert_auth(spotify_user_id="user1")
    await repo.update_import_status("user1", ImportStatus.running)

    auth = await repo.get_auth()
    assert auth is not None
    assert auth.import_status == ImportStatus.running


async def test_auth_update_token(session):
    from datetime import datetime, timedelta

    repo = AuthRepository(session)
    await repo.upsert_auth(spotify_user_id="user1", access_token="old")

    expires = datetime.utcnow() + timedelta(hours=1)
    await repo.update_token(
        "user1",
        access_token="new_access",
        refresh_token="new_refresh",
        token_expires_at=expires,
    )

    auth = await repo.get_auth()
    assert auth is not None
    assert auth.access_token == "new_access"
    assert auth.refresh_token == "new_refresh"


# ── ArtistRepository.get_names_by_spotify_ids ─────────────────────────────────


async def test_artist_get_names_by_spotify_ids_returns_known_names(session):
    repo = ArtistRepository(session)
    await repo.upsert(spotify_id="sp1", name="Artist One")
    await repo.upsert(spotify_id="sp2", name="Artist Two")

    result = await repo.get_names_by_spotify_ids(["sp1", "sp2"])

    assert result == {"sp1": "Artist One", "sp2": "Artist Two"}


async def test_artist_get_names_by_spotify_ids_ignores_unknown_ids(session):
    repo = ArtistRepository(session)
    await repo.upsert(spotify_id="sp1", name="Artist One")

    result = await repo.get_names_by_spotify_ids(["sp1", "does_not_exist"])

    assert result == {"sp1": "Artist One"}
    assert "does_not_exist" not in result


async def test_artist_get_names_by_spotify_ids_empty_input(session):
    repo = ArtistRepository(session)

    result = await repo.get_names_by_spotify_ids([])

    assert result == {}
