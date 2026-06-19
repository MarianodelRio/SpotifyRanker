from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from libs.common.enums import CandidateSource, FeedbackType, PlaylistMode, PlaySource


class Track(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    spotify_id: str
    title: str
    artist_name: str
    album_title: str
    duration_ms: int
    popularity: int
    image_url: str | None = None


class Artist(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    spotify_id: str
    name: str
    popularity: int
    genres: list[str] = Field(default_factory=list)
    image_url: str | None = None


class UserProfile(BaseModel):
    genre_weights: dict[str, float] = Field(default_factory=dict)
    artist_affinities: dict[str, float] = Field(default_factory=dict)
    known_track_ids: set[str] = Field(default_factory=set)
    global_like_ratio: float = 0.0
    diversity_score: float = 0.0


class Candidate(BaseModel):
    track: Track
    source: CandidateSource
    artist_affinity_score: float = 0.0


class RankedTrack(BaseModel):
    candidate: Candidate
    final_score: float
    score_breakdown: dict[str, float] = Field(default_factory=dict)


class GeneratedPlaylist(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    mode: PlaylistMode
    tracks: list[RankedTrack] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    spotify_url: str | None = None


class FeedbackEntry(BaseModel):
    track_id: str
    feedback_type: FeedbackType
    source: PlaySource
    playlist_id: str | None = None
