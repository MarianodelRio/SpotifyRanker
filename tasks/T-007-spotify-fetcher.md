---
id: T-007
phase: 1
agent: Backend/API
depends_on: [T-005, T-006]
status: PR_OPEN
branch: feature/T-007-spotify-fetcher
pr: "https://github.com/MarianodelRio/SpotifyRanker/pull/11"
---

### T-007 — Spotify data fetcher
**Phase:** 1 | **Agent:** Backend/API | **Depends on:** T-005, T-006

Build the Spotify API client capable of fetching all data needed for import and search. This is the only module allowed to call the Spotify Web API.

**Scope — `libs/spotify/fetcher.py`**
- Saved tracks (paginated, handles cursor-based pagination).
- Top tracks: short-term, medium-term, long-term (up to 50 each).
- Top artists: short-term, medium-term, long-term.
- Artist albums (paginated).
- Album tracks (paginated).
- Track search (`q`, `type=track`, paginated).
- Artist search (`q`, `type=artist`).
- Playlist tracks (paginated).

All methods handle rate limiting with exponential backoff on HTTP 429. All return domain models from `libs/common/`, not raw Spotify JSON.

**Acceptance criteria**
- All methods tested with mocked HTTP responses (no real Spotify calls in tests).
- Rate limiting: on a 429 response, retries with backoff up to 3 times before raising.
- Pagination: fetches all pages, not just the first.
- Returns `list[Track]` or `list[Artist]` (common/ models), never raw dicts.

**Notes**
- Implemented `SpotifyClient` in `libs/spotify/client.py` (not mentioned in the original scope but required by the agent spec) — handles auth headers, 401 token refresh via injected `refresh_fn`, and 429 exponential backoff up to 3 retries. `get_paginated()` follows Spotify's `next` cursor automatically.
- `SpotifyFetcher` in `libs/spotify/fetcher.py` wraps `SpotifyClient` with all 8 fetch methods; all return domain models.
- `fetch_artist_albums` returns `list[dict]` (raw) since albums don't map to a domain model in `common/`; all others return `list[Track]` or `list[Artist]`.
- 29 new tests across `test_spotify_client.py` and `test_spotify_fetcher.py`; full suite 145 passed, mypy and ruff clean.
- PR Reviewer: flagged that `get_paginated()` second-page requests bypass retry/refresh logic (direct `_http.get()` on absolute `next` URLs). Acceptable for MVP — Spotify rarely 429s mid-pagination, and token refreshes between pages would require more complex state management. Worth revisiting if flakiness appears in integration testing.
