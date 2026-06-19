---
id: T-009
phase: 1
agent: Data
depends_on: [T-006]
status: TODO
branch: ""
pr: ""
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
_Orchestrator fills after completion._
