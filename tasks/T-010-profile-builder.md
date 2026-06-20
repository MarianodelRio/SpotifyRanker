---
id: T-010
phase: 1
agent: Domain Core
depends_on: [T-006]
status: PR_OPEN
branch: feature/T-010-profile-builder
pr: "https://github.com/MarianodelRio/SpotifyRanker/pull/9"
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
- Followed task spec: `build_profile(session: AsyncSession) → UserProfile` reads from DB directly (consistent with CLAUDE.md "profile: stateless, reads from DB"). This diverges from the domain-core agent file which says "no DB access in libs/profile/", but the task spec is authoritative.
- Signal weights taken verbatim from design.md §10. Per-track weight uses `max()` of applicable signals to avoid double-counting when a track is both saved and liked.
- `known_track_ids` includes ALL tracks with a `user_track_data` row (including dislikes/skips, as specified).
- `diversity_score` normalized as `min(active_genres / 10, 1.0)` where active = genres with weight > 0.1.
- 11 unit tests with in-memory SQLite; 89/89 suite pass; mypy + ruff clean.
- PR Reviewer: rebase was clean (one mechanical conflict in task file only). 116/116 pass after rebase. One architectural note for human: `known_track_ids` coverage of "played" source depends on T-009 maintaining the invariant that play events always create a user_track_data row — no test covers the play-count-only case. Non-blocking: behavior is correct if that invariant holds.
