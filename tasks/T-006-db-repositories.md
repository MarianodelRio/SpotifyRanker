---
id: T-006
phase: 1
agent: Data
depends_on: [T-004]
status: TODO
branch: ""
pr: ""
---

### T-006 — DB repositories
**Phase:** 1 | **Agent:** Data | **Depends on:** T-004

Build the repository layer. All DB reads and writes in the entire application must go through these repositories — no other module accesses the ORM models directly.

**Scope**
One repository class per major entity: `TrackRepository`, `ArtistRepository`, `AlbumRepository`, `GenreRepository`, `UserTrackDataRepository`, `PlayEventRepository`, `PlaylistRepository`, `AuthRepository`.

Each repository receives a `Session` in its constructor. Exposes methods needed by Phase 1 features — not more. Typical methods: `get_by_id`, `get_by_spotify_id`, `upsert` (insert or update on conflict), entity-specific queries (e.g. `get_saved_tracks`, `get_top_artists`).

**Acceptance criteria**
- All repositories tested against in-memory SQLite (no file, no network).
- `upsert_track` and `upsert_artist` handle duplicate `spotify_id` without errors.
- No repositories import from any `libs/` module other than `common/`.
- Full mypy pass.

**Notes**
_Orchestrator fills after completion._
