---
id: T-030
phase: 3
agent: Frontend
depends_on: [T-029, T-028, T-015]
status: PR_OPEN
branch: feature/T-030-onboarding-frontend
pr: "https://github.com/MarianodelRio/SpotifyRanker/pull/32"
---

### T-030 — Onboarding + profile frontend
**Phase:** 3 | **Agent:** Frontend | **Depends on:** T-029, T-028, T-015

Build the profile/onboarding UI and wire model status into the interface.

**Scope**
- Profile section in the sidebar (or as a modal): shows GET /profile data — top genres with weights (bar chart or tag cloud), top artists with affinity scores, model last trained, examples count.
- "Declare artists" flow: search input (calls GET /search?type=artist), results list, "Add" button per artist, calls POST /profile/artist. Shows import progress.
- "Declare playlists" flow: same pattern with POST /profile/playlist.
- Declared artists/playlists list with remove button (calls DELETE /profile/artist/{id}).
- Model status indicator in header or profile: "Model trained X minutes ago" or "Training..." badge.
- Manual retrain button: calls POST /model/train.

**Acceptance criteria**
- Declaring an artist triggers the import and shows a progress indicator.
- Genre weights are displayed and update after a retrain.
- Model status badge updates correctly (polling GET /model/status every few seconds while training is in progress).
- Manual retrain button is disabled while training is already in progress.

**Notes**
- Fixed ModelStatus TypeScript type to match actual backend response (training_in_progress: boolean, last_loss: number | null).
- Fixed getDeclared() return type: backend returns {artists: [], playlists: []}, not a flat DeclaredItem[].
- Added ProfileResponse type for GET /profile response shape.
- Added searchArtists() to api/search.ts.
- Declare playlist flow uses URL/ID input (no search endpoint for playlists in the backend).
- useModelStatus hook shared between Header and Profile; both poll independently.
- Profile auto-refreshes genre weights when training completes.
- PR Reviewer: rebase skipped the coordination claim commit (mechanical conflict in task file only, no production code). formatAgo duplicated in Header.tsx and Profile/index.tsx — minor, not a bug. No frontend test suite in project.
