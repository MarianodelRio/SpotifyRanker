# TasteRanker — CLAUDE.md

## Project Overview

**TasteRanker** is a personal music discovery engine connected to Spotify. It reads the user's library, listening history, and playlists; builds a taste profile using a Two-Tower deep learning model; and generates personalized discovery playlists that Spotify doesn't offer natively. Music plays directly in the browser via the Spotify Web Playback SDK.

Core differentiator: a fully transparent, user-controllable recommendation pipeline (candidate generation → Two-Tower ranking → playlist export) that does not depend on Spotify's restricted recommendation endpoints.

Single-user, local-first. No cloud deployment in MVP.

---

## Current Architecture

**Modular monolith.** Modules communicate only through shared domain models in `libs/common/`. No microservices in v0.

```
apps/
  api/              ← FastAPI HTTP entry point (routers, DI, config)
  frontend/         ← React + Vite + TypeScript UI (three-panel layout)

libs/
  common/           ← PROTECTED: shared Pydantic models and enums
  spotify/          ← Spotify API adapter (pure I/O, no business logic)
  profile/          ← UserProfile builder (stateless, pure functions)
  candidates/       ← Candidate track generation (stateless)
  ml/               ← Feature engineering, Two-Tower training and inference
  ranker/           ← Scoring, mode configuration, diversification
  playlist/         ← Playlist assembly and Spotify export
  feedback/         ← Feedback persistence and retraining trigger

db/                 ← SQLAlchemy engine, session factory, ORM models, repositories
models_store/       ← Trained PyTorch model files (user_tower.pt, item_tower.pt)
tests/              ← All tests (unit, integration, fixtures)
scripts/            ← Dev CLI utilities (not production code)
docs/               ← Technical documentation
```

**Dependency graph (DAG, no reverse imports allowed):**
```
common
  ↑
  ├── spotify          (I/O only)
  ├── profile          (stateless, reads from DB)
  ├── ml               (feature engineering + Two-Tower model)
  │
  ├── candidates       (uses spotify + profile)
  ├── ranker           (uses ml + profile)
  │
  ├── playlist         (uses spotify + ranker)
  ├── feedback         (reads/writes DB only)
  │
  └── api              (orchestrates all modules)
```

---

## Development Commands

```bash
# Full stack (recommended)
docker compose up                  # starts api (:8000) + frontend (:5173)
docker compose up api              # backend only
docker compose up frontend         # frontend only

# Without Docker — Python environment
pip install -e ".[dev]"            # install all deps
uvicorn apps.api.main:app --reload # run backend

# Without Docker — Frontend
cd apps/frontend
npm install
npm run dev                        # run frontend dev server

# Database
python db/init_db.py               # create SQLite tables (runs automatically in Docker)
```

---

## Testing Commands

```bash
pytest                             # all tests
pytest tests/unit/                 # unit tests only
pytest tests/integration/          # integration tests only
pytest --cov=libs --cov-report=term-missing  # with coverage
pytest -x                          # stop on first failure
```

**Coverage target:** 70% minimum on `libs/` for any merge.

---

## Linting Commands

```bash
ruff check .                       # lint
ruff format .                      # format
mypy libs/ apps/api/               # type checking (strict on core modules)

# Frontend
cd apps/frontend
npm run lint                       # eslint
npx tsc --noEmit                   # type check
```

All four must pass before any merge to `master`.

---

## Folder Ownership

| Folder | Owner Agent | Notes |
|--------|-------------|-------|
| `libs/common/` | **Architect only** | PROTECTED — requires explicit approval to change |
| `libs/spotify/` | backend-api | Pure I/O adapter, owned alongside apps/api/ |
| `libs/profile/` | domain-core | Stateless profile builder |
| `libs/candidates/` | domain-core | Candidate generation strategies |
| `libs/ml/` | recommendation-ranking | Two-Tower feature engineering, training, inference |
| `libs/ranker/` | recommendation-ranking | Scoring, mode weights, diversification |
| `libs/playlist/` | domain-core | Assembly and export |
| `libs/feedback/` | data-persistence | Feedback persistence and retraining trigger |
| `apps/api/` | backend-api | HTTP layer only |
| `apps/frontend/` | frontend | React UI, Spotify Web Playback SDK |
| `db/` | data-persistence | ORM models, repositories, migrations |
| `models_store/` | recommendation-ranking | Trained PyTorch model files |
| `tests/` | testing | All tests |
| `docs/` | docs | Documentation |
| `.github/` | devops | CI/CD |

---

## Shared Contracts Policy

`libs/common/models.py` and `libs/common/enums.py` are **protected files**.

Rules:
1. No agent modifies them without explicit human approval.
2. The Architect Agent must review and approve all changes.
3. Any change to contracts requires updating the TypeScript types in `apps/frontend/src/types/api.ts`.
4. Any breaking change requires updating all consuming modules in the same PR.
5. If your feature needs a new model field, propose it before coding.

---

## Branch Policy

```
master                        ← always stable, all checks passing
feature/T-XXX-short-slug      ← one branch per task (Orchestrator creates these)
```

Never commit directly to `master`. Every change goes through a PR.

**Exception:** `tasks/*.md` files are coordination metadata, not production code. The Orchestrator, PR Reviewer, and `/done` command commit task status updates (`IN_PROGRESS`, `READY_FOR_PR`, `PR_OPEN`, `DONE`) directly to master so all agents see real-time state. Only `tasks/` files may be pushed directly to master — everything else requires a PR.

The existence of a remote branch `feature/T-XXX-*` is the coordination signal between parallel agents — it means that task is claimed. Branch creation in Step 4 is the claim; other agents skip tasks with an active branch.

Each agent works in its own git worktree (`../spotify_ranker-T-XXX/`), not in the main repo. The main repo stays on `master` and is used only for workflow commands (`/orchestrate`, `/status`, `/prepare-pr`). See `docs/parallel_development.md` for the full setup.

Task lifecycle: `TODO → IN_PROGRESS → READY_FOR_PR → PR_OPEN → DONE`

Task status lives in the frontmatter of each `tasks/T-XXX-slug.md` file — not in a shared Status Board.
See `tasks/` for all task definitions and current status. See `plan.md` for the dependency graph.

---

## Agent Usage Policy

See `docs/agent_workflow.md` for the full workflow definition.

**Primary workflow:** Orchestrator loop — sync main, read `tasks/*.md`, human checkpoint, implement, push, mark `READY_FOR_PR`. See `.claude/agents/orchestrator.md`.

**Quick rules:**
- Every task is executed via the Orchestrator protocol (`/orchestrate`).
- One agent per folder/module. Never two agents editing the same file simultaneously.
- Every coding task must include tests in the same PR.
- No agent touches `libs/common/` without Architect approval.
- No agent touches files outside its assigned folders.
- Human must approve the plan before implementation starts (mandatory checkpoint).
- Orchestrator reaches `READY_FOR_PR` — it never opens PRs.
- PR Reviewer opens PRs when the human runs `/prepare-pr` — it never marks tasks `DONE`.
- Human merges PRs and runs `/done T-XXX` to mark tasks `DONE`. The skill also reports which tasks are now unblocked.

---

## Rules for Not Modifying Unrelated Files

- An agent working on `libs/ranker/` must not touch `libs/spotify/` even if it sees an improvement.
- Any change outside the assigned folders requires explicit mention in the PR description with justification.
- Linting/formatting fixes on unrelated files are allowed only if done in a separate commit labeled "chore: format".
- Never refactor code not directly related to the current task.

---

## Rules for Updating Docs

- When you add a new API endpoint → update `docs/api.md`.
- When you change the ranking model or mode weights → update `docs/scoring.md`.
- When you make an architectural decision → create or update an ADR in `docs/adr/`.
- When you change setup instructions → update `README.md`.
- The Docs Agent owns `docs/` but any agent must keep docs in sync with their code changes.

---

## Rules for Test Coverage

- Every new function in `libs/` must have at least one unit test.
- Every new API endpoint must have at least one integration test.
- Unit tests must not require network access or a real database.
- Integration tests mock the Spotify API using fixtures in `tests/fixtures/spotify_responses/`.
- Coverage on `libs/` must not drop below 70% on any merge.
- Property tests are encouraged for ML and ranker modules (score always in expected range, etc.).

---

## Rules for Asking Before Destructive Actions

Ask before:
- Modifying `libs/common/models.py` or `libs/common/enums.py`.
- Changing `db/models.py` in a way that requires a migration.
- Deleting any existing test.
- Modifying the Two-Tower architecture in `libs/ml/models/`.
- Modifying `pyproject.toml` to remove a dependency.
- Force-pushing or rebasing shared branches.

Do not ask — just do it:
- Adding new fields to models (non-breaking).
- Adding new test files.
- Adding new source files in assigned folders.
- Formatting and linting fixes.
