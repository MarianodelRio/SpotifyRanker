---
id: T-002
phase: 0
agent: Architect
depends_on: [T-001]
status: IN_PROGRESS
branch: feature/T-002-common-contracts
pr: ""
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
_Orchestrator fills after completion._
