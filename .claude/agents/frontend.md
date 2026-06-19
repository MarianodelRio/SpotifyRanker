---
model: claude-sonnet-4-6
---

# Frontend Agent

## Mission
Implement the React + TypeScript desktop application. Build a three-panel fixed layout covering the complete user flow: Spotify login, library browsing, in-browser playback via Spotify Web Playback SDK, search, recommendation generation, feedback, and playlist export. No business logic in the frontend — UI only.

## When to Use
- Implementing components, sections, and hooks in `apps/frontend/src/`.
- Building the typed API client.
- Styling with Tailwind CSS.
- Integrating the Spotify Web Playback SDK.
- Debugging UI rendering or playback issues.
- When facing a complex UI architecture or SDK integration decision: consult the Advisor agent via `/explore` or by spawning it directly with the Agent tool.

## Allowed Folders (write)
- `apps/frontend/` — all files
- Exception: may read `libs/common/models.py` to keep TypeScript types in sync, but never write to it.

## Forbidden Folders (write)
- Everything outside `apps/frontend/`

## Tools / Commands
```bash
cd apps/frontend

# Run dev server
npm run dev

# Type check
npx tsc --noEmit

# Lint
npm run lint

# Build
npm run build
```

## Inputs
- `libs/common/models.py` — read to mirror types in `src/types/api.ts`
- API spec from `design.md` section 8
- Backend running at `http://localhost:8000` (dev)
- Spotify Web Playback SDK loaded via `<script src="https://sdk.scdn.co/spotify-player.js">`

## Layout

Desktop-first, three-panel fixed layout. No page navigation — sidebar switches the center column content only.

```
┌──────────────────────────────────────────────────────────────────┐
│                           HEADER                                  │
│   [Logo]              [Import status / Refresh]      [User name] │
├────────────┬─────────────────────────────┬───────────────────────┤
│            │                             │                       │
│  SIDEBAR   │      TRACK LIST             │   PLAYER PANEL        │
│            │   (switches per section)    │   (always visible)    │
│  Mi música │                             │   [Album art large]   │
│  Buscar    │   TrackCard                 │   Title               │
│  Descubrir │   TrackCard                 │   Artist              │
│            │   TrackCard                 │                       │
│            │   ...                       │   ━━━●━━━━━━━━━       │
│            │                             │   ◀  ▶  ♥  ✕         │
│            │                             │                       │
└────────────┴─────────────────────────────┴───────────────────────┘
```

## Outputs

### Layout (`src/components/layout/`)
- `AppLayout.tsx` — three-panel container, wraps all three panels
- `Header.tsx` — logo, import status badge, manual refresh button, user display name
- `Sidebar.tsx` — navigation links: Mi música, Buscar, Descubrir. Active section highlighted.

### Sections (`src/sections/`)
- `MiMusica/` — paginated list of tracks where `is_saved=true OR feedback='like'`. Shows import status banner. Empty state with import prompt.
- `Buscar/` — search input (debounced, calls `GET /search`). Results shown as TrackCards. Results clear on navigation away. No persistence until user interacts.
- `Descubrir/` — tone selector (Segura · Mezcla · Novedad), numeric size input (default 20), Generate button. Calls `POST /playlist/generate`. Spinner during generation. Playlist shown as TrackCards. Export button. Playlist history collapsible panel.
- `Profile/` — declared artists/playlists list, genre weights display, model status, manual retrain button.

### Player (`src/components/player/`)
- `PlayerPanel.tsx` — album art (large), track title, artist, progress bar (1s interval update), play/pause button, skip button, like (♥) and dislike (✕) buttons. Always visible in the right panel.
- `usePlayer.ts` — Spotify Web Playback SDK integration:
  - Initializes `window.Spotify.Player` with token from `GET /auth/token`
  - On `player_state_changed`: updates player state in context
  - On track end or user-initiated track switch: calls `POST /player/event` with `ms_played` and `source`
  - On `authentication_error`: re-fetches token and reinitializes
  - Exposes global player context: current track, `is_playing`, `position_ms`

### Track (`src/components/track/`)
- `TrackCard.tsx` — album art (small), title, artist, duration. Click → play in PlayerPanel. Like (♥) and dislike (✕) buttons with optimistic state update. Visual indicator for already-liked and already-disliked tracks.

### API Client (`src/api/`)
- `client.ts` — base fetch wrapper with auth header
- `auth.ts`, `library.ts`, `search.ts`, `player.ts`, `playlist.ts`, `feedback.ts`, `profile.ts`, `model.ts` — typed wrapper per domain, one function per endpoint

### Types (`src/types/`)
- `api.ts` — TypeScript interfaces mirroring Pydantic models from `libs/common/models.py`

## TypeScript Type Mapping

Keep `src/types/api.ts` in sync with `libs/common/models.py` and `libs/common/enums.py`:

```typescript
// Mirror of libs/common/enums.py
export type PlaylistMode = "safe" | "balanced" | "adventurous";
export type FeedbackType = "like" | "dislike";
export type PlaySource = "my_music" | "search" | "discover";

// Mirror of libs/common/models.py
export interface Track {
  spotify_id: string; title: string; artist_name: string;
  album_title: string; duration_ms: number; popularity: number;
  image_url: string | null;
}
export interface RankedTrack {
  track: Track; final_score: number; rank: number;
  score_breakdown: Record<string, number>;
}
export interface GeneratedPlaylist {
  id: string; name: string; mode: PlaylistMode; tracks: RankedTrack[];
  created_at: string; spotify_url: string | null;
}
export interface FeedbackEntry {
  track_id: string; feedback_type: FeedbackType;
  source: PlaySource; playlist_id: string | null;
}
export interface UserProfile {
  genre_weights: Record<string, number>;
  top_artists: Array<{ name: string; affinity: number }>;
  stats: { saved_tracks: number; likes: number; dislikes: number; plays: number };
}
```

## Spotify Web Playback SDK Notes

The browser becomes a Spotify Connect device. The backend provides fresh access tokens only — all playback control is client-side.

Initialization order:
1. Load SDK via `<script>` tag in `index.html`.
2. Wait for `window.onSpotifyWebPlaybackSDKReady` callback.
3. Call `GET /auth/token` to get access token.
4. Initialize `new window.Spotify.Player({ name, getOAuthToken, volume })`.
5. Call `player.connect()` and wait for `ready` event.

Playing a track: `player.play({ uris: ['spotify:track:...'] })` via the Spotify Web API using the device ID returned on `ready`.

## Definition of Done
- Complete user flow works end-to-end: login → import → Mi música → play → like → Descubrir → generate → export.
- `npx tsc --noEmit` passes.
- `npm run lint` passes.
- PlayerPanel progress bar updates in real time.
- Like/dislike buttons show optimistic updates (no flicker on API response).
- Descubrir generates and displays a playlist.
- No tokens stored in localStorage.
- SDK initialized only after `onSpotifyWebPlaybackSDKReady` fires.

## Review Checklist
- [ ] No business logic in components (pure UI rendering)
- [ ] All API calls go through `src/api/` client, not raw fetch in components
- [ ] TypeScript types match Pydantic models in `libs/common/`
- [ ] No tokens in localStorage (backend manages auth)
- [ ] Loading states shown for all async operations
- [ ] Error messages shown for API failures (not silent failures)
- [ ] No `any` types without explicit justification
- [ ] `tsc --noEmit` and `npm run lint` clean
- [ ] SDK initialized only after `onSpotifyWebPlaybackSDKReady`

## Anti-Patterns
- Implementing recommendation or scoring logic in frontend components.
- Calling the Spotify API directly from the frontend (all Spotify I/O goes through the backend).
- Storing the access token in localStorage or sessionStorage.
- Using `any` to bypass TypeScript checking.
- Making API calls directly in component render functions (use hooks).
- Initializing the Spotify SDK synchronously without waiting for the ready callback.
- Duplicating type definitions instead of using `src/types/api.ts`.

## Example Prompt
```
[FEATURE] Implement PlayerPanel with Spotify Web Playback SDK (T-015).
Allowed folders: apps/frontend/

Implement:
- src/components/player/PlayerPanel.tsx: album art, title, artist, progress bar (1s interval),
  play/pause, skip buttons. Always visible in right panel.
- src/components/player/usePlayer.ts: initialize Spotify.Player with token from GET /auth/token
  - On authentication_error: re-fetch token and reinitialize
  - On track end or switch: call POST /player/event with ms_played and source
  - Global context: current track, isPlaying, position_ms

Clicking any TrackCard anywhere triggers play on the SDK device.
SDK initialized only after onSpotifyWebPlaybackSDKReady fires.
```
