from __future__ import annotations

from dataclasses import dataclass

from libs.common.enums import PlaylistMode
from libs.common.models import Candidate, UserProfile


@dataclass(frozen=True)
class ModeWeights:
    base_score_multiplier: float
    artist_affinity_weight: float
    novelty_bonus: float  # applied when is_unknown_artist == 1.0
    popularity_weight: float  # positive = prefer popular, negative = prefer obscure


_MODE_WEIGHTS: dict[PlaylistMode, ModeWeights] = {
    PlaylistMode.safe: ModeWeights(
        base_score_multiplier=1.3,
        artist_affinity_weight=0.4,
        novelty_bonus=-0.3,
        popularity_weight=0.3,
    ),
    PlaylistMode.balanced: ModeWeights(
        base_score_multiplier=1.0,
        artist_affinity_weight=0.15,
        novelty_bonus=0.0,
        popularity_weight=0.0,
    ),
    PlaylistMode.adventurous: ModeWeights(
        base_score_multiplier=1.0,
        artist_affinity_weight=0.05,
        novelty_bonus=0.3,
        popularity_weight=-0.2,
    ),
}


def apply_mode(
    candidate: Candidate,
    base_score: float,
    profile: UserProfile,
    mode: PlaylistMode,
) -> tuple[float, dict[str, float]]:
    """Apply mode-specific adjustments to the Two-Tower base score.

    Returns (final_score, score_breakdown).
    score_breakdown keys: base_score, artist_affinity_bonus,
                          novelty_adjustment, popularity_adjustment, mode_weight.
    """
    weights = _MODE_WEIGHTS[mode]

    # Artist affinity bonus: how well-known this artist is to the user
    artist_affinity = profile.artist_affinities.get(candidate.track.artist_name, 0.0)
    artist_affinity_bonus = weights.artist_affinity_weight * artist_affinity

    # Novelty: penalise or reward unknown artists
    # artist_affinity_score == 0.0 and artist not in profile → treat as unknown
    is_unknown = (
        1.0
        if candidate.artist_affinity_score == 0.0
        and candidate.track.artist_name not in profile.artist_affinities
        else 0.0
    )
    novelty_adjustment = weights.novelty_bonus * is_unknown

    # Popularity: normalised to [0, 1] (track.popularity is 0–100)
    norm_popularity = candidate.track.popularity / 100.0
    popularity_adjustment = weights.popularity_weight * norm_popularity

    weighted_base = base_score * weights.base_score_multiplier
    final_score = weighted_base + artist_affinity_bonus + novelty_adjustment + popularity_adjustment

    breakdown: dict[str, float] = {
        "base_score": base_score,
        "artist_affinity_bonus": artist_affinity_bonus,
        "novelty_adjustment": novelty_adjustment,
        "popularity_adjustment": popularity_adjustment,
        "mode_weight": weights.base_score_multiplier,
    }
    return final_score, breakdown
