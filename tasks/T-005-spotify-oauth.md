---
id: T-005
phase: 0
agent: Backend/API
depends_on: [T-004]
status: TODO
branch: ""
pr: ""
---

### T-005 — Spotify OAuth PKCE
**Phase:** 0 | **Agent:** Backend/API | **Depends on:** T-004

Implement the full Spotify OAuth 2.0 PKCE flow. This is the authentication foundation — nothing else works without it.

**Scope — `libs/spotify/auth.py`**
- PKCE code verifier and challenge generation.
- Build the Spotify authorization URL with required scopes: `user-library-read`, `user-top-read`, `user-read-playback-state`, `streaming`, `playlist-modify-public`, `playlist-modify-private`.
- Exchange authorization code for access + refresh tokens.
- Token refresh logic (call Spotify token endpoint with refresh token).

**Scope — `apps/api/routers/auth.py`**
- `GET /auth/login` → redirect to Spotify authorization URL.
- `GET /auth/callback` → exchange code, store tokens in `auth` table.
- `GET /auth/status` → `{is_authenticated, display_name}`.
- `POST /auth/logout` → clear tokens from DB.
- `GET /auth/token` → return fresh access token (auto-refresh if expired).

**Acceptance criteria**
- Full login flow works end-to-end in a browser: navigate to `/auth/login` → Spotify → callback → token stored in DB.
- `/auth/token` returns a valid access token after login.
- `/auth/status` correctly returns `is_authenticated: true` after login.
- Token is automatically refreshed when expired (test with a manually expired token).

**Notes**
_Orchestrator fills after completion._
