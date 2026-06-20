---
id: T-015
phase: 1
agent: Frontend
depends_on: [T-012, T-009]
status: IN_PROGRESS
branch: feature/T-015-player-panel
pr: ""
---

### T-015 — PlayerPanel (Spotify Web Playback SDK)
**Phase:** 1 | **Agent:** Frontend | **Depends on:** T-012, T-009

Integrate the Spotify Web Playback SDK and build the right-column player. This is the playback core.

**Scope**
- Initialize `window.Spotify.Player` on app load using the token from `/auth/token`. Re-fetch token on expiry.
- `PlayerPanel` component (right column, always visible): album art, track title, artist name, progress bar (updated every second), play/pause button, skip button.
- Clicking any TrackCard anywhere in the app triggers `player.play({uris: [spotifyUri]})`.
- Global player state (current track, is playing, position) available via React context or equivalent.
- On track end or on track switch: call `POST /player/event` with `ms_played` and `source`.

**Acceptance criteria**
- Clicking a track in Mi música or Buscar plays it in the browser.
- Progress bar updates in real time.
- Play/pause and skip work.
- `POST /player/event` is called when a track ends or is skipped.
- Token is refreshed automatically if the SDK reports auth errors.

**Notes**
- `PlayerProvider` wraps the authenticated app inside `AuthProvider`, so the SDK only initializes after login.
- Position tracking (`positionMs`) is stored in a ref, not context state — this prevents every context consumer from re-rendering every second during playback. `PlayerPanel` reads position via `getPositionMs()` callback on its own 1s interval.
- `player_state_changed` fires ~100ms during playback; only `isPlaying` and track-switch detection are derived from it. No API calls are triggered directly from this event.
- Playback transfer (`PUT /me/player`) is called automatically when the SDK emits `ready` with a device_id, making the browser the active Spotify Connect device.
- `authentication_error` triggers `player.disconnect()` + reinitialize with a fresh token from `GET /auth/token`.
- `TrackCard` component created at `src/components/track/TrackCard.tsx` — ready for T-013 (Mi música) and T-014 (Buscar) to import.
- Like/dislike buttons in `PlayerPanel` and `TrackCard` are rendered but wired to no-op — T-016 owns that logic.
