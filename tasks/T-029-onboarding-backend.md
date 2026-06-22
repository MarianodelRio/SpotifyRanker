---
id: T-029
phase: 3
agent: Backend/API
depends_on: [T-007, T-018]
status: PR_OPEN
branch: feature/T-029-onboarding-backend
pr: "https://github.com/MarianodelRio/SpotifyRanker/pull/18"
---

### T-029 — Onboarding backend
**Phase:** 3 | **Agent:** Backend/API | **Depends on:** T-007, T-018

Implement the explicit taste declaration feature — the user declares favorite artists or playlists and the system imports their tracks as training data.

**Scope — `apps/api/routers/profile.py`**
- `POST /profile/artist` → `{spotify_id}`: fetches the artist's full discography via the Spotify fetcher, upserts tracks into DB, assigns training labels based on declared-artist weights from `design.md` section 10 (popular tracks: label=0.90, rest: 0.60).
- `POST /profile/playlist` → `{spotify_id}`: fetches all playlist tracks, upserts, assigns label=0.80/weight=0.7.
- `GET /profile/declared` → list of declared artists and playlists with their import status.
- `DELETE /profile/artist/{id}` → removes the declared artist (does not delete tracks from DB, only removes the label assignment).
- `GET /profile` → `{genre_weights, top_artists, stats}` from `build_profile`.

**Acceptance criteria**
- Declaring an artist imports all their tracks into DB with correct labels.
- Declaring a playlist imports all its tracks with correct labels.
- After declaring, `build_training_set` returns more examples (verifiable by count).
- Deleting a declared artist removes its label assignments without deleting tracks.

**Notes**

Cross-module changes required and approved by human:
- `db/models.py`: added `declared_artist_label`, `declared_artist_weight`, `declared_artist_spotify_id`, `declared_playlist_label`, `declared_playlist_weight` nullable columns to `UserTrackData`; added `DeclaredArtist` and `DeclaredPlaylist` tables.
- `db/repositories/declared.py`: new `DeclaredArtistRepository` (with upsert/get/get_all/delete that cascades label-clear) and `DeclaredPlaylistRepository`.
- `db/repositories/user_track_data.py`: extended `upsert()` to accept all five new declared-signal fields.
- `libs/ml/training_set.py`: extended `_compute_label_weight()` to include declared artist and playlist signals; uses max-label selection like all other signals.
- `libs/spotify/fetcher.py`: added `fetch_artist()`, `fetch_artist_top_tracks()`, `fetch_playlist_info()`.
- `apps/api/routers/profile_router.py`: all 5 endpoints implemented. Popular vs. rest track classification uses Spotify top-tracks as proxy (since album track listings don't include per-track popularity).
- `tests/unit/test_db_init_session.py`: updated expected table count (11 → 13).
- `tests/unit/test_training_set.py`: 8 new tests covering all declared-signal cases.
- `tests/integration/test_profile_router.py`: 9 integration tests covering all 5 endpoints.

PR Reviewer observations:
1. ArtistGenre links not populated during artist declaration — `genre_repo.get_or_create()` is called but the `artist_genres` join table is never written. Declared-artist tracks won't contribute to `genre_weights` in `build_profile()`. Not an acceptance criterion for this task but worth a follow-up task or inline fix.
2. TrackArtist links not created for discography tracks — same gap; tracks imported via this endpoint lack artist links. Pre-existing pattern from import_router for saved tracks, but worsens here since the artist is known.
3. `_POPULAR_THRESHOLD = 50` constant defined but never used (classification uses top-tracks set, not the field).
4. `settings: Settings = Depends(get_settings)` injected in declare_artist/declare_playlist but never referenced inside the function body.
5. `POST /profile/artist` runs synchronously — for artists with large catalogs (100+ albums) this will be slow and may hit request timeouts. Consider background task in a follow-up.
