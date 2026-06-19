---
id: T-001
phase: 0
agent: Architect
depends_on: []
status: TODO
branch: ""
pr: ""
---

### T-001 — Repo setup and project scaffold
**Phase:** 0 | **Agent:** Architect | **Depends on:** —

Create the complete repository skeleton. No implementation — just structure, configuration, and tooling.

**Scope**
- All folders from `design.md` section 6: `apps/api/`, `apps/frontend/`, `libs/*/`, `db/`, `models_store/`, `tests/`, `scripts/`, `docs/`.
- `pyproject.toml` with all Python dependencies (FastAPI, SQLAlchemy, PyTorch, httpx, pytest, ruff, mypy, etc.).
- `apps/frontend/package.json` with all JS dependencies (React 18, TypeScript, Vite, Tailwind CSS).
- `.env.example` with `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`, `SPOTIFY_REDIRECT_URI`, `DATABASE_URL`.
- `pytest.ini` or `pyproject.toml` test config, `ruff.toml`, `mypy.ini`.
- `__init__.py` in every Python package folder.
- `README.md` with setup and run instructions.
- `Dockerfile` — multi-stage image for the backend (Python 3.11 slim, PyTorch CPU-only).
- `apps/frontend/Dockerfile` — Node image for the Vite dev server.
- `docker-compose.yml` — orchestrates `api` (:8000) and `frontend` (:5173); mounts the SQLite file and `models_store/` as volumes.
- `.dockerignore` — excludes `__pycache__`, `.env`, `models_store/*.pt`, `node_modules`, `.git`.

**Acceptance criteria**
- `pip install -e ".[dev]"` completes without errors.
- `npm install` in `apps/frontend/` completes without errors.
- `ruff check .` and `mypy libs/ apps/api/` run without errors (on empty files).
- `pytest` runs and collects 0 tests (no failures).
- `from libs.common.models import Track` does not raise ImportError.
- `docker compose up` starts both services without errors.
- API responds at `http://localhost:8000/docs`.
- Frontend responds at `http://localhost:5173`.

**Notes**
_Orchestrator fills after completion._
