---
id: T-028
phase: 3
agent: Backend/API
depends_on: [T-027]
status: TODO
branch: ""
pr: ""
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
_Orchestrator fills after completion._
