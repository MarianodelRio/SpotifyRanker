---
id: T-030
phase: 3
agent: Frontend
depends_on: [T-029, T-028, T-015]
status: TODO
branch: ""
pr: ""
---

### T-030 — Onboarding + profile frontend
**Phase:** 3 | **Agent:** Frontend | **Depends on:** T-029, T-028, T-015

Build the profile/onboarding UI and wire model status into the interface.

**Scope**
- Profile section in the sidebar (or as a modal): shows `GET /profile` data — top genres with weights (bar chart or tag cloud), top artists with affinity scores, model last trained, examples count.
- "Declare artists" flow: search input (calls `GET /search?type=artist`), results list, "Add" button per artist, calls `POST /profile/artist`. Shows import progress.
- "Declare playlists" flow: same pattern with `POST /profile/playlist`.
- Declared artists/playlists list with remove button (calls `DELETE /profile/artist/{id}`).
- Model status indicator in header or profile: "Model trained X minutes ago" or "Training..." badge.
- Manual retrain button: calls `POST /model/train`.

**Acceptance criteria**
- Declaring an artist triggers the import and shows a progress indicator.
- Genre weights are displayed and update after a retrain.
- Model status badge updates correctly (polling `GET /model/status` every few seconds while training is in progress).
- Manual retrain button is disabled while training is already in progress.

**Notes**
_Orchestrator fills after completion._
