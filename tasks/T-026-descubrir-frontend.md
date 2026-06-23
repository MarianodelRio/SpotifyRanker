---
id: T-026
phase: 2
agent: Frontend
depends_on: [T-025, T-015]
status: READY_FOR_PR
branch: feature/T-026-descubrir-frontend
pr: ""
---

### T-026 — Descubrir section frontend
**Phase:** 2 | **Agent:** Frontend | **Depends on:** T-025, T-015

Build the Descubrir section — the main discovery UI where the user generates and explores playlists.

**Scope**
- Controls bar: tone selector (Segura / Mezcla / Novedad), numeric size input (default 20), Generate button.
- Clicking Generate calls `POST /playlist/generate`, shows a spinner during the request, then populates the track list.
- Generated playlist rendered as a list of `TrackCard` components. Clicking a track plays it.
- Export button: calls `POST /playlist/{id}/export`, shows the Spotify URL on success.
- Playlist history: a secondary view (or collapsible panel) listing past generated playlists. Clicking one loads its tracks.
- Score breakdown: optionally visible per track (collapsed by default, expandable).

**Acceptance criteria**
- Full flow works: select Mezcla → size 20 → Generate → see tracks → click one → plays in player.
- Export button creates the playlist in Spotify and shows the URL.
- History shows all past playlists and allows loading their track list.
- Spinner shown during generation. Error message shown if generation fails.

**Notes**
- `useDescubrir.ts` is a single custom hook owning all state (mode, size, loading, error, playlist, history, spotifyUrl). No context needed — Descubrir state is local to this section.
- Score breakdown uses a native `<details>/<summary>` element per track, collapsed by default. Renders `RankedTrack.score_breakdown` key-value pairs and `final_score`.
- History is fetched once on mount via `getPlaylistHistory()`; new generates prepend to it.
- Export disables the button and shows "✓ Exported" + an "Open in Spotify ↗" link once successful.
- `TrackCard` is reused as-is; track is accessed via `ranked.candidate.track` (matches the actual `RankedTrack` shape in `types/api.ts`).
- `tsc --noEmit` and `eslint` both pass clean.
