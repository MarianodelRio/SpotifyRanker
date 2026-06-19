from enum import Enum


class PlaylistMode(str, Enum):
    safe = "safe"
    balanced = "balanced"
    adventurous = "adventurous"


class CandidateSource(str, Enum):
    saved = "saved"
    top_tracks = "top_tracks"
    related_artist = "related_artist"
    search = "search"


class FeedbackType(str, Enum):
    like = "like"
    dislike = "dislike"


class TimeRange(str, Enum):
    short_term = "short_term"
    medium_term = "medium_term"
    long_term = "long_term"
