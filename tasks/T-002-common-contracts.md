---
id: T-002
phase: 0
agent: Architect
depends_on: [T-001]
status: PR_OPEN
branch: feature/T-002-common-contracts
pr: "https://github.com/MarianodelRio/SpotifyRanker/pull/2"
---

### T-002 — Common contracts (models + enums)
**Phase:** 0 | **Agent:** Architect | **Depends on:** T-001

Define all shared Pydantic models and enums in `libs/common/`. These are the contracts that all other modules import and must never break.

**Scope — `libs/common/enums.py`**
- `PlaylistMode`: safe, balanced, adventurous
- `FeedbackType`: like, dislike
- `ImportStatus`: idle, running, completed, failed
- `CandidateSource`: artist_discography, genre_search
- `PlaySource`: my_music, search, discover

**Scope — `libs/common/models.py`**
Domain models as Pydantic BaseModel (not ORM):
- `Track`: spotify_id, title, artist_name, album_title, duration_ms, popularity, image_url
- `Artist`: spotify_id, name, popularity, genres, image_url
- `UserProfile`: genre_weights (dict), artist_affinities (dict), known_track_ids (set), global_like_ratio, diversity_score
- `Candidate`: track (Track), source (CandidateSource), artist_affinity_score
- `RankedTrack`: candidate (Candidate), final_score, score_breakdown (dict)
- `GeneratedPlaylist`: id, name, mode (PlaylistMode), tracks (list[RankedTrack]), created_at, spotify_url (optional)
- `FeedbackEntry`: track_id, feedback_type (FeedbackType), source (PlaySource), playlist_id (optional)

**Acceptance criteria**
- All models and enums importable from `libs.common`.
- No imports from any other `libs/` module inside `libs/common/`.
- Full mypy strict pass.
- TypeScript types in `apps/frontend/src/types/api.ts` mirror these models (can be placeholder types at this stage).

**Notes**
- `CandidateSource` updated to `artist_discography / genre_search` per design.md (scaffold had different values).
- `TimeRange` enum retained (not in spec but referenced in architect smoke test; needed by upcoming T-007 Spotify fetcher).
- `UserProfile` has no `model_config = ConfigDict(from_attributes=True)` — it has no ORM counterpart, correct by design.
- `GeneratedPlaylist.id` auto-generates a UUID via `Field(default_factory=...)`.
- `apps/frontend/src/types/api.ts` created from scratch (directory did not exist); TypeScript `Set` not used for `known_track_ids` — serialized as `string[]` per JSON convention.
- 14 unit tests, 100% coverage on `libs/common/`.
