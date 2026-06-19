---
id: T-024
phase: 2
agent: Domain Core
depends_on: [T-022, T-023, T-007]
status: TODO
branch: ""
pr: ""
---

### T-024 — Playlist assembler + Spotify exporter
**Phase:** 2 | **Agent:** Domain Core | **Depends on:** T-022, T-023, T-007

Build the playlist assembly and export module — the last step of the recommendation pipeline.

**Scope — `libs/playlist/`**
- `assembler.py`: `assemble(ranked_tracks, mode, size, session) → GeneratedPlaylist`. Selects top `size` tracks from the ranked list. Persists to DB: creates a `playlists` row and one `playlist_tracks` row per track (storing rank, final_score, score_breakdown). Returns `GeneratedPlaylist`.
- `exporter.py`: `export_to_spotify(playlist, fetcher, session) → str`. Creates a Spotify playlist via the Spotify API, adds all tracks by URI, updates `playlists.spotify_url` and `spotify_playlist_id` in DB. Returns the Spotify URL.

**Acceptance criteria**
- Assembled playlist has exactly `size` tracks (or fewer if not enough candidates).
- All `playlist_tracks` rows are written to DB with correct rank and score.
- After export, `playlists.spotify_url` is populated and the playlist appears in the user's Spotify account.
- Export is idempotent: re-exporting the same playlist creates a new Spotify playlist rather than failing.

**Notes**
_Orchestrator fills after completion._
