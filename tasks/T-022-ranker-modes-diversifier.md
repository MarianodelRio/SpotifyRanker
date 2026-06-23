---
id: T-022
phase: 2
agent: ML/Ranking
depends_on: [T-021, T-010]
status: DONE
branch: feature/T-022-ranker-modes-diversifier
pr: "https://github.com/MarianodelRio/SpotifyRanker/pull/29"
---

### T-022 — Ranker + modes + diversifier
**Phase:** 2 | **Agent:** ML/Ranking | **Depends on:** T-021, T-010

Build the full ranking layer: score candidates with the ML model, apply mode-specific adjustments, and diversify the output.

**Scope — `libs/ranker/`**
- `ranker.py`: `rank(candidates, profile, mode, towers) → list[RankedTrack]`. Computes item embeddings, user embedding, base scores. Calls mode adjuster, then diversifier.
- `modes.py`: applies mode weight table from `design.md` section 10. Segura = boost artist affinity + popularity, penalize unknown artists. Novedad = boost unknown artists, penalize popularity. Mezcla = neutral. Each adjustment modifies `final_score` and records the breakdown in `score_breakdown`.
- `diversifier.py`: ensures no more than 3 tracks per artist and no genre exceeds 40% of the playlist. Greedy selection from the ranked list.

**Acceptance criteria**
- In Novedad mode, tracks from unknown artists rank higher than in Segura mode (testable with synthetic data).
- Diversifier: a 20-track playlist from a 100-candidate pool never has more than 3 tracks from the same artist.
- `score_breakdown` dict is populated for every `RankedTrack` (not empty).
- `RankedTrack` objects match the `common.models.RankedTrack` schema exactly.

**Notes**
- `modes.py` implements a `ModeWeights` frozen dataclass with constants for `safe`/`balanced`/`adventurous` (mapped from enum values). `apply_mode()` returns `(final_score, score_breakdown)` with keys: `base_score`, `artist_affinity_bonus`, `novelty_adjustment`, `popularity_adjustment`, `mode_weight`.
- Unknown-artist detection: `artist_affinity_score == 0.0` AND artist not in `profile.artist_affinities`. This correctly handles candidates from outside the user's known artists.
- `diversifier.py` accepts an optional `genres_map: dict[str, list[str]] | None`. Genre cap is enforced when it is provided; artist cap is always enforced. `Track` has no genres field, so callers must inject genres externally if genre diversification is needed.
- `ranker.py` also accepts optional `genres_map` and `artist_popularity_map` for richer embeddings; both default to `None` for backward-compatible usage.
- All 301 tests pass; mypy and ruff clean.
- PR Reviewer: `ranker.py` has 0% unit test coverage (expected — requires trained model files). `modes.py` and `diversifier.py` are both 100%. Overall libs/ coverage is 88%. Flagged for human review: unknown-artist detection logic at modes.py:59-64 and the once-per-call `get_vocab()` disk read in ranker.py:42.
