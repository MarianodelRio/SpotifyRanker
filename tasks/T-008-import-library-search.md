---
id: T-008
phase: 1
agent: Backend/API
depends_on: [T-007]
status: TODO
branch: ""
pr: ""
---

### T-008 — Import task + library + search endpoints
**Phase:** 1 | **Agent:** Backend/API | **Depends on:** T-007

Implement the background import pipeline and all library/search API endpoints.

**Scope — Background import task**
On `POST /import/start`: launch a background task that:
1. Fetches saved tracks, top tracks (short/medium/long), top artists from Spotify.
2. Upserts all tracks, artists, albums, genres via repositories.
3. Populates `user_track_data` (is_saved, save_source, top_position_*).
4. Updates `auth.import_status` throughout (running → completed or failed).

**Scope — API endpoints**
- `POST /import/start` → triggers background import, returns immediately.
- `GET /import/status` → `{status, tracks_imported, artists_imported, started_at}`.
- `GET /library` → paginated list of saved + liked tracks with metadata (reads from DB).
- `GET /search?q=&type=` → proxies to Spotify Search, returns tracks or artists (does not persist results).

**Acceptance criteria**
- After running import, `user_track_data` contains rows for all imported tracks.
- `/import/status` reflects progress in real time during import.
- Import is idempotent: running it twice does not create duplicate rows.
- `/library` returns only tracks where `is_saved=true OR feedback='like'`.
- `/search` returns results from Spotify but writes nothing to DB.

**Notes**
_Orchestrator fills after completion._
