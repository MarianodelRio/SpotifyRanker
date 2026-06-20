---
id: T-006
phase: 1
agent: Data
depends_on: [T-004]
status: DONE
branch: feature/T-006-db-repositories
pr: "https://github.com/MarianodelRio/SpotifyRanker/pull/7"
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
- All 8 repositories in `db/repositories/`, one file per entity. `__init__.py` re-exports all for clean imports.
- Upserts use `sqlalchemy.dialects.sqlite.insert(...).on_conflict_do_update()` — no try/except, atomic.
- `id` and `created_at` not in `set_={}` on any upsert — internal UUIDs are stable across reimports.
- `play_count` intentionally absent from `UserTrackDataRepository.upsert()` — managed by feedback processor (T-009).
- `AuthRepository.get_auth()` is argless (single-user, returns first row with `.limit(1)`).
- `get_top_by_affinity()` joins `track_artists → user_track_data`, orders by `SUM(play_count)`.
- **PR Reviewer notes**: `PlaylistRepository.create()` and `PlayEventRepository.append()` accept `mode`/`source` as `str` rather than the enum types — functionally fine for SQLAlchemy but reduces type safety. Not a blocker; can be tightened in a later task. The `assert row is not None` guards after upsert+select are technically stripped by `-O` but are acceptable in this internal DB layer.
- 78 tests pass (33 new). mypy, ruff clean. 92% coverage on `db/repositories/`.
