---
id: T-010
phase: 1
agent: Domain Core
depends_on: [T-006]
status: TODO
branch: ""
pr: ""
---

### T-010 — Taste profile builder
**Phase:** 1 | **Agent:** Domain Core | **Depends on:** T-006

Build the stateless `UserProfile` from data in the database. This is the input to the ML pipeline and the candidate generator.

**Scope — `libs/profile/builder.py`**
`build_profile(session) → UserProfile`:
- `genre_weights`: normalized weights per genre derived from liked and saved tracks' artist genres. Recency-weighted (short-term top tracks count more than long-term).
- `artist_affinities`: score per artist based on top position, save status, and like feedback.
- `known_track_ids`: set of all spotify_ids the user has interacted with (any signal).
- `global_like_ratio`: likes / (likes + dislikes), 0.0 if no feedback yet.
- `diversity_score`: 0–1 measure of genre breadth (number of distinct genres with weight > 0.1, normalized).

All computations are pure functions of DB state. No side effects, no Spotify API calls.

**Acceptance criteria**
- `build_profile` is deterministic: same DB state → same UserProfile every time.
- With zero feedback, returns a valid UserProfile with empty/default values (no errors).
- Genre weights sum to 1.0 (normalized).
- `known_track_ids` includes tracks from all sources: saved, liked, disliked, played.
- Full unit test coverage with in-memory SQLite fixtures.

**Notes**
_Orchestrator fills after completion._
