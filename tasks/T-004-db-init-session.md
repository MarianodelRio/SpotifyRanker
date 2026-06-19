---
id: T-004
phase: 0
agent: Data
depends_on: [T-003]
status: TODO
branch: ""
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
_Orchestrator fills after completion._
