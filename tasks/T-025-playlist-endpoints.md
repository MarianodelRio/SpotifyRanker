---
id: T-025
phase: 2
agent: Backend/API
depends_on: [T-024, T-008]
status: IN_PROGRESS
branch: feature/T-025-playlist-endpoints
pr: ""
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
_Orchestrator fills after completion._
