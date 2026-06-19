---
id: T-022
phase: 2
agent: ML/Ranking
depends_on: [T-021, T-010]
status: TODO
branch: ""
pr: ""
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
_Orchestrator fills after completion._
