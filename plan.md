# TasteRanker — Implementation Plan

> Derived from `design.md`. Read design.md first for requirements, data model, and architectural decisions.
> This document defines phases, module ownership, parallelization strategy, and agent assignments.

---

## 1. Project Summary

TasteRanker is a personal music discovery web app and player for a single Spotify Premium user. It imports the user's Spotify library, builds a taste profile, and uses a Two-Tower deep learning model to generate personalized discovery playlists. Music plays directly in the browser via the Spotify Web Playback SDK.

The MVP proves that a fully self-owned recommendation pipeline — without Spotify's restricted endpoints — can produce relevant, personalized playlists that improve with feedback.

**What makes this buildable fast:**
- Single user eliminates auth complexity.
- SQLite eliminates database infrastructure.
- Modular monolith allows parallel agent development from Phase 1 onward.
- Phase 0 is the only sequential bottleneck.

---

## 2. Architecture Summary

### Module Map

```
Dockerfile            Backend container image (Python 3.11, PyTorch CPU-only).
docker-compose.yml    Dev orchestration: api (:8000) + frontend (:5173) + volumes.
apps/
  api/                FastAPI HTTP entry point. Orchestrates libs/. No business logic.
  frontend/
    Dockerfile        Frontend container image (Node, Vite dev server).
    ...               React + TypeScript + Vite. Spotify Web Playback SDK.

libs/
  common/       PROTECTED. Shared Pydantic models and enums. No imports from other libs.
  spotify/      Spotify API adapter. Pure I/O. No business logic.
  profile/      Stateless taste profile builder. Reads DB, returns UserProfile.
  candidates/   Generates pool of unknown candidate tracks from Spotify.
  ml/           Feature engineering, Two-Tower model training and inference.
  ranker/       Scores candidates using ml/, applies mode weights, diversifies.
  playlist/     Assembles final playlist, exports to Spotify.
  feedback/     Persists feedback, updates user_track_data, triggers retraining.

db/             SQLAlchemy ORM models, session factory, repositories.
models_store/   Trained PyTorch model files (user_tower.pt, item_tower.pt).
```

### Dependency DAG (no reverse imports allowed)

```
common
  ↑
  ├── spotify          reads: common
  ├── profile          reads: common, db
  ├── ml               reads: common, db
  │
  ├── candidates       reads: common, spotify, profile
  ├── ranker           reads: common, ml, profile
  │
  ├── playlist         reads: common, spotify, ranker
  ├── feedback         reads: common, db
  │
  └── api              reads: all libs (orchestration only)

frontend             reads: api (HTTP only)
```

### Protected Files

These files require Architect Agent approval before any modification:

- `libs/common/models.py`
- `libs/common/enums.py`
- `db/models.py` (schema-breaking changes only)

---

## 3. Module Definitions

### `libs/common/` — Shared Contracts
**Owner:** Architect Agent
**Responsibility:** Defines the domain models and enums shared across all modules. The single source of truth for inter-module communication.
**Key models:** `Track`, `Artist`, `UserProfile`, `Candidate`, `RankedTrack`, `GeneratedPlaylist`, `FeedbackEntry`
**Key enums:** `PlaylistMode` (safe/balanced/adventurous), `FeedbackType` (like/dislike), `ImportStatus`, `CandidateSource`
**Rule:** No module may define its own representation of a domain object. All must use models from here.

---

### `libs/spotify/` — Spotify Adapter
**Owner:** Backend/API Agent
**Responsibility:** All HTTP communication with the Spotify Web API. OAuth PKCE flow, token refresh, rate limiting with retry backoff, pagination.
**Inputs:** Credentials, access token, method parameters.
**Outputs:** Domain models from `common/` (Track, Artist, Album lists).
**Knows:** Spotify API structure, OAuth 2.0, HTTP error codes.
**Does not know:** Recommendation logic, user profile, ranking.

---

### `libs/profile/` — Taste Profile Builder
**Owner:** Domain Core Agent
**Responsibility:** Builds a `UserProfile` from data in the database. Stateless pure functions — same inputs always produce the same output.
**Inputs:** Raw data from DB (user_track_data, artist_genres, top positions).
**Outputs:** `UserProfile` with `genre_weights`, `artist_affinities`, `known_track_ids`.
**Knows:** How to weight signals (explicit > implicit, recent > historical).
**Does not know:** Spotify API, ranking, playlist modes.

---

### `libs/candidates/` — Candidate Generator
**Owner:** Domain Core Agent
**Responsibility:** Generates a pool of tracks the user has not interacted with. Fetches from Spotify using two strategies: artist discographies and genre search.
**Inputs:** `UserProfile`, `SpotifyClient`.
**Outputs:** `list[Candidate]` — tracks not in `user_track_data`, with source metadata.
**Knows:** Candidate generation strategies, deduplication logic.
**Does not know:** Scoring, ranking, playlist modes.

---

### `libs/ml/` — ML Pipeline
**Owner:** ML/Ranking Agent
**Responsibility:** Feature engineering (builds numeric vectors for user and tracks), Two-Tower model definition (UserTower + ItemTower as PyTorch MLPs), training loop with InfoNCE loss and Hard Negative Mining, inference (computes embeddings and scores).
**Inputs:** Training dataset from DB, user_features and track_features vectors.
**Outputs:** Trained model files, `user_embedding`, `track_embeddings`, relevance scores.
**Knows:** PyTorch, contrastive learning, feature normalization.
**Does not know:** Spotify API, playlist modes, candidate sources.

---

### `libs/ranker/` — Scorer and Diversifier
**Owner:** ML/Ranking Agent
**Responsibility:** Takes candidates and scores them using `ml/inference`. Applies mode-specific weight adjustments (Segura/Mezcla/Novedad). Diversifies the final list to avoid artist and genre repetition.
**Inputs:** `list[Candidate]`, `UserProfile`, `PlaylistMode`.
**Outputs:** `list[RankedTrack]` sorted by final score.
**Knows:** Mode weight configurations, diversification rules.
**Does not know:** How candidates were generated, Spotify API.

---

### `libs/playlist/` — Assembler and Exporter
**Owner:** Domain Core Agent
**Responsibility:** Selects the top N ranked tracks, assembles the `GeneratedPlaylist` object, persists to DB, and optionally exports to Spotify.
**Inputs:** `list[RankedTrack]`, `PlaylistMode`, target size, `SpotifyClient`.
**Outputs:** `GeneratedPlaylist` with optional `spotify_url`.
**Knows:** Spotify playlist creation API, DB persistence of playlist history.
**Does not know:** How tracks were ranked or scored.

---

### `libs/feedback/` — Feedback Processor
**Owner:** Data Agent
**Responsibility:** Persists feedback entries, updates `user_track_data`, and detects when the retraining threshold is reached.
**Inputs:** `FeedbackEntry` from the API.
**Outputs:** Updated `user_track_data`, retraining trigger signal.
**Knows:** DB write operations, feedback threshold logic.
**Does not know:** Ranking, ML model, Spotify API.

---

### `db/` — Data Layer
**Owner:** Data Agent
**Responsibility:** SQLAlchemy engine, session factory, ORM models for all 10 tables, repository classes for each entity. Single point of DB access for all modules.
**Key tables:** `tracks`, `artists`, `albums`, `genres`, `artist_genres`, `track_artists`, `user_track_data`, `play_events`, `playlists`, `playlist_tracks`, `auth`.

---

### `apps/api/` — HTTP Entry Point
**Owner:** Backend/API Agent
**Responsibility:** FastAPI application. Defines all routes, handles dependency injection (DB session, SpotifyClient, model loader), launches background tasks (import, retraining). Contains no business logic — delegates entirely to libs/.
**Routers:** auth, import, profile, library, search, player, playlist, feedback, model.

---

### `apps/frontend/` — React Application
**Owner:** Frontend Agent
**Responsibility:** Desktop-first single page application. Three-panel layout: sidebar navigation, track list column, player panel. Integrates Spotify Web Playback SDK for in-browser playback. Typed API client mirroring backend models.
**Sections:** Mi música, Buscar, Descubrir.
**Key components:** TrackCard, PlayerPanel, Sidebar, Header, PlaylistGenerator.

---

## 4. Development Phases

### Phase 0 — Bootstrap
**Goal:** Shared contracts finalized. Repo structure in place. Every agent can start working independently.
**Sequential. Blocks all other phases.**

- Repo structure created with all empty module folders.
- `libs/common/models.py` written, reviewed, and approved. No agent starts coding modules until this file is signed off.
- `libs/common/enums.py` finalized.
- `db/models.py` — all 10 ORM tables defined.
- `db/init_db.py` — creates SQLite file and all tables.
- Spotify OAuth PKCE flow working end-to-end (`/auth/login` → `/auth/callback` → token stored).
- `.env.example`, `pyproject.toml`, `package.json` configured.
- `CLAUDE.md` written with module ownership rules.
- `Dockerfile`, `apps/frontend/Dockerfile`, `docker-compose.yml` — full dev stack starts with `docker compose up`.

**Exit criteria:** `docker compose up` starts both services. Running the app logs in with Spotify and stores a valid token. `python db/init_db.py` creates the database. `from libs.common.models import Track` works.

---

### Phase 1 — Core MVP
**Goal:** User can log in, import their Spotify data, see their library, search any track, and play music in the browser.
**Parallel. Requires Phase 0 complete.**

**Backend/API Agent:**
- `libs/spotify/fetcher.py` — saved tracks, top tracks, top artists, album tracks, with full pagination and rate limiting.
- `POST /import/start` — launches background import task.
- `GET /import/status` — returns import progress.
- `GET /auth/token` — returns fresh token to frontend.

**Domain Core Agent:**
- `libs/profile/builder.py` — builds UserProfile from DB data.
- `libs/profile/weights.py` — computes genre_weights and artist_affinities.
- `GET /profile` endpoint integration.

**Data Agent:**
- `db/repositories/` — TrackRepo, ArtistRepo, GenreRepo, UserTrackDataRepo.
- `libs/feedback/processor.py` — saves feedback to DB.
- `POST /feedback` endpoint integration.

**Frontend Agent:**
- App shell: sidebar, header, three-panel layout.
- Login page with Spotify OAuth redirect.
- Import status banner in header.
- Mi música section: paginated list of saved + liked tracks.
- Buscar section: search input, Spotify results, no persistence.
- PlayerPanel: Spotify Web Playback SDK integration, play on track click.
- TrackCard with like/dislike buttons.

**Exit criteria:** Login → import runs in background → Mi música shows saved tracks → clicking a track plays it in the browser → like/dislike is recorded in DB.

---

### Phase 2 — Discovery
**Goal:** Full recommendation pipeline working. User can generate a personalized playlist and see it in the Descubrir section.
**Parallel. Requires Phase 1 complete.**

**ML/Ranking Agent:**
- `libs/ml/features.py` — user_features and track_features vector builders.
- `libs/ml/training_set.py` — builds labeled dataset from DB with all signal sources.
- `libs/ml/models/user_tower.py` and `item_tower.py` — PyTorch MLP definitions.
- `libs/ml/trainer.py` — training loop with InfoNCE loss, Hard Negative Mining, saves model to `models_store/`.
- `libs/ml/inference.py` — loads model, computes user_embedding and track_embeddings, pre-computes and caches item embeddings.
- `libs/ranker/ranker.py`, `modes.py`, `diversifier.py`.

**Domain Core Agent:**
- `libs/candidates/generator.py` — orchestrates candidate sources.
- `libs/candidates/sources/artist_discography.py` — top artists → Spotify albums → unknown tracks.
- `libs/candidates/sources/genre_search.py` — top genres → Spotify Search → unknown tracks.
- `libs/candidates/deduplicator.py` — removes known tracks.
- `libs/playlist/assembler.py` — selects top N, builds GeneratedPlaylist.
- `libs/playlist/exporter.py` — creates playlist in Spotify.
- `POST /playlist/generate` and `POST /playlist/{id}/export` endpoint integration.

**Frontend Agent:**
- Descubrir section: tone selector (Segura/Mezcla/Novedad), size input, generate button.
- Generated playlist view in track list column.
- Export to Spotify button with result URL.
- Playlist history view.

**Exit criteria:** Pressing Generate in Descubrir returns 20 songs the user hasn't heard, ranked by relevance. Export creates a real playlist in the user's Spotify account.

---

### Phase 3 — Feedback Loop and Onboarding
**Goal:** The system learns from usage. Onboarding allows explicit taste declaration. Play events are recorded. Retraining is automatic.
**Parallel. Requires Phase 2 complete.**

**Backend/API Agent:**
- `libs/feedback/trigger.py` — detects 20-feedback threshold, fires background retraining.
- `POST /player/event` — records play events with ms_played and source.
- `POST /profile/artist` and `POST /profile/playlist` — declares taste, imports discography, assigns training labels.
- `GET /profile/declared` and delete endpoints.
- `POST /model/train` and `GET /model/status`.

**Domain Core Agent:**
- Onboarding label assignment logic: maps declared artist/playlist tracks to training labels.

**Frontend Agent:**
- Onboarding UI in profile or sidebar: search and declare favorite artists and playlists.
- Profile view: genre weights visualization, top artists, model status.
- Play event reporting from PlayerPanel on track change or end.

**Data Agent:**
- Background retraining task wired to feedback trigger.
- Retraining status reflected in `auth` table and surfaced via `GET /model/status`.

**Exit criteria:** Liking 20 songs triggers automatic background retraining. The next generated playlist reflects the updated model. Declaring a new artist expands the training set.

---

### Phase 4 — ML Refinement
**Goal:** Model quality improves. Hard Negative Mining cycles active. System is stable and polished.
**Sequential or light parallel. Requires Phase 3 complete.**

- Hard Negative Mining implemented and active in training loop.
- Pre-computation of item embeddings cached in DB, refreshed on retrain.
- Model evaluation metrics: coverage, diversity, like-rate on generated playlists.
- Performance optimization: candidate fetch time, scoring time.
- Edge case handling: empty library, no feedback yet, Spotify API failures.
- Full test coverage on `libs/` modules.

---

## 5. Parallelization Strategy

### Branch Structure

```
main                          ← always stable and passing tests
  phase-0/bootstrap           ← Architect Agent (sequential, everyone waits)
  phase-1/backend-core        ← Backend/API Agent
  phase-1/domain-core         ← Domain Core Agent
  phase-1/frontend            ← Frontend Agent
  phase-1/data                ← Data Agent
  phase-2/ml-ranking          ← ML/Ranking Agent
  phase-2/discovery-core      ← Domain Core Agent
  phase-2/discovery-frontend  ← Frontend Agent
  phase-3/feedback-loop       ← all agents on their modules
```

### Integration Order

```
phase-0/bootstrap        → main   (unlocks everything)
phase-1/data             → main   (DB + feedback, no external deps)
phase-1/domain-core      → main   (profile, depends on data)
phase-1/backend-core     → main   (depends on domain-core)
phase-1/frontend         → main   (depends on backend-core)
phase-2/ml-ranking       → main   (depends on phase-1/data)
phase-2/discovery-core   → main   (depends on ml-ranking + backend-core)
phase-2/discovery-frontend → main (depends on discovery-core)
phase-3/*                → main   (incremental, any order)
```

### Conflict Prevention Rules

1. Each agent writes only to its assigned folders. No exceptions.
2. `libs/common/` is read-only for all agents except Architect.
3. `db/models.py` changes require Architect review.
4. Two agents never edit the same file simultaneously.
5. If an agent needs to modify a file outside its scope, it opens a discussion first — it never edits directly.

---

## 6. Agent Definitions

### Architect Agent
**Mission:** Maintains design integrity. Approves changes to shared contracts. Arbitrates cross-module conflicts.
**Owns:** `libs/common/`, `design.md`, `plan.md`, `CLAUDE.md`
**Forbidden from modifying:** Any `libs/` module code (read-only except common/)
**Typical tasks:** Review PRs touching models.py, update plan when design changes, resolve interface conflicts between modules.

---

### Backend/API Agent
**Mission:** HTTP layer and Spotify integration. No business logic in routers.
**Owns:** `apps/api/`, `libs/spotify/`
**Must not touch:** `libs/ml/`, `libs/ranker/`, `apps/frontend/`
**Typical tasks:** API endpoints, OAuth flow, SpotifyClient, background tasks, rate limiting.

---

### Domain Core Agent
**Mission:** Core recommendation business logic — profile, candidates, playlist.
**Owns:** `libs/profile/`, `libs/candidates/`, `libs/playlist/`
**Must not touch:** `libs/ml/`, `libs/spotify/` (can import interfaces, not modify), `apps/`
**Typical tasks:** Profile building, candidate generation strategies, playlist assembly and export.

---

### ML/Ranking Agent
**Mission:** Two-Tower model, feature engineering, scoring and ranking.
**Owns:** `libs/ml/`, `libs/ranker/`, `models_store/`
**Must not touch:** `apps/api/`, `apps/frontend/`, `libs/spotify/`
**Typical tasks:** Feature vectors, PyTorch model definitions, training loop, inference, mode weight configuration, diversification.

---

### Data Agent
**Mission:** Persistence layer and feedback processing.
**Owns:** `db/`, `libs/feedback/`
**Must not touch:** `libs/ml/`, `libs/ranker/`, `apps/frontend/`
**Typical tasks:** ORM models, repositories, feedback persistence, retraining trigger, DB initialization.

---

### Frontend Agent
**Mission:** React application, player, and user interactions.
**Owns:** `apps/frontend/`
**Must not touch:** Anything outside `apps/frontend/`
**Typical tasks:** Three-panel layout, Spotify Web Playback SDK, TrackCard, PlayerPanel, section pages, typed API client.

---

### Test Agent
**Mission:** Test coverage across all modules.
**Owns:** `tests/`
**Must not touch:** Production code in `libs/` or `apps/` (reads only)
**Typical tasks:** Unit tests per module, integration tests with TestClient, Spotify response fixtures, property tests for ranker.

---

### Review Agent
**Mission:** Code review before merging. Enforces quality gates.
**Owns:** Read-only across the entire repo.
**Must not touch:** Nothing (review only, no commits)
**Typical tasks:** Check DAG compliance, verify no cross-module imports, confirm tests pass, validate common/ was not modified without approval.

---

## 7. Quality Gates

Every feature branch must satisfy all of the following before merging to main:

### Tests
- [ ] `pytest` passes with no errors.
- [ ] Coverage on `libs/` does not drop below 70%.
- [ ] Unit tests run without network access or real DB (mocked or in-memory SQLite).
- [ ] New public functions in `libs/` have at least one unit test.

### Linting and Types
- [ ] `ruff check .` passes with no errors.
- [ ] `ruff format .` produces no diff.
- [ ] `mypy libs/ apps/api/` passes with no errors.
- [ ] `tsc --noEmit` passes in `apps/frontend/` with no errors.

### Architecture
- [ ] No imports that violate the DAG (common → spotify/profile/ml → candidates/ranker → playlist → api).
- [ ] No business logic inside `apps/api/routers/`.
- [ ] No Spotify API calls outside `libs/spotify/`.
- [ ] No direct DB access outside `db/` and `libs/feedback/`.

### Contracts
- [ ] `libs/common/models.py` and `libs/common/enums.py` have not been modified without Architect approval.
- [ ] If models changed, TypeScript types in `apps/frontend/src/types/` are updated.

### Code Quality
- [ ] No debug statements (`print()`, `breakpoint()`, `console.log()`) in production code.
- [ ] No unrelated changes in the PR.
- [ ] No commented-out code without explanation.

### Documentation
- [ ] If a new API endpoint was added, it is documented in `docs/api.md`.
- [ ] If the scoring formula changed, `docs/scoring.md` is updated.

---

## 8. Dependency Graph

```
Phase 0 — Sequential (each task blocks the next):
  T-001 → T-002 → T-003 → T-004 → T-005

Phase 1 — Parallel (after T-004 / T-005):
  T-001 ──────────────────────────────→ T-011 (frontend can start after T-001)
  T-004 → T-006 ──→ T-007 → T-008 ──→ T-013
                 ↘                  ↘→ T-014
                  → T-009 ──────────→ T-015 → T-016
                  → T-010

Phase 2 — Parallel (T-010 and T-007 must be DONE):
  T-002 ──────────────────────────────→ T-019 ─────────────────────┐
  T-010 → T-017 ──────────────────────────────────────────────→ T-020 → T-021 → T-022 ─→ T-024 → T-025 → T-026
  T-006, T-010 → T-018 ───────────────────────────────────────→ T-020
  T-010, T-007 → T-023 ──────────────────────────────────────────────────────→ T-024

Phase 3 — Parallel (T-020 must be DONE):
  T-009, T-020 → T-027 → T-028
  T-007, T-018 → T-029 → T-030 (also needs T-028, T-015)

Phase 4 — Parallel (T-030 must be DONE):
  T-020 → T-031
  T-021, T-006 → T-032
  T-030 → T-033
  T-028, T-025 → T-034
```

**Critical path (longest chain):**
`T-001 → T-002 → T-003 → T-004 → T-006 → T-010 → T-018 → T-020 → T-021 → T-022 → T-024 → T-025 → T-026`
