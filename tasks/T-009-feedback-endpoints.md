---
id: T-009
phase: 1
agent: Data
depends_on: [T-006]
status: DONE
branch: feature/T-009-feedback-endpoints
pr: "https://github.com/MarianodelRio/SpotifyRanker/pull/10"
---

### T-009 — Feedback + play event endpoints
**Phase:** 1 | **Agent:** Data | **Depends on:** T-006

Implement feedback persistence and play event recording. These are the two main write paths from user interactions.

**Scope — `libs/feedback/processor.py`**
- `record_feedback(entry: FeedbackEntry)`: upserts into `user_track_data` (one row per track). Updates `feedback` and `feedback_at`. If track not yet in DB, creates a minimal `user_track_data` row.
- `record_play_event(track_id, ms_played, source, playlist_id)`: appends to `play_events`, increments `play_count` and updates `last_played_at` in `user_track_data`.

**Scope — API endpoints**
- `POST /feedback` → `{track_id, feedback_type, source, playlist_id?}` → calls `record_feedback`.
- `POST /player/event` → `{track_id, ms_played, source, playlist_id?}` → calls `record_play_event`.

**Acceptance criteria**
- Posting like for a track creates or updates `user_track_data.feedback = 'like'`.
- Posting dislike overwrites a previous like on the same track.
- Play events append (do not overwrite): multiple events per track are all stored.
- `play_count` increments correctly on each play event.

**Notes**
- `record_play_event` uses a single transaction: `play_events` append + `user_track_data` upsert (play_count increment, last_played_at) commit together atomically.
- `play_count` increment uses SQLite `user_track_data.play_count + 1` via `text()` inside `on_conflict_do_update` — no read-modify-write race.
- `apps/api/routers/feedback.py` was added outside Data agent's usual `libs/feedback/` scope, justified by the task definition explicitly listing the API endpoints in scope. The router is thin wiring only.
- Enum names use lowercase (`FeedbackType.like`, `PlaySource.my_music`) matching `libs/common/enums.py`.
- 8 unit tests added, all passing. 121 total tests pass post-rebase. mypy, ruff clean. `libs/feedback/processor.py` 100% coverage.
- PR Reviewer: rebase was clean after resolving one mechanical conflict (task file status claim vs READY_FOR_PR on master). No design conflicts.
- Watch: no HTTP-level integration tests for the endpoints — wiring is tested only by full suite passing. No FK validation in the endpoint (caller must pass a valid `track_id`).
