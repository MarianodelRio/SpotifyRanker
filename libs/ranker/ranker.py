from __future__ import annotations

from libs.common.enums import PlaylistMode
from libs.common.models import Candidate, RankedTrack, UserProfile
from libs.ml.inference import (
    compute_item_embedding,
    compute_user_embedding,
    get_vocab,
    load_embedding_cache,
    score_candidates,
)
from libs.ml.trainer import TowerPair
from libs.ranker.diversifier import diversify
from libs.ranker.modes import apply_mode


def rank(
    candidates: list[Candidate],
    profile: UserProfile,
    mode: PlaylistMode,
    towers: TowerPair,
    n: int = 20,
    genres_map: dict[str, list[str]] | None = None,
    artist_popularity_map: dict[str, int] | None = None,
) -> list[RankedTrack]:
    """Score candidates with the Two-Tower model, apply mode adjustments, diversify.

    Args:
        candidates: tracks to rank.
        profile: current user taste profile.
        mode: playlist tone (safe / balanced / adventurous).
        towers: loaded TowerPair from load_model().
        n: number of tracks to return after diversification.
        genres_map: optional track_id → genre list (enables genre diversification).
        artist_popularity_map: optional artist_name → popularity int 0–100.

    Returns:
        Sorted, diversified list of RankedTrack (best first).
    """
    if not candidates:
        return []

    vocab = get_vocab()

    user_emb = compute_user_embedding(profile, towers, vocab)
    cache = load_embedding_cache()

    item_embs = []
    for candidate in candidates:
        track = candidate.track
        if track.spotify_id in cache:
            item_embs.append(cache[track.spotify_id])
        else:
            genres = genres_map.get(track.spotify_id, []) if genres_map else []
            artist_pop = (
                artist_popularity_map.get(track.artist_name, 0) if artist_popularity_map else 0
            )
            item_embs.append(compute_item_embedding(track, towers, genres, artist_pop, vocab))

    base_scores = score_candidates(user_emb, item_embs)

    ranked: list[RankedTrack] = []
    for candidate, base_score in zip(candidates, base_scores, strict=True):
        final_score, breakdown = apply_mode(candidate, base_score, profile, mode)
        ranked.append(
            RankedTrack(candidate=candidate, final_score=final_score, score_breakdown=breakdown)
        )

    ranked.sort(key=lambda rt: rt.final_score, reverse=True)

    return diversify(ranked, n, genres_map=genres_map)
