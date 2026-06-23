"""Unit tests for libs/ml/metrics.py."""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from db.models import (
    Artist,
    ArtistGenre,
    Base,
    Genre,
    Playlist,
    PlaylistTrack,
    Track,
    TrackArtist,
    UserTrackData,
)
from libs.ml.metrics import append_loss_history, compute_diversity_score, compute_like_rate


@pytest.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as s:
        yield s
    await engine.dispose()


def _track(title: str = "Song") -> Track:
    return Track(id=str(uuid.uuid4()), spotify_id=str(uuid.uuid4()), title=title)


def _playlist(name: str = "PL") -> Playlist:
    return Playlist(id=str(uuid.uuid4()), name=name, mode="balanced", size=10)


# ── compute_like_rate ─────────────────────────────────────────────────────────


async def test_like_rate_empty_db(session):
    result = await compute_like_rate(session)
    assert result is None


async def test_like_rate_no_likes(session):
    track = _track()
    playlist = _playlist()
    pt = PlaylistTrack(id=str(uuid.uuid4()), playlist_id=playlist.id, track_id=track.id, rank=1)
    session.add_all([track, playlist, pt])
    await session.commit()

    result = await compute_like_rate(session)
    assert result == 0.0


async def test_like_rate_all_liked(session):
    tracks = [_track(f"T{i}") for i in range(4)]
    playlist = _playlist()
    pts = [
        PlaylistTrack(id=str(uuid.uuid4()), playlist_id=playlist.id, track_id=t.id, rank=i)
        for i, t in enumerate(tracks)
    ]
    utds = [UserTrackData(track_id=t.id, feedback="like") for t in tracks]
    session.add_all(tracks + [playlist] + pts + utds)
    await session.commit()

    result = await compute_like_rate(session)
    assert result == 1.0


async def test_like_rate_partial(session):
    tracks = [_track(f"T{i}") for i in range(10)]
    playlist = _playlist()
    pts = [
        PlaylistTrack(id=str(uuid.uuid4()), playlist_id=playlist.id, track_id=t.id, rank=i)
        for i, t in enumerate(tracks)
    ]
    liked_utds = [UserTrackData(track_id=tracks[i].id, feedback="like") for i in range(5)]
    disliked_utds = [UserTrackData(track_id=tracks[i].id, feedback="dislike") for i in range(5, 10)]
    session.add_all(tracks + [playlist] + pts + liked_utds + disliked_utds)
    await session.commit()

    result = await compute_like_rate(session)
    assert result == pytest.approx(0.5)


# ── compute_diversity_score ───────────────────────────────────────────────────


async def test_diversity_score_empty_db(session):
    result = await compute_diversity_score(session)
    assert result is None


async def test_diversity_score_one_playlist_one_artist_one_genre(session):
    genre = Genre(name="pop")
    artist = Artist(id=str(uuid.uuid4()), spotify_id=str(uuid.uuid4()), name="Artist A")
    ag = ArtistGenre(artist_id=artist.id, genre_id=1)  # genre gets id=1 (autoincrement)
    track = _track()
    ta = TrackArtist(track_id=track.id, artist_id=artist.id, is_primary=True)
    playlist = _playlist()
    pt = PlaylistTrack(id=str(uuid.uuid4()), playlist_id=playlist.id, track_id=track.id, rank=1)

    session.add_all([genre, artist])
    await session.flush()
    ag.genre_id = genre.id
    session.add_all([ag, track, ta, playlist, pt])
    await session.commit()

    result = await compute_diversity_score(session)
    # 1 distinct artist + 1 distinct genre = 2.0, averaged over 1 playlist
    assert result == pytest.approx(2.0)


async def test_diversity_score_uses_last_5_playlists(session):
    # Create 7 playlists, first 2 have no tracks (empty); last 5 have 1 track each with 1 artist
    genre = Genre(name="rock")
    session.add(genre)
    await session.flush()

    artist = Artist(id=str(uuid.uuid4()), spotify_id=str(uuid.uuid4()), name="RockArtist")
    session.add(artist)
    await session.flush()

    ag = ArtistGenre(artist_id=artist.id, genre_id=genre.id)
    session.add(ag)

    playlists = [_playlist(f"PL{i}") for i in range(7)]
    session.add_all(playlists)
    await session.flush()

    # Only attach tracks to last 5 playlists (by creation order, but we need created_at ordering)
    for pl in playlists[2:]:
        track = _track()
        ta = TrackArtist(track_id=track.id, artist_id=artist.id, is_primary=True)
        pt = PlaylistTrack(id=str(uuid.uuid4()), playlist_id=pl.id, track_id=track.id, rank=1)
        session.add_all([track, ta, pt])

    await session.commit()

    result = await compute_diversity_score(session)
    # Each of the 5 playlists has 1 artist + 1 genre = 2; avg = 2.0
    assert result is not None
    assert result == pytest.approx(2.0)


# ── append_loss_history ───────────────────────────────────────────────────────


def test_append_loss_history_empty():
    state: dict = {}
    append_loss_history(state, 1.23)
    assert state["loss_history"] == [1.23]


def test_append_loss_history_grows():
    state: dict = {}
    for i in range(5):
        append_loss_history(state, float(i))
    assert state["loss_history"] == [0.0, 1.0, 2.0, 3.0, 4.0]


def test_append_loss_history_caps_at_max_n():
    state: dict = {}
    for i in range(25):
        append_loss_history(state, float(i), max_n=20)
    assert len(state["loss_history"]) == 20
    assert state["loss_history"][0] == 5.0  # oldest kept
    assert state["loss_history"][-1] == 24.0


def test_append_loss_history_returns_state():
    state: dict = {}
    returned = append_loss_history(state, 0.5)
    assert returned is state
