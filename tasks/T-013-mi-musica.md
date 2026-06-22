---
id: T-013
phase: 1
agent: Frontend
depends_on: [T-012, T-008]
status: READY_FOR_PR
branch: feature/T-013-mi-musica
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
Two new files only — no changes outside `apps/frontend/src/sections/MiMusica/`:
- `useImportPoller.ts`: polls `GET /import/status` every 3s while status is `running`; fires a `justCompleted` pulse when transitioning out of `running` so the track list re-fetches automatically.
- `index.tsx`: import banner (shows while running or failed, hides otherwise), "Sync library" button in header when idle, loading skeleton (8 animated rows), empty state with "Import from Spotify" CTA, paginated track list with "Load more" button, and total-count footer when all pages loaded.
- All API calls go through existing `src/api/library.ts` functions. `TrackCard` used as-is.
- `tsc --noEmit` and ESLint pass clean.
