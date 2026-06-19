from pydantic import BaseModel, ConfigDict


class Track(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    spotify_id: str
    title: str


class Artist(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    spotify_id: str
    name: str


class UserProfile(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: str


class Candidate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    spotify_id: str


class RankedTrack(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    spotify_id: str
    final_score: float


class GeneratedPlaylist(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str


class FeedbackEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    spotify_id: str
    feedback: str
