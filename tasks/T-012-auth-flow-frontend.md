---
id: T-012
phase: 1
agent: Frontend
depends_on: [T-011, T-005]
status: TODO
branch: ""
pr: ""
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
_Orchestrator fills after completion._
