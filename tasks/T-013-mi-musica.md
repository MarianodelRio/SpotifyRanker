---
id: T-013
phase: 1
agent: Frontend
depends_on: [T-012, T-008]
status: TODO
branch: ""
pr: ""
---

### T-013 — Mi música section
**Phase:** 1 | **Agent:** Frontend | **Depends on:** T-012, T-008

Build the Mi música section showing the user's saved and liked tracks.

**Scope**
- Calls `GET /library` (paginated) to load saved + liked tracks.
- Shows import status banner while import is running (`GET /import/status`). Includes a "Refresh" button that calls `POST /import/start`.
- Renders a scrollable list of `TrackCard` components (placeholder style at this point — full TrackCard built in T-016).
- Infinite scroll or "load more" pagination.
- Empty state: shown if library has 0 tracks, with a prompt to trigger an import.

**Acceptance criteria**
- Import status banner shows during import and disappears when completed.
- Track list updates after import completes (re-fetches on status change).
- Pagination loads more tracks on scroll.
- Empty state renders correctly before first import.

**Notes**
_Orchestrator fills after completion._
