from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from db.models import Artist, Track, TrackArtist, UserTrackData
from libs.common.models import UserProfile
from libs.profile.weights import normalize_max, normalize_sum

# Signal weights from design.md §10 — used for both genre and artist accumulation.
# Per track we take the max of all applicable weights (saves + likes + top positions)
# so that a saved+liked track doesn't artificially inflate its genres 2×.
_W_SAVED = 1.0
_W_LIKE = 1.0
_W_TOP_SHORT_HIGH = 0.9  # positions 1–10
_W_TOP_SHORT_LOW = 0.7  # positions 11–50
_W_TOP_MEDIUM = 0.6
_W_TOP_LONG = 0.5

# Genres with a normalized weight above this threshold count toward diversity.
_DIVERSITY_THRESHOLD = 0.1
# Max "active genre" count treated as fully diverse (diversity_score == 1.0).
_DIVERSITY_MAX = 10


async def build_profile(session: AsyncSession) -> UserProfile:
    """Build a UserProfile from the current DB state.

    Deterministic: identical DB state always produces the same result.
    """
    rows: list[UserTrackData] = list(
        (
            await session.execute(
                select(UserTrackData).options(
                    selectinload(UserTrackData.track).options(
                        selectinload(Track.artist_links).options(
                            selectinload(TrackArtist.artist).selectinload(Artist.genres)
                        )
                    )
                )
            )
        ).scalars()
    )

    genre_raw: dict[str, float] = {}
    artist_raw: dict[str, float] = {}
    known_ids: set[str] = set()
    like_count = 0
    dislike_count = 0

    for utd in rows:
        track = utd.track
        if track is None:
            continue

        known_ids.add(track.spotify_id)

        if utd.feedback == "like":
            like_count += 1
        elif utd.feedback == "dislike":
            dislike_count += 1

        weight = _signal_weight(utd)
        if weight <= 0.0:
            continue

        for link in track.artist_links:
            artist = link.artist
            if artist is None:
                continue
            artist_raw[artist.spotify_id] = artist_raw.get(artist.spotify_id, 0.0) + weight
            for genre in artist.genres:
                genre_raw[genre.name] = genre_raw.get(genre.name, 0.0) + weight

    genre_weights = normalize_sum(genre_raw)
    artist_affinities = normalize_max(artist_raw)

    total_feedback = like_count + dislike_count
    global_like_ratio = like_count / total_feedback if total_feedback > 0 else 0.0

    active_genres = sum(1 for w in genre_weights.values() if w > _DIVERSITY_THRESHOLD)
    diversity_score = min(active_genres / _DIVERSITY_MAX, 1.0)

    return UserProfile(
        genre_weights=genre_weights,
        artist_affinities=artist_affinities,
        known_track_ids=known_ids,
        global_like_ratio=global_like_ratio,
        diversity_score=diversity_score,
    )


def _signal_weight(utd: UserTrackData) -> float:
    """Return the highest applicable signal weight for a UserTrackData row."""
    weight = 0.0

    if utd.is_saved:
        weight = max(weight, _W_SAVED)

    if utd.feedback == "like":
        weight = max(weight, _W_LIKE)
    # Dislikes carry no positive signal toward genre/artist weights.

    if utd.top_position_short is not None:
        pos = utd.top_position_short
        if 1 <= pos <= 10:
            weight = max(weight, _W_TOP_SHORT_HIGH)
        elif 11 <= pos <= 50:
            weight = max(weight, _W_TOP_SHORT_LOW)

    if utd.top_position_medium is not None:
        weight = max(weight, _W_TOP_MEDIUM)

    if utd.top_position_long is not None:
        weight = max(weight, _W_TOP_LONG)

    return weight
