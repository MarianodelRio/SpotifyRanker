---
id: T-012
phase: 1
agent: Frontend
depends_on: [T-011, T-005]
status: DONE
branch: feature/T-012-auth-flow-frontend
pr: "https://github.com/MarianodelRio/SpotifyRanker/pull/12"
---

### T-012 — Auth flow frontend
**Phase:** 1 | **Agent:** Frontend | **Depends on:** T-011, T-005

Connect the frontend to the backend OAuth flow. After this task, the user can log in with Spotify and the app knows who they are.

**Scope**
- Login page shown when `GET /auth/status` returns `is_authenticated: false`.
- "Login with Spotify" button redirects to `GET /auth/login` (backend-driven redirect).
- After OAuth callback, backend stores the token. Frontend re-checks `/auth/status` and enters the app.
- User display name shown in header (from `/auth/status`).
- `GET /auth/token` called to initialize the Spotify Web Playback SDK (token fetched before SDK init).
- Logout button calls `POST /auth/logout` and returns to login page.

**Acceptance criteria**
- Full login flow works end-to-end in a browser.
- App does not render its main layout until `is_authenticated: true`.
- Token retrieved from `/auth/token` and available in app state for SDK initialization.
- Logout clears auth state and returns to login page.

**Notes**
- Auth state managed via `useAuth` hook (checks `/auth/status` on mount, fetches SDK token when authenticated).
- `AuthContext` split across two files to satisfy `react-refresh/only-export-components` lint rule: `context/auth-context.ts` (non-JSX, exports the context object) and `context/AuthContext.tsx` (exports only the `AuthProvider` component).
- `useAuthContext` hook in its own `hooks/useAuthContext.ts` file for the same reason.
- `token` from `GET /auth/token` is stored in auth state and available via `useAuthContext()` for the Spotify Web Playback SDK (T-015).
- `LoginPage` redirects to `http://localhost:8000/auth/login` (hardcoded backend URL, consistent with the `apiFetch` base URL).
- `tsc --noEmit` and `eslint --max-warnings 0` both pass. `node_modules` were missing from the main repo and installed via `docker run node:18-alpine npm install`.
- PR Reviewer: rebase produced one mechanical conflict in the task file (IN_PROGRESS vs READY_FOR_PR metadata — resolved to keep READY_FOR_PR). The claim commit was absorbed into master's history; only the implementation commit remains. All 5 checks pass (153 pytest, ruff, mypy, tsc, eslint). One criterion requires manual browser testing: end-to-end OAuth flow with a running backend.
