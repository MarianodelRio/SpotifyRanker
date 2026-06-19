from enum import Enum


class PlaylistMode(str, Enum):
    safe = "safe"
    balanced = "balanced"
    adventurous = "adventurous"


class FeedbackType(str, Enum):
    like = "like"
    dislike = "dislike"


class ImportStatus(str, Enum):
    idle = "idle"
    running = "running"
    completed = "completed"
    failed = "failed"


class CandidateSource(str, Enum):
    artist_discography = "artist_discography"
    genre_search = "genre_search"


class PlaySource(str, Enum):
    my_music = "my_music"
    search = "search"
    discover = "discover"


class SaveSource(str, Enum):
    spotify = "spotify"
    app = "app"


class TimeRange(str, Enum):
    short_term = "short_term"
    medium_term = "medium_term"
    long_term = "long_term"
