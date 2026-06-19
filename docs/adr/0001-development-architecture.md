# ADR 0001 — Modular Monolith Architecture for TasteRanker MVP

**Date:** 2026-06-17
**Status:** Accepted
**Deciders:** Project architect

---

## Context

TasteRanker needs an architecture that:
1. Allows multiple Claude Code agents to work in parallel without stepping on each other.
2. Keeps the system simple enough to build quickly as a single-developer or small-team project.
3. Preserves the option to extract modules into separate services if the project scales.
4. Does not require Docker, service discovery, or distributed tracing to get started.

The project is a personal tool (single user, local deployment) in its first phase.

---

## Decision

We adopt a **modular monolith** architecture: a single Python process with strict internal module boundaries enforced by convention and code review, not by network.

The module graph is a DAG (no circular imports):

```
libs/common
    ← libs/spotify
    ← libs/profile
    ← libs/candidates
    ← libs/ranker
    ← libs/playlist
    ← libs/feedback
    ← apps/api
```

Each module:
- Communicates with other modules only through types defined in `libs/common/models.py`.
- Has no knowledge of the HTTP layer (`apps/api/`).
- Can be tested independently without a running server or database.
- Is owned by exactly one agent, preventing editing conflicts.

---

## Rationale

### Why not microservices from the start?

Microservices impose overhead that slows down MVP development by 3–5x:
- Network serialization and latency between every module call.
- Service discovery, health checks, and deployment for each service.
- Distributed tracing to debug cross-service issues.
- Contract versioning between services.
- Harder to run locally without Docker Compose or Kubernetes.

For a single-user personal tool, none of these problems exist. The tradeoff is all cost, no benefit in v0.

### Why a modular monolith instead of a big ball of mud?

Module boundaries enforced by convention give us the main benefit of microservices — independent development and reasoning — without the operational overhead. If we need to extract `libs/ranker/` into an async scoring service later, we change only the adapter (how `apps/api/` calls the ranker) and nothing else.

### Why SQLite as the database?

- Zero setup, no external process.
- Sufficient for single-user local use.
- SQLAlchemy abstraction means migrating to PostgreSQL requires only a connection string change and a migration.
- The ORM layer (`db/`) is isolated: no other module imports SQLAlchemy models directly.

### Why FastAPI for the API layer?

- Native async support for Spotify API calls.
- Pydantic integration for request/response validation (same models as domain layer).
- OpenAPI docs generated automatically.
- TestClient allows integration tests without a running server.

### Why React + Vite + TypeScript for the frontend?

- TypeScript ensures the frontend stays in sync with backend Pydantic models.
- Vite is fast and requires no configuration.
- The frontend is a pure UI layer — no business logic, no direct Spotify calls.

---

## Consequences

### Positive
- One command to start the whole system: `uvicorn apps.api.main:app --reload`.
- Every module can be tested in isolation without network or DB.
- Claude Code agents can work in parallel without merge conflicts (one agent per module folder).
- The codebase is simple enough for a single person to understand completely.

### Negative
- All modules share the same process: a crash in one module crashes everything.
- No independent scaling of heavy components (e.g., ranking a large batch).
- If multiple users are added, the single-user assumptions in `db/` will need to change.

### Constraints accepted
- `libs/common/models.py` is a shared contract — changes require coordination.
- Module boundaries are enforced by convention, not by compilation; a developer could accidentally import across boundaries.
- The system must stay single-user until a deliberate multi-user refactor (separate ADR needed).

---

## Module Extraction Roadmap (Future)

When the time comes, modules can be extracted in this order of increasing complexity:

| Module | When to extract | What changes |
|--------|----------------|--------------|
| `libs/ranker/` | When ML scoring needs async batch processing | Replace direct call with a job queue |
| `libs/spotify/` | When caching or multi-user is needed | Replace with a proxy service |
| `libs/candidates/` | When external sources (MusicBrainz) are slow | Move to a scheduled batch job |
| `libs/feedback/` | When feedback volume grows | Replace with an event stream |

Each extraction requires only changing the adapter in `apps/api/` — no other module changes.

---

## Alternatives Considered

### Alternative A: Django monolith
Rejected. Django's ORM and view system encourage mixing HTTP and domain logic. FastAPI with separate modules maintains cleaner separation.

### Alternative B: FastAPI + separate React SPA + separate scoring service (3 processes)
Rejected for v0. Adds Docker Compose, CORS configuration, and distributed debugging complexity with no benefit at single-user scale.

### Alternative C: Pure Python script (no API)
Considered for the MVP but rejected. The feedback loop and playlist history require persistence and a UI, which a script can't provide elegantly.
