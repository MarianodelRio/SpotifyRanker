---
id: T-015
phase: 1
agent: Frontend
depends_on: [T-012, T-009]
status: TODO
branch: ""
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
_Orchestrator fills after completion._
