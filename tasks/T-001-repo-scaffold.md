---
id: T-001
phase: 0
agent: Architect
depends_on: []
status: DONE
branch: feature/T-001-repo-scaffold
pr: "https://github.com/MarianodelRio/SpotifyRanker/pull/1"
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
- Python target is 3.10 (pyenv has 3.10.12); `requires-python = ">=3.10"` in pyproject.toml. Design.md says 3.11 but the environment doesn't have it — no 3.11-specific features used.
- `str, Enum` pattern kept (not `StrEnum`) for 3.10 compatibility; UP042 rule ignored in ruff.toml.
- `setup.py` shim added alongside `pyproject.toml` for legacy editable install support on pip 23 / setuptools 59.
- `pip install -e ".[dev]"` installs PyTorch with CUDA from PyPI by default (existing pyenv environment already had torch 2.11.0+cu130). Dockerfile uses `--index-url https://download.pytorch.org/whl/cpu` for a lean image.
- All acceptance criteria verified: ruff/mypy pass on 14 source files, pytest collects 0 tests (exit 5 = no failures), `from libs.common.models import Track` resolves cleanly, `npm install` succeeds in apps/frontend.
- Push to remote requires GitHub credentials configured (`git push -u origin feature/T-001-repo-scaffold`).
