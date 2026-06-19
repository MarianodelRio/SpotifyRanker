---
id: T-011
phase: 1
agent: Frontend
depends_on: [T-001]
status: TODO
branch: ""
pr: ""
---

### T-011 — React app shell
**Phase:** 1 | **Agent:** Frontend | **Depends on:** T-001

Build the application layout and navigation skeleton. No real data yet — components use placeholder content.

**Scope**
- Vite + React + TypeScript project initialized in `apps/frontend/`.
- Tailwind CSS configured.
- Three-panel layout: `Sidebar` (left, fixed) + `TrackList` (center, scrollable) + `PlayerPanel` (right, fixed). Matches the wireframe in `design.md` section 9.
- `Header` with app logo and placeholder user name slot.
- `Sidebar` with navigation links: Mi música, Buscar, Descubrir.
- Client-side routing (React Router or similar) switching center column content per section.
- `apps/frontend/src/types/api.ts` with TypeScript types mirroring `libs/common/models.py`.
- `apps/frontend/src/api/client.ts` — typed API client wrapper (fetch-based, placeholder methods, no real calls yet).

**Acceptance criteria**
- `npm run dev` starts the app with no errors.
- Navigating Sidebar links switches the center column content.
- `npx tsc --noEmit` and `npm run lint` pass with no errors.
- No placeholder `console.log` statements.

**Notes**
_Orchestrator fills after completion._
