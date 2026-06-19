---
id: T-027
phase: 3
agent: Data
depends_on: [T-009, T-020]
status: TODO
branch: ""
pr: ""
---

### T-027 — Retraining trigger
**Phase:** 3 | **Agent:** Data | **Depends on:** T-009, T-020

Add automatic retraining logic to the feedback pipeline. Every 20 new feedback events triggers a background retraining job.

**Scope — `libs/feedback/trigger.py`**
- `check_and_trigger(session, background_tasks)`: called after every `POST /feedback`. Counts new feedback events since last retraining. If count ≥ 20, launches `trainer.train()` as a FastAPI background task.
- Retraining status is stored in a simple state file (or a row in `auth` table): `last_trained_at`, `training_in_progress` flag.
- While retraining is in progress, additional triggers are debounced (not stacked).

**Acceptance criteria**
- Posting 20 feedback events (one at a time) triggers exactly one background retrain.
- The 21st feedback does not trigger a second retrain if the first is still running.
- After retraining completes, the counter resets to 0.
- Retraining runs in the background and does not block the API response.

**Notes**
_Orchestrator fills after completion._
