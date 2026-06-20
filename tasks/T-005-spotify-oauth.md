---
id: T-005
phase: 0
agent: Backend/API
depends_on: [T-004]
status: DONE
branch: feature/T-005-spotify-oauth
pr: "https://github.com/MarianodelRio/SpotifyRanker/pull/8"
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
- PKCE `code_verifier` stored in a module-level dict (`_pending_verifiers`) keyed by `state`, not in the DB. The `auth` table has no `code_verifier` column; in-memory is sufficient for this single-user local app (human approved at checkpoint).
- `apps/api/config.py` and `apps/api/dependencies.py` added alongside the router (both in scope for Backend/API).
- CORS configured for `http://localhost:5173` in `main.py`.
- All Spotify HTTP calls use `httpx.AsyncClient`; mocked with `unittest.mock` in tests (no `respx` dependency needed).
- 27 tests: 15 unit (PKCE helpers + token functions) and 12 integration (all 5 endpoints including token auto-refresh and error paths).
- `ruff check`, `ruff format`, `mypy`, `pytest` all green.
- PR Reviewer: `# noqa: F401` on router import line is unnecessary (all 4 imports are genuinely used) — minor annotation noise, not worth a fix commit.
- PR Reviewer: `test_session` fixture defined in test_auth_routes.py but not directly referenced by any test — harmless.
- PR Reviewer: `Settings.SPOTIFY_CLIENT_ID` defaults to `""` rather than being required — enables tests but silently allows app start without real credentials.
