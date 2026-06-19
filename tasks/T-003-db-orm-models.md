---
id: T-003
phase: 0
agent: Data
depends_on: [T-002]
status: READY_FOR_PR
branch: feature/T-003-db-orm-models
pr: ""
---

### T-003 — DB ORM models
**Phase:** 0 | **Agent:** Data | **Depends on:** T-002

Define all SQLAlchemy ORM models in `db/models.py`. These map to the 10-table schema in `design.md` section 7.

**Scope**
All 10 tables: `artists`, `genres`, `artist_genres`, `albums`, `tracks`, `track_artists`, `user_track_data`, `play_events`, `playlists`, `playlist_tracks`, `auth`.

Key constraints to implement:
- UUID primary keys (use `uuid.uuid4` default).
- `UNIQUE` on all `spotify_id` columns.
- Composite PKs on join tables (`artist_genres`, `track_artists`, `playlist_tracks`).
- `UNIQUE(playlist_id, rank)` and `UNIQUE(playlist_id, track_id)` on `playlist_tracks`.
- `updated_at` auto-updated on every write (use `onupdate` in SQLAlchemy).
- All FK relationships declared with `relationship()` for lazy loading.

**Acceptance criteria**
- `from db.models import Track, Artist, Playlist` works.
- All column types, constraints, and relationships match `design.md` section 7 exactly.
- No business logic inside ORM models (data holders only).
- Full mypy pass.

**Notes**
- `SaveSource` enum (`spotify | app`) fue agregado a `libs/common/enums.py` (aprobado explícitamente — no estaba en T-002). El tipo TypeScript correspondiente fue agregado a `apps/frontend/src/types/api.ts`.
- `auth` usa `spotify_user_id` como PK natural (sin UUID) según el schema de `design.md`.
- `playlist_tracks` tiene PK UUID extra para facilitar referencias, más las dos UNIQUE constraints compuestas requeridas.
- Todos los Enum SQLAlchemy usan nombre explícito (`name=`) para evitar colisiones en SQLite.
- `score_breakdown` tipado como `dict[str, float] | None` para pasar mypy en modo strict.
