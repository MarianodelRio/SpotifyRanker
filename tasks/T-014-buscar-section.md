---
id: T-014
phase: 1
agent: Frontend
depends_on: [T-012, T-008]
status: READY_FOR_PR
branch: feature/T-014-buscar-section
pr: ""
---

### T-014 — Buscar section
**Phase:** 1 | **Agent:** Frontend | **Depends on:** T-012, T-008

Build the Buscar section for searching the Spotify catalog.

**Scope**
- Search input at the top. Calls `GET /search?q=&type=track` on each query (debounced).
- Results displayed as a list of `TrackCard` components.
- Results are not persisted — cleared when the user navigates away or clears the input.
- Clicking a track plays it (via the PlayerPanel, which is the shared player state).
- No like/dislike in search results at this stage (handled by T-016's TrackCard).

**Acceptance criteria**
- Typing in the search box fetches results from `/search` (with debounce).
- Results clear when the input is cleared or section is left.
- Clicking a track triggers playback in the PlayerPanel.
- Empty query shows empty state (not a search).

**Notes**
- Replaced the stub with a full implementation: controlled input, 300ms debounce via `useEffect`, `searchTracks()` from the existing API client.
- Results rendered as `TrackCard` list with `source="search"`.
- Empty state (no query), loading state, error state, and no-results state all handled.
- Results clear naturally on component unmount (component state); cleanup also cancels any pending debounce timer.
- No new types, API functions, or dependencies introduced — all contracts were already in place.
