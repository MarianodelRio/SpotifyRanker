---
id: T-029
phase: 3
agent: Backend/API
depends_on: [T-007, T-018]
status: TODO
branch: ""
pr: ""
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
_Orchestrator fills after completion._
