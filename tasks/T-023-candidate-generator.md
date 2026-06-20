---
id: T-023
phase: 2
agent: Domain Core
depends_on: [T-010, T-007]
status: PR_OPEN
branch: feature/T-023-candidate-generator
pr: "https://github.com/MarianodelRio/SpotifyRanker/pull/14"
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
- Implemented two sources: `artist_discography` (top-10 artists by affinity, albums → tracks, capped at 150) and `genre_search` (top-5 genres via Spotify search, capped at 150).
- `deduplicator.py` runs after all sources are aggregated; upserts unique tracks into DB via `TrackRepository`.
- `CandidateGenerator.generate()` merges both source lists (artist_discography first for priority trimming), enforces 500-candidate hard cap, then deduplicates.
- `session` is injected into `generate()` per task spec; only `deduplicator.py` touches the DB — sources remain pure async functions.
- 14 unit tests, all passing; full suite (167 tests) green; mypy clean.
- PR Reviewer: trivial fix applied — added explanation comment to `type: ignore[assignment]` in `genre_search.py` (SpotifyFetcher.search returns a union; narrowed to list[Track] since type="track" is passed). Branch rebased onto master as a single clean implementation commit.
