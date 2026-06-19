"""Unit tests for ORM models using SQLite in-memory."""

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from db.models import (
    Album,
    Artist,
    ArtistGenre,
    Auth,
    Base,
    Genre,
    PlayEvent,
    Playlist,
    PlaylistTrack,
    Track,
    TrackArtist,
    UserTrackData,
)
from libs.common.enums import (
    FeedbackType,
    ImportStatus,
    PlaylistMode,
    PlaySource,
    SaveSource,
)


@pytest.fixture(scope="module")
def engine():
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture
def session(engine):
    with Session(engine) as s:
        yield s
        s.rollback()


# ── Helpers ───────────────────────────────────────────────────────────────────


def make_artist(spotify_id: str = "artist_1", name: str = "Artista Uno") -> Artist:
    return Artist(spotify_id=spotify_id, name=name)


def make_album(artist_id: str, spotify_id: str = "album_1") -> Album:
    return Album(spotify_id=spotify_id, title="Album Uno", artist_id=artist_id)


def make_track(album_id: str, spotify_id: str = "track_1") -> Track:
    return Track(
        spotify_id=spotify_id,
        title="Canción Uno",
        album_id=album_id,
        duration_ms=210000,
        popularity=70,
    )


def make_playlist(name: str = "Mi Descubrimiento") -> Playlist:
    return Playlist(name=name, mode=PlaylistMode.balanced, size=20)


# ── Table creation ────────────────────────────────────────────────────────────


def test_all_tables_exist(engine):
    with engine.connect() as conn:
        tables = (
            conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'")).scalars().all()
        )
    expected = {
        "artists",
        "genres",
        "artist_genres",
        "albums",
        "tracks",
        "track_artists",
        "user_track_data",
        "play_events",
        "playlists",
        "playlist_tracks",
        "auth",
    }
    assert expected.issubset(set(tables))


# ── Artist ────────────────────────────────────────────────────────────────────


def test_artist_insert(session):
    artist = make_artist()
    session.add(artist)
    session.flush()
    assert artist.id is not None
    assert len(artist.id) == 36  # UUID format


def test_artist_spotify_id_unique(session):
    session.add(make_artist("dup_artist"))
    session.flush()
    session.add(make_artist("dup_artist"))
    with pytest.raises(IntegrityError):
        session.flush()


def test_artist_is_blocked_default(session):
    artist = make_artist("artist_blocked_test")
    session.add(artist)
    session.flush()
    assert artist.is_blocked is False


# ── Genre / ArtistGenre ───────────────────────────────────────────────────────


def test_genre_name_unique(session):
    session.add(Genre(name="rock"))
    session.flush()
    session.add(Genre(name="rock"))
    with pytest.raises(IntegrityError):
        session.flush()


def test_artist_genre_composite_pk(session):
    artist = make_artist("ag_artist")
    genre = Genre(name="pop_test")
    session.add_all([artist, genre])
    session.flush()
    link = ArtistGenre(artist_id=artist.id, genre_id=genre.id)
    session.add(link)
    session.flush()
    dup = ArtistGenre(artist_id=artist.id, genre_id=genre.id)
    session.add(dup)
    with pytest.raises(IntegrityError):
        session.flush()


# ── Album ─────────────────────────────────────────────────────────────────────


def test_album_spotify_id_unique(session):
    artist = make_artist("album_artist")
    session.add(artist)
    session.flush()
    session.add(make_album(artist.id, "dup_album"))
    session.flush()
    session.add(make_album(artist.id, "dup_album"))
    with pytest.raises(IntegrityError):
        session.flush()


# ── Track ─────────────────────────────────────────────────────────────────────


def test_track_spotify_id_unique(session):
    artist = make_artist("track_artist")
    album = make_album(artist.id, "track_album")
    session.add_all([artist, album])
    session.flush()
    session.add(make_track(album.id, "dup_track"))
    session.flush()
    session.add(make_track(album.id, "dup_track"))
    with pytest.raises(IntegrityError):
        session.flush()


# ── TrackArtist ───────────────────────────────────────────────────────────────


def test_track_artist_composite_pk(session):
    artist = make_artist("ta_artist")
    album = make_album(artist.id, "ta_album")
    track = make_track(album.id, "ta_track")
    session.add_all([artist, album, track])
    session.flush()
    link = TrackArtist(track_id=track.id, artist_id=artist.id, is_primary=True)
    session.add(link)
    session.flush()
    dup = TrackArtist(track_id=track.id, artist_id=artist.id, is_primary=False)
    session.add(dup)
    with pytest.raises(IntegrityError):
        session.flush()


# ── UserTrackData ─────────────────────────────────────────────────────────────


def test_user_track_data_defaults(session):
    artist = make_artist("utd_artist")
    album = make_album(artist.id, "utd_album")
    track = make_track(album.id, "utd_track")
    session.add_all([artist, album, track])
    session.flush()
    utd = UserTrackData(track_id=track.id)
    session.add(utd)
    session.flush()
    assert utd.is_saved is False
    assert utd.play_count == 0


def test_user_track_data_with_enums(session):
    artist = make_artist("utd2_artist")
    album = make_album(artist.id, "utd2_album")
    track = make_track(album.id, "utd2_track")
    session.add_all([artist, album, track])
    session.flush()
    utd = UserTrackData(
        track_id=track.id,
        is_saved=True,
        save_source=SaveSource.spotify,
        feedback=FeedbackType.like,
    )
    session.add(utd)
    session.flush()
    assert utd.save_source == SaveSource.spotify
    assert utd.feedback == FeedbackType.like


def test_user_track_data_unique_per_track(session):
    artist = make_artist("utd3_artist")
    album = make_album(artist.id, "utd3_album")
    track = make_track(album.id, "utd3_track")
    session.add_all([artist, album, track])
    session.flush()
    session.add(UserTrackData(track_id=track.id))
    session.flush()
    session.add(UserTrackData(track_id=track.id))
    with pytest.raises(IntegrityError):
        session.flush()


# ── PlayEvent ─────────────────────────────────────────────────────────────────


def test_play_event_insert(session):
    artist = make_artist("pe_artist")
    album = make_album(artist.id, "pe_album")
    track = make_track(album.id, "pe_track")
    session.add_all([artist, album, track])
    session.flush()
    event = PlayEvent(
        track_id=track.id,
        ms_played=90000,
        source=PlaySource.my_music,
    )
    session.add(event)
    session.flush()
    assert event.id is not None
    assert event.source == PlaySource.my_music


# ── Playlist / PlaylistTrack ──────────────────────────────────────────────────


def test_playlist_insert(session):
    pl = make_playlist()
    session.add(pl)
    session.flush()
    assert pl.id is not None
    assert pl.mode == PlaylistMode.balanced


def test_playlist_track_unique_rank(session):
    artist = make_artist("pt_artist")
    album = make_album(artist.id, "pt_album")
    track_a = make_track(album.id, "pt_track_a")
    track_b = make_track(album.id, "pt_track_b")
    pl = make_playlist("pt_playlist")
    session.add_all([artist, album, track_a, track_b, pl])
    session.flush()

    session.add(PlaylistTrack(playlist_id=pl.id, track_id=track_a.id, rank=1))
    session.flush()
    session.add(PlaylistTrack(playlist_id=pl.id, track_id=track_b.id, rank=1))
    with pytest.raises(IntegrityError):
        session.flush()


def test_playlist_track_unique_track(session):
    artist = make_artist("pt2_artist")
    album = make_album(artist.id, "pt2_album")
    track = make_track(album.id, "pt2_track")
    pl = make_playlist("pt2_playlist")
    session.add_all([artist, album, track, pl])
    session.flush()

    session.add(PlaylistTrack(playlist_id=pl.id, track_id=track.id, rank=1))
    session.flush()
    session.add(PlaylistTrack(playlist_id=pl.id, track_id=track.id, rank=2))
    with pytest.raises(IntegrityError):
        session.flush()


# ── Auth ──────────────────────────────────────────────────────────────────────


def test_auth_default_import_status(session):
    auth = Auth(spotify_user_id="user123", display_name="Mariano")
    session.add(auth)
    session.flush()
    assert auth.import_status == ImportStatus.idle


def test_auth_import_status_enum(session):
    auth = Auth(
        spotify_user_id="user456",
        import_status=ImportStatus.running,
    )
    session.add(auth)
    session.flush()
    assert auth.import_status == ImportStatus.running
