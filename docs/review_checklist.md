# Review Checklist — TasteRanker

Use this checklist before merging any branch into `master`.

---

## Tests

- [ ] `pytest` passes with no failures in CI
- [ ] Coverage on `libs/` has not dropped below 70%
- [ ] Unit tests do not require network access (no real Spotify calls)
- [ ] Unit tests do not require a real database (SQLite in-memory or mocked)
- [ ] Every new function in `libs/` has at least one unit test
- [ ] Every new API endpoint has at least one integration test
- [ ] New edge cases covered (empty lists, missing fields, API errors, zero candidates)

---

## Linting and Formatting

- [ ] `ruff check .` passes with zero errors
- [ ] `ruff format .` produces no diff (code is already formatted)
- [ ] No unused imports
- [ ] No commented-out code without explanation
- [ ] No `print()`, `breakpoint()`, `pdb.set_trace()` in production files
- [ ] No `console.log()` left in frontend production code

---

## Type Checking

- [ ] `mypy libs/ apps/api/` passes with zero errors
- [ ] `npx tsc --noEmit` passes in `apps/frontend/` with zero errors
- [ ] No `# type: ignore` added without a comment explaining why

---

## Module Contracts

- [ ] `libs/common/models.py` was NOT modified (or Architect explicitly approved it)
- [ ] `libs/common/enums.py` was NOT modified (or Architect explicitly approved it)
- [ ] No circular imports introduced (DAG: common ← spotify/profile/candidates ← ranker ← playlist ← api)
- [ ] TypeScript types in `apps/frontend/src/types/api.ts` are consistent with Pydantic models if models changed
- [ ] `db/models.py` was NOT modified without a migration (or this is Phase 0)

---

## Folder Ownership

- [ ] The PR only touches files in the assigned agent's folders
- [ ] Any out-of-scope file change is explicitly justified in the PR description
- [ ] No domain logic added to `apps/api/routers/` (thin controllers only)
- [ ] No Spotify API calls outside `libs/spotify/`
- [ ] No direct DB access outside `db/` and `libs/feedback/`
- [ ] No imports from `libs/ranker/` or `libs/profile/` inside `libs/spotify/`

---

## Code Quality

- [ ] No magic numbers — constants are named
- [ ] No functions longer than ~50 lines without a strong reason
- [ ] Public functions that have non-obvious behavior have a docstring
- [ ] Pydantic models use `Field()` with descriptions where helpful
- [ ] Error handling is present at system boundaries (API routes, Spotify client)
- [ ] No bare `except:` clauses
- [ ] Spotify rate limiting and token expiry are handled in `libs/spotify/`

---

## Documentation

- [ ] If a new API endpoint was added → `docs/api.md` updated
- [ ] If a ranker signal was added or changed → `docs/scoring.md` updated
- [ ] If an architectural decision was made → ADR added to `docs/adr/`
- [ ] If setup steps changed → `README.md` updated
- [ ] PR description explains what was built and why (not just what files changed)

---

## PR Hygiene

- [ ] PR title starts with the task ID: `T-XXX: [short description]`
- [ ] PR does not include changes unrelated to the task
- [ ] PR description includes acceptance criteria checkboxes from `task.md`
- [ ] PR does not contain merge commits from `master` (rebase before merging)
- [ ] Branch name follows `feature/T-XXX-short-slug` pattern

---

## Domain-Specific Checks

### Spotify Integration PRs
- [ ] All used Spotify endpoints have JSON fixtures in `tests/fixtures/spotify_responses/`
- [ ] Rate limiting with retry/backoff is in place
- [ ] Token refresh is handled
- [ ] Restricted endpoints (`/recommendations`, `/audio-features`, `/audio-analysis`, `related-artists`) are NOT used

### ML/Ranker PRs
- [ ] `final_score` is always in [-1, 1] (L2-normalized embeddings, dot product)
- [ ] `PlaylistMode` weight configurations are defined in `libs/ranker/modes.py` and documented in `docs/scoring.md`
- [ ] Diversifier enforces ≤ 3 tracks per artist and ≤ 40% per genre
- [ ] `score_breakdown` dict is populated for every `RankedTrack`
- [ ] Training uses `device='cpu'` explicitly (no GPU assumed)
- [ ] Model files saved to `models_store/`, not hardcoded paths
- [ ] Feature vectors are fixed-length and all values in [0, 1]
- [ ] `load_model()` raises `ModelNotTrainedError` if files are absent (not raw `FileNotFoundError`)

### Frontend PRs
- [ ] TypeScript types are not duplicated (use types from `src/types/api.ts`)
- [ ] API calls go through the typed client in `src/api/` (not raw fetch)
- [ ] No sensitive data (tokens) stored in localStorage
- [ ] OAuth token is handled via httpOnly cookie (backend-managed)

### DB / Feedback PRs
- [ ] New ORM models have a corresponding migration or `init_db.py` update
- [ ] `FeedbackStore` tests use SQLite in-memory (not a file)
- [ ] No raw SQL strings — use SQLAlchemy ORM
