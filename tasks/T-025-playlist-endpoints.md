---
id: T-025
phase: 2
agent: Backend/API
depends_on: [T-024, T-008]
status: DONE
branch: feature/T-025-playlist-endpoints
pr: "https://github.com/MarianodelRio/SpotifyRanker/pull/34"
---

### T-025 — Playlist endpoints
**Phase:** 2 | **Agent:** Backend/API | **Depends on:** T-024, T-008

Expose the full playlist generation and history API.

**Scope — `apps/api/routers/playlist.py`**
- `POST /playlist/generate` → `{mode, size}` → runs the full pipeline synchronously: build profile → generate candidates → rank → assemble → return `GeneratedPlaylist`. Shows a spinner on the frontend while running.
- `GET /playlist/history` → list of all previously generated playlists (name, mode, size, created_at, spotify_url).
- `GET /playlist/{id}` → full playlist detail with all tracks, scores, and score breakdowns.
- `POST /playlist/{id}/export` → calls `exporter.export_to_spotify`, returns `{spotify_url}`.

**Acceptance criteria**
- `/playlist/generate` returns a valid playlist with ranked tracks in under 15 seconds.
- `/playlist/history` returns all previously generated playlists ordered by `created_at` descending.
- `/playlist/{id}` returns the full track list with `score_breakdown` per track.
- Generating when no model is trained returns a clear error (not a 500).

**Notes**
- Router file is `apps/api/routers/playlist_router.py` (not `playlist.py` as scope said — naming follows project convention).
- `assembler.py` had a bug: `track_id` FK was being set to `spotify_id` (string) instead of the DB UUID. Fixed via `TrackRepository.get_by_spotify_id` lookup; `PlaylistTrack` rows are skipped if the track isn't in the DB yet.
- `PlaylistRepository` gained two new methods: `get_by_id_with_tracks` (eager-loads `tracks → track`) and `update_export`.
- `main.py` and `profile_router.py` restored from master HEAD to bring in E402/logger fixes from `395e8ae` that post-dated the branch creation.
- 11 integration tests + 2 updated assembler unit tests. 350 total tests pass, ruff clean, mypy clean for T-025 files (1 pre-existing error in `artist_discography.py` unrelated).
- PR Reviewer: `db/repositories/playlist.py` and `libs/playlist/assembler.py` are out of scope for the Backend/API agent but were required to fix a critical bug (track_id FK). Flagged for human awareness.
- PR Reviewer: `update_export` calls `session.commit()` internally — inconsistent with other repository methods that leave commit to the caller. Low risk in practice given single-user context.
- PR Reviewer: rebase resolved add/add conflict on `playlist_router.py` using T-025 implementation over master stub (422 codes, full pipeline). Human confirmed this approach.
