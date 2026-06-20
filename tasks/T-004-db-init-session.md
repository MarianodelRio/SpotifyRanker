---
id: T-004
phase: 0
agent: Data
depends_on: [T-003]
status: READY_FOR_PR
branch: feature/T-004-db-init-session
pr: ""
---

### T-004 — DB init and session factory
**Phase:** 0 | **Agent:** Data | **Depends on:** T-003

Create the database engine, session factory, and initialization script.

**Scope**
- `db/engine.py`: SQLAlchemy async engine pointed at `DATABASE_URL` from `.env`. Session factory with `expire_on_commit=False`.
- `db/init_db.py`: script that creates all tables from ORM models (runs `Base.metadata.create_all`). Safe to run multiple times.
- `db/session.py`: FastAPI-compatible dependency (`get_db`) that yields a session and commits/rolls back correctly.

**Acceptance criteria**
- `python db/init_db.py` creates `tasteranker.db` with all 10 tables.
- `get_db()` yields a usable session in a FastAPI dependency context.
- Running `init_db.py` twice does not raise errors (idempotent).

**Notes**
- Added `aiosqlite>=0.20.0` to `pyproject.toml` (required by SQLAlchemy async engine for SQLite; was missing from dependencies).
- WAL mode is enabled via a sync-engine event listener on SQLite connections — allows concurrent reads during background import.
- `init_db.py` uses `conn.run_sync(Base.metadata.create_all)` via the async engine so no separate sync engine is needed.
- `get_db()` commits on success and rolls back on any exception before re-raising — FastAPI dependency injection compatible.
- Table count in tests is 11 (auth + 10 domain tables); design.md schema section lists auth separately but it is part of the same `Base`.
