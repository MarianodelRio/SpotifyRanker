---
id: T-023
phase: 2
agent: Domain Core
depends_on: [T-010, T-007]
status: TODO
branch: ""
pr: ""
---

### T-023 — Candidate generator
**Phase:** 2 | **Agent:** Domain Core | **Depends on:** T-010, T-007

Build the candidate generation module that fetches unknown tracks from Spotify for the user to discover.

**Scope — `libs/candidates/`**
- `generator.py`: `generate(profile, fetcher, session) → list[Candidate]`. Orchestrates both sources, deduplicates, returns final pool.
- `sources/artist_discography.py`: top N artists by affinity from `UserProfile` → fetch all albums and tracks via Spotify fetcher → filter out tracks in `known_track_ids`. Returns `list[Candidate]` with `source=CandidateSource.artist_discography`.
- `sources/genre_search.py`: top 5 genres by weight → Spotify search by genre → filter out known tracks. Returns `list[Candidate]` with `source=CandidateSource.genre_search`.
- `deduplicator.py`: removes duplicates by `spotify_id`. Upserts candidate tracks into DB (tracks table) so they can be scored and persisted if interacted with.

**Acceptance criteria**
- No track in `known_track_ids` appears in the returned candidates.
- At least one result from each source strategy (if the profile has genres and artists).
- Candidate tracks are upserted into the DB after generation.
- With an empty profile (no affinities), returns an empty list gracefully (no errors).

**Notes**
_Orchestrator fills after completion._
