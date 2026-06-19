---
id: T-011
phase: 1
agent: Frontend
depends_on: [T-001]
status: READY_FOR_PR
branch: feature/T-011-react-app-shell
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
- Installed react-router-dom v6.30.4 (not v7 — v7 requires Node >=20, which conflicts with the current local Node 16 toolchain; Docker uses >=18 so either would run, but v6 is more conservative for now).
- `src/types/api.ts` mirrors the design.md spec rather than the current stub `libs/common/models.py` (which is still being filled in by T-002). When T-002 merges, the types file should be validated against the final Pydantic models.
- All API domain modules (`auth.ts`, `library.ts`, etc.) are fully typed and structured for real fetch calls — they will 404 until backend endpoints are implemented. No mock data.
- `tailwind.config.js` gains `darkMode: 'class'` for future dark/light toggling.
- `npx tsc --noEmit` and `eslint` both pass clean with zero warnings.
