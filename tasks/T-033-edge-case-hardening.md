---
id: T-033
phase: 4
agent: Backend/API
depends_on: [T-030]
status: TODO
branch: ""
pr: ""
---

### T-033 — Edge case hardening
**Phase:** 4 | **Agent:** Backend/API | **Depends on:** T-030

Harden the system against the most likely failure modes in a personal-use production environment.

**Scope**
- Empty library: first-time user with zero imported tracks. `/playlist/generate` returns a clear message prompting onboarding rather than an error.
- No feedback yet: model trained with only implicit signals. Ensure training still completes (no division-by-zero in label computation).
- Spotify API failures: 5xx responses during import or candidate generation do not crash the background task. Partial imports are logged and the status reflects the failure.
- Token expiry during long operations: token is refreshed mid-import if it expires.
- Model not trained: `/playlist/generate` before first training returns HTTP 400 with a clear message and a hint to trigger `/model/train`.
- Rate limiting: all Spotify API calls under load respect backoff. Test with a mock that returns 429.

**Acceptance criteria**
- Calling `/playlist/generate` with no model returns `400 {"error": "model_not_trained", "hint": "..."}`.
- A 429 from Spotify during import does not fail the import task — it retries and continues.
- A partial import (e.g., artist fetch fails halfway) completes the saved tracks portion and marks status as `partial`.

**Notes**
_Orchestrator fills after completion._
