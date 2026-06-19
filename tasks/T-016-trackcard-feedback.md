---
id: T-016
phase: 1
agent: Frontend
depends_on: [T-015, T-009]
status: TODO
branch: ""
pr: ""
---

### T-016 — TrackCard + feedback UI
**Phase:** 1 | **Agent:** Frontend | **Depends on:** T-015, T-009

Build the final `TrackCard` component with like/dislike buttons, and add like/dislike buttons to the `PlayerPanel`.

**Scope**
- `TrackCard`: album art (small), title, artist, duration. Click → plays track. Like (♥) and dislike (✕) buttons.
- Clicking like or dislike calls `POST /feedback` and updates visual state immediately (optimistic update).
- If the user changes from like to dislike (or vice versa), the previous feedback is overwritten.
- Player panel also shows like/dislike buttons for the currently playing track.
- Liked tracks show a filled heart icon; disliked tracks show a visual indicator.

**Acceptance criteria**
- Liking a track sends `POST /feedback` with `feedback_type: 'like'`.
- Disliking sends `feedback_type: 'dislike'`.
- Visual state updates immediately, without waiting for the server response.
- Changing from like to dislike on the same track sends the update (not a duplicate).
- Player panel buttons stay in sync with the TrackCard buttons for the same track.

**Notes**
_Orchestrator fills after completion._
