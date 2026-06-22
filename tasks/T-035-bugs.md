---
id: T-035
phase: 1
agent: multi (data-persistence → backend-api → frontend)
depends_on: []
status: DONE
branch: feature/T-035-bugfix
pr: "https://github.com/MarianodelRio/SpotifyRanker/pull/24"
---

### T-035 — Bugfix: search, player, library contract, import

**Phase:** bugfix | **Agent:** data-persistence + backend-api + frontend | **Depends on:** —

Fixes five bugs found during manual testing of the running system. All causes are confirmed. Changes cross three agent domains and must be implemented in order: DB schema first, then backend, then frontend.

---

## Bug 1 — Buscador siempre "Try again" (BLOCKING)

**Root cause:** The backend returns `{"results": items, ...}` but the frontend `SearchResult` interface and `Buscar/index.tsx` expect `{"tracks": items}`. `data.tracks` is always `undefined` → TypeError in `.then()` → `.catch()` → always shows the error message, even when Spotify returns valid results.

**Fix (backend-api):**

File: `apps/api/routers/library_router.py`
- Line 113: rename `"results"` key to `"tracks"` in the return dict.
- Also keep the uncommitted `except httpx.HTTPStatusError` block (already present in working tree).

No frontend changes needed.

---

## Bug 2 — Player no reproduce (BLOCKING)

**Root cause A — Scopes OAuth faltantes:** Spotify Web Playback SDK requires `user-read-private` and `user-read-email`. Without them the SDK never authenticates, never emits `ready`, `deviceId` stays `null`, and `playTrack` silently returns early.

**Fix (backend-api):** Already present in uncommitted changes to `libs/spotify/auth.py` — the two scopes are added. Keep as-is. The existing token in DB was issued without those scopes → the user must do logout + login once after this fix is merged.

**Root cause B — Race condition:** `transferPlayback` was called immediately in the `ready` event, before Spotify's server was ready to accept the device.

**Fix (frontend):** Already present in uncommitted changes to `apps/frontend/src/context/PlayerContext.tsx` — `setTimeout(..., 1000)` delay. Keep as-is.

**Root cause C — No feedback on account_error:** If the account doesn't have Spotify Premium, the SDK fires `account_error` and the current listener only calls `console.error`. The user sees silence with no explanation.

**Fix (frontend) — new work:**

File: `apps/frontend/src/context/player-context.ts`
- Add `error: string | null` to the `PlayerContextValue` interface.

File: `apps/frontend/src/context/PlayerContext.tsx`
- Add `const [playerError, setPlayerError] = useState<string | null>(null)`.
- In the `account_error` listener: call `setPlayerError("Spotify Premium is required for browser playback.")`.
- Expose `error: playerError` in the context value Provider.

File: `apps/frontend/src/components/player/PlayerPanel.tsx`
- Read `error` from `usePlayer()`.
- Render an error banner when `error` is non-null (e.g. red text above the controls).

**index.html SDK stub:** Keep the uncommitted `window.onSpotifyWebPlaybackSDKReady = () => {};` before the SDK `<script>` tag. `PlayerContext.tsx` already handles the case where `window.Spotify` is already defined when the component mounts.

---

## Bug 3 — `/library` contract broken (BLOCKING for Mi Música)

Three sub-bugs, all fixed together.

**Sub-bug A — Pagination mismatch:**
Frontend sends `?page=1&per_page=50`. Backend reads `?offset=0&limit=50`. Params are ignored; backend always uses defaults.

Backend returns `{"tracks": [...], "count": 50, ...}`. Frontend reads `data.total` (undefined) and `data.page` (undefined). `hasMore = tracks.length < undefined` → always false → "Load more" never appears.

**Sub-bug B — Missing fields in /library response:**
Backend returns `spotify_id, title, duration_ms, popularity, is_saved, feedback, top_position_*`. Missing: `artist_name`, `album_title`, `image_url`.
The frontend `Track` interface requires all three. Mi Música shows tracks with empty artist and no image.

**Sub-bug C — Import does not save denormalized fields:**
The DB `tracks` table has no `artist_name`, `album_title`, or `image_url` columns. The schema uses normalized FKs (`album_id` → `albums`, `track_artists` → `artists`). But the import never populates `album_id` or `track_artists`, so 100% of those rows are NULL and JOINs return nothing.

The `Track` object from `libs/common/models.py` already carries `artist_name`, `album_title`, `image_url` as flat fields — so the data is available at import time, just never saved.

**Decision: Denormalize `tracks` table — add three nullable TEXT columns.**

This is the correct MVP fix. JOINs on empty tables would not help. Existing 2,064 tracks will have NULL for the new columns until the user triggers a re-import; the UI already handles `image_url: null` (grey placeholder). `artist_name: null` will show empty text — acceptable short-term.

### Changes required

**Agent: data-persistence** ⚠️ *Schema change — requires Architect approval before merge.*

File: `db/models.py`
- Add to `Track` class:
  ```python
  artist_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
  album_title: Mapped[str | None] = mapped_column(String(512), nullable=True)
  image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
  ```

Manual migration on existing DB (run once):
```sql
ALTER TABLE tracks ADD COLUMN artist_name TEXT;
ALTER TABLE tracks ADD COLUMN album_title TEXT;
ALTER TABLE tracks ADD COLUMN image_url TEXT;
```

File: `db/repositories/track.py`
- Add `artist_name: str | None = None`, `album_title: str | None = None`, `image_url: str | None = None` to `upsert()` signature.
- Include in `insert().values()` and `on_conflict_do_update.set_`.

**Agent: backend-api**

File: `apps/api/routers/import_router.py`
- In the saved_tracks loop (lines 71–76) and in both top_tracks loops (lines 89–99): pass `artist_name=track.artist_name`, `album_title=track.album_title`, `image_url=track.image_url` to `track_repo.upsert()`.

File: `apps/api/routers/library_router.py`
- Change endpoint params from `offset: int = Query(0), limit: int = Query(50)` to `page: int = Query(1, ge=1), per_page: int = Query(50, ge=1, le=200)`.
- Compute `offset = (page - 1) * per_page` inside the handler.
- Add a COUNT query before the paginated query to get the real total:
  ```python
  count_stmt = (
      select(func.count())
      .select_from(Track)
      .join(UserTrackData, UserTrackData.track_id == Track.id)
      .where(or_(UserTrackData.is_saved.is_(True), UserTrackData.feedback == "like"))
  )
  total = (await db.execute(count_stmt)).scalar_one()
  ```
- Add `artist_name`, `album_title`, `image_url` to the track dict in the response loop (reading `track.artist_name`, etc.).
- Change return to `{"tracks": tracks, "total": total, "page": page, "per_page": per_page}`.

No frontend changes needed — `LibraryPage` interface, `getLibrary()`, and `MiMusica/index.tsx` already use `total`, `page`, `per_page`.

---

## Bug 4 — Import lento / sin progreso visible (UX)

**Root cause A — Batch fetch before any DB write:** `fetch_saved_tracks()` fetches ALL Spotify pages before writing anything to DB. For a 2000-track library (40+ pages) the progress counter shows `0 tracks` for minutes, then jumps to the total at once.

**Root cause B — Aggressive rate-limit backoff:** `retry_after * (2**attempt)` can reach 20 s on the third attempt (with `Retry-After: 5`).

**Root cause C — No token refresh in background task:** `SpotifyClient` is created with `SpotifyClient(access_token)` and no `refresh_fn`. If the token expires mid-import, all subsequent fetches fail with 401 and the import silently ends in `failed`.

**Fix (backend-api):**

File: `libs/spotify/client.py`
- Line 47: cap backoff: `backoff = min(retry_after * (2**attempt), 30)`.

File: `libs/spotify/fetcher.py`
- Add async generator `fetch_saved_tracks_paged(self, limit: int = 50) -> AsyncGenerator[list[Track], None]`: fetches one Spotify page at a time and yields each batch.
- Add async generator `fetch_top_tracks_paged(self, time_range: str, limit: int = 50) -> AsyncGenerator[list[Track], None]`: same pattern.
- These do not replace the existing `fetch_saved_tracks()` and `fetch_top_tracks()` methods (keep those for backwards compatibility with other callers and tests).

File: `apps/api/routers/import_router.py`
- Change `_run_import` signature to also accept `refresh_token: str | None` and `client_id: str`.
- Build a `refresh_fn` closure that opens `AsyncSessionLocal`, calls `refresh_access_token(refresh_token, client_id)`, persists the new `access_token` and `token_expires_at` to the `Auth` row, and returns the new token.
- Pass `refresh_fn=refresh_fn` to `SpotifyClient(access_token, refresh_fn=refresh_fn)`.
- Replace the `saved_tracks = await fetcher.fetch_saved_tracks()` + loop block with:
  ```python
  async for batch in fetcher.fetch_saved_tracks_paged():
      for track in batch:
          track_id = await track_repo.upsert(...)
          await user_data_repo.upsert(...)
  ```
  This commits per-track (TrackRepository.upsert already commits on each call), so progress is visible immediately.
- Do the same for the top_tracks loops using `fetch_top_tracks_paged()`.
- Update `start_import` endpoint to pass `auth.refresh_token` and `settings.SPOTIFY_CLIENT_ID` to `_run_import`. Inject `settings` via FastAPI `Depends(get_settings)`.

---

## Bug 5 — Like no funcionaba (ALREADY FIXED in uncommitted changes)

Feedback endpoints return HTTP 204 No Content. The original `apiFetch` called `.json()` on an empty body → SyntaxError → the like appeared to fail even though it was saved in DB.

Fix in `apps/frontend/src/api/client.ts` is correct and complete:
```typescript
if (res.status === 204 || res.headers.get("content-length") === "0") return undefined as T;
```

No additional changes needed. Keep as-is.

---

## Uncommitted changes — Disposition

All uncommitted changes in the working tree are correct partial fixes. They must be incorporated into this branch, not discarded.

| File | Uncommitted change | Action |
|---|---|---|
| `libs/spotify/auth.py` | Adds `user-read-private`, `user-read-email` scopes | ✅ Keep — integrate into branch |
| `apps/frontend/index.html` | SDK stub before `<script>` | ✅ Keep — integrate |
| `apps/frontend/src/api/client.ts` | 204/empty body handling | ✅ Keep — integrate (fixes Bug 5) |
| `apps/frontend/src/context/PlayerContext.tsx` | `setTimeout(..., 1000)` | ✅ Keep — integrate |
| `apps/api/routers/library_router.py` | `except httpx.HTTPStatusError` | ✅ Keep — integrate + add `results`→`tracks` rename |

---

## Implementation order (internal dependency)

1. `db/models.py` + `db/repositories/track.py` (data-persistence)
2. Backend fixes: `import_router.py`, `library_router.py`, `libs/spotify/client.py`, `libs/spotify/fetcher.py` (backend-api)
3. Frontend fixes: `PlayerContext.tsx`, `player-context.ts`, `PlayerPanel.tsx` (frontend)

Step 2 depends on step 1 (uses the new `artist_name` etc. params in `track_repo.upsert`).

---

## Acceptance criteria

- Searching any term in Buscar shows actual results (no "Try again" on valid queries).
- Clicking play on any track starts playback in the browser (requires re-auth after merge to get new-scoped token).
- If account has no Spotify Premium, a visible error message appears in the player panel.
- Mi Música shows artist name and album art for tracks that were imported after this fix.
- Mi Música "Load more" button appears when there are more than 50 tracks.
- Import progress counter starts incrementing within seconds of starting (not waiting for all pages to load).
- Liking a track no longer shows an error (already working in uncommitted).

---

## Protected boundary flags

- `db/models.py` is modified (schema change). Requires Architect approval before merge.
- `libs/common/models.py` and `libs/common/enums.py` are NOT touched.

**Notes**

Implementation completed 2026-06-22. All 14 files changed in one commit. Key decisions and deviations:

- Added `get_pages` async generator to `SpotifyClient` (not mentioned in spec) to avoid duplicating pagination logic across paged fetcher methods. Existing `get_paginated` is unchanged.
- `refresh_fn` in `_run_import` preserves the old refresh_token if Spotify doesn't return a new one (Spotify only rotates when using PKCE with `refresh_token_rotation`).
- Pagination tests updated to use `page/per_page` and assert `total` field.
- Search response tests updated from `data["results"]` → `data["tracks"]`.
- `scripts/migrate_T035_track_denorm.py` added for one-time ALTER TABLE migration; skips gracefully if columns already exist.
- User must logout + login once after merge so new OAuth scopes (`user-read-private`, `user-read-email`) are granted.
