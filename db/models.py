import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from libs.common.enums import (
    FeedbackType,
    ImportStatus,
    PlaylistMode,
    PlaySource,
    SaveSource,
)


class Base(DeclarativeBase):
    pass


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.utcnow()


# ── Music Metadata Cache ──────────────────────────────────────────────────────


class Artist(Base):
    __tablename__ = "artists"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    spotify_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    popularity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_now, onupdate=_now, nullable=False
    )

    genres: Mapped[list["Genre"]] = relationship(
        "Genre", secondary="artist_genres", back_populates="artists", lazy="select"
    )
    albums: Mapped[list["Album"]] = relationship("Album", back_populates="artist", lazy="select")
    track_links: Mapped[list["TrackArtist"]] = relationship(
        "TrackArtist", back_populates="artist", lazy="select"
    )


class Genre(Base):
    __tablename__ = "genres"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)

    artists: Mapped[list["Artist"]] = relationship(
        "Artist", secondary="artist_genres", back_populates="genres", lazy="select"
    )


class ArtistGenre(Base):
    __tablename__ = "artist_genres"

    artist_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("artists.id", ondelete="CASCADE"), primary_key=True
    )
    genre_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("genres.id", ondelete="CASCADE"), primary_key=True
    )


class Album(Base):
    __tablename__ = "albums"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    spotify_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    artist_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("artists.id", ondelete="SET NULL"), nullable=True
    )
    release_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_tracks: Mapped[int | None] = mapped_column(Integer, nullable=True)
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_now, onupdate=_now, nullable=False
    )

    artist: Mapped["Artist | None"] = relationship("Artist", back_populates="albums", lazy="select")
    tracks: Mapped[list["Track"]] = relationship("Track", back_populates="album", lazy="select")


class Track(Base):
    __tablename__ = "tracks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    spotify_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    album_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("albums.id", ondelete="SET NULL"), nullable=True
    )
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    popularity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    preview_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_now, onupdate=_now, nullable=False
    )

    album: Mapped["Album | None"] = relationship("Album", back_populates="tracks", lazy="select")
    artist_links: Mapped[list["TrackArtist"]] = relationship(
        "TrackArtist", back_populates="track", lazy="select"
    )
    user_data: Mapped["UserTrackData | None"] = relationship(
        "UserTrackData", back_populates="track", lazy="select", uselist=False
    )
    play_events: Mapped[list["PlayEvent"]] = relationship(
        "PlayEvent", back_populates="track", lazy="select"
    )


class TrackArtist(Base):
    __tablename__ = "track_artists"

    track_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tracks.id", ondelete="CASCADE"), primary_key=True
    )
    artist_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("artists.id", ondelete="CASCADE"), primary_key=True
    )
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    track: Mapped["Track"] = relationship("Track", back_populates="artist_links", lazy="select")
    artist: Mapped["Artist"] = relationship("Artist", back_populates="track_links", lazy="select")


# ── User Signals ──────────────────────────────────────────────────────────────


class UserTrackData(Base):
    __tablename__ = "user_track_data"

    track_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("tracks.id", ondelete="CASCADE"),
        primary_key=True,
        unique=True,
    )
    is_saved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    save_source: Mapped[str | None] = mapped_column(
        Enum(SaveSource, name="savesource"), nullable=True
    )
    saved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    feedback: Mapped[str | None] = mapped_column(
        Enum(FeedbackType, name="feedbacktype"), nullable=True
    )
    feedback_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    play_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_played_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    top_position_short: Mapped[int | None] = mapped_column(Integer, nullable=True)
    top_position_medium: Mapped[int | None] = mapped_column(Integer, nullable=True)
    top_position_long: Mapped[int | None] = mapped_column(Integer, nullable=True)
    declared_artist_label: Mapped[float | None] = mapped_column(Float, nullable=True)
    declared_artist_weight: Mapped[float | None] = mapped_column(Float, nullable=True)
    declared_artist_spotify_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    declared_playlist_label: Mapped[float | None] = mapped_column(Float, nullable=True)
    declared_playlist_weight: Mapped[float | None] = mapped_column(Float, nullable=True)

    track: Mapped["Track"] = relationship("Track", back_populates="user_data", lazy="select")


class PlayEvent(Base):
    __tablename__ = "play_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    track_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tracks.id", ondelete="CASCADE"), nullable=False
    )
    played_at: Mapped[datetime] = mapped_column(DateTime, default=_now, nullable=False)
    ms_played: Mapped[int] = mapped_column(Integer, nullable=False)
    source: Mapped[str] = mapped_column(Enum(PlaySource, name="playsource"), nullable=False)
    playlist_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("playlists.id", ondelete="SET NULL"), nullable=True
    )

    track: Mapped["Track"] = relationship("Track", back_populates="play_events", lazy="select")
    playlist: Mapped["Playlist | None"] = relationship(
        "Playlist", back_populates="play_events", lazy="select"
    )


# ── Generated Content ─────────────────────────────────────────────────────────


class Playlist(Base):
    __tablename__ = "playlists"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    mode: Mapped[str] = mapped_column(Enum(PlaylistMode, name="playlistmode"), nullable=False)
    size: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now, nullable=False)
    exported_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    spotify_playlist_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    spotify_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    tracks: Mapped[list["PlaylistTrack"]] = relationship(
        "PlaylistTrack", back_populates="playlist", lazy="select"
    )
    play_events: Mapped[list["PlayEvent"]] = relationship(
        "PlayEvent", back_populates="playlist", lazy="select"
    )


class PlaylistTrack(Base):
    __tablename__ = "playlist_tracks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    playlist_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("playlists.id", ondelete="CASCADE"), nullable=False
    )
    track_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tracks.id", ondelete="CASCADE"), nullable=False
    )
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    final_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    score_breakdown: Mapped[dict[str, float] | None] = mapped_column(JSON, nullable=True)

    __table_args__ = (
        UniqueConstraint("playlist_id", "rank", name="uq_playlist_rank"),
        UniqueConstraint("playlist_id", "track_id", name="uq_playlist_track"),
    )

    playlist: Mapped["Playlist"] = relationship("Playlist", back_populates="tracks", lazy="select")
    track: Mapped["Track"] = relationship("Track", lazy="select")


# ── System ────────────────────────────────────────────────────────────────────


class Auth(Base):
    __tablename__ = "auth"

    spotify_user_id: Mapped[str] = mapped_column(String(128), primary_key=True, nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    access_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    import_status: Mapped[str] = mapped_column(
        Enum(ImportStatus, name="importstatus"),
        default=ImportStatus.idle,
        nullable=False,
    )
    import_started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    import_completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


# ── Onboarding Declarations ────────────────────────────────────────────────────


class DeclaredArtist(Base):
    __tablename__ = "declared_artists"

    spotify_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    track_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now, nullable=False)


class DeclaredPlaylist(Base):
    __tablename__ = "declared_playlists"

    spotify_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    track_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now, nullable=False)
