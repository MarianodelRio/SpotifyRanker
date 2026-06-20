---
id: T-018
phase: 2
agent: ML/Ranking
depends_on: [T-006, T-010]
status: DONE
branch: feature/T-018-training-dataset
pr: "https://github.com/MarianodelRio/SpotifyRanker/pull/13"
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
- `TrainingExample` dataclass defined in `libs/ml/training_set.py` (not in `libs/common/`) since it's ML-internal; `user_features`/`track_features` are empty numpy arrays — T-020 populates them via T-017's feature builders.
- Signal weight table applied exactly as in design.md §10; max-label-wins rule prevents double-counting when multiple signals apply to the same track.
- Skip detection reads eager-loaded `PlayEvent.ms_played / Track.duration_ms < 0.1`.
- 14 unit tests cover all signal combinations, the 200-track count guarantee, and max-label tie-break logic.
- The `profile` parameter is accepted for API consistency but not used in T-018; T-020 uses it to compute user feature vectors.
- PR Reviewer: fixed trivially-true `isinstance(x, type(x))` assertions in test — replaced with `isinstance(x, np.ndarray)`; added missing `import numpy as np` to test file. No production code changed.
- Declared-artist and declared-playlist signals from design.md §10 are not implemented — DB schema has no SaveSource values for them. These will need to be added in a follow-up task when artist/playlist declaration features land.
