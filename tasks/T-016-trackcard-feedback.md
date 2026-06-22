---
id: T-016
phase: 1
agent: Frontend
depends_on: [T-015, T-009]
status: DONE
branch: feature/T-016-trackcard-feedback
pr: "https://github.com/MarianodelRio/SpotifyRanker/pull/22"
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
- `FeedbackContext` / `FeedbackProvider` added at `src/context/FeedbackContext.tsx` — wraps `PlayerProvider` children in `App.tsx`. Keyed by `spotify_id`. State is `Record<string, 'like' | 'dislike' | null>`.
- `useFeedback` hook at `src/hooks/useFeedback.ts` — throws if used outside `FeedbackProvider`.
- Optimistic update: state is applied immediately; on API error the previous value is restored (revert, not clear).
- `TrackCard` buttons use `stopPropagation` to prevent click from triggering play; the outer `div` still handles row-click → play.
- `PlayerPanel` reads `currentSource` from `PlayerContext` (already in `PlayerContextValue`) to pass the correct source when submitting feedback.
- `tsc --noEmit` and `eslint` both pass clean.
- Like shows filled ♥ (green), dislike shows ✕ (red); neutral shows ♡ / ✕ in muted zinc.
- PR Reviewer note: T-016 core implementation (`19fc061`) was merged to master via PR #21 (T-020 training loop) due to git branch contamination during parallel orchestration. PR #22 formally closes T-016 and adds only the `App.tsx` indentation fix (FeedbackProvider nesting). All acceptance criteria were verified in the feature branch diff; `tsc` and `eslint` pass clean.
- PR Reviewer note: `useCallback` in `FeedbackContext` depends on `feedbackMap` — this recreates `submitFeedback` on each feedback action, causing re-renders in consumers. Acceptable for current scale; worth noting for future optimization.
