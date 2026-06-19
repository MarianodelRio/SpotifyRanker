---
id: T-018
phase: 2
agent: ML/Ranking
depends_on: [T-006, T-010]
status: TODO
branch: ""
pr: ""
---

### T-018 — Training dataset builder
**Phase:** 2 | **Agent:** ML/Ranking | **Depends on:** T-006, T-010

Build the module that constructs the labeled training dataset from all user signals in the database, applying the weight table from `design.md` section 10.

**Scope — `libs/ml/training_set.py`**
`build_training_set(session, profile: UserProfile) → list[TrainingExample]`:
- Reads all rows from `user_track_data` joined with track/artist/genre data.
- Assigns label (0.0–1.0) and weight per row using the signal weight table from `design.md` section 10 (saved=1.0/1.0, app_like=1.0/1.0, top_short_1_10=0.95/0.9, etc.).
- Returns a list of `TrainingExample` with `user_features`, `track_features`, `label`, `weight`.

**Acceptance criteria**
- An imported library of 200 tracks produces ≥ 200 training examples.
- Labels and weights match the table in `design.md` section 10 exactly.
- A track with both a save and a top position gets the highest label across both signals (no double-counting the same signal with different weights).
- Tested with a fixture DB populated with known signals.

**Notes**
_Orchestrator fills after completion._
