---
id: T-028
phase: 3
agent: Backend/API
depends_on: [T-027]
status: PR_OPEN
branch: feature/T-028-model-endpoints
pr: "https://github.com/MarianodelRio/SpotifyRanker/pull/28"
---

### T-028 — Model train/status endpoints
**Phase:** 3 | **Agent:** Backend/API | **Depends on:** T-027

Expose the model management API endpoints.

**Scope — `apps/api/routers/model.py`**
- `POST /model/train` → manually triggers retraining (launches background task). Returns `{status: 'started'}` immediately.
- `GET /model/status` → `{trained_at, examples_count, training_in_progress, last_loss}`.

**Acceptance criteria**
- `POST /model/train` returns immediately and starts training in the background.
- `GET /model/status` reflects `training_in_progress: true` while training is running.
- After training completes, `trained_at` and `examples_count` are updated.
- If no model has been trained yet, `GET /model/status` returns a clear state (not an error).

**Notes**
- Router file created as `apps/api/routers/model_router.py` (task spec said `model.py` but convention in the project is `*_router.py` suffix — applied consistently).
- `POST /model/train` returns `{status: "already_running"}` if `training_in_progress` is already set, avoiding concurrent retrains.
- `_run_manual_retrain()` extends `models_store/training_state.json` with `last_loss` and `examples_count` after training; the auto-trigger path (`libs/feedback/trigger.py`) is unchanged and leaves those fields unset (null) — both paths share the same state file safely via the `training_in_progress` guard.
- 9 integration tests added covering: no-model state, full state, in-progress flag, corrupt file, started/already-running guards, success path, and failure path (flag cleared on exception).
- All 293 tests pass; ruff and mypy clean.
- PR Reviewer: rebase was clean except for a mechanical conflict in `tasks/T-028-model-endpoints.md` frontmatter (IN_PROGRESS vs READY_FOR_PR) — resolved by keeping master's state. All checks confirmed green on the rebased branch. No scope violations or design concerns found.
