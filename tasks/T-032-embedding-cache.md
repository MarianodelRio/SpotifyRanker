---
id: T-032
phase: 4
agent: ML/Ranking
depends_on: [T-021, T-006]
status: TODO
branch: ""
pr: ""
---

### T-032 — Item embedding cache
**Phase:** 4 | **Agent:** ML/Ranking | **Depends on:** T-021, T-006

Pre-compute and cache item embeddings for all known tracks in the database, so scoring at playlist generation time is fast.

**Scope**
- After training completes, run `compute_item_embedding` for all tracks in the `tracks` table and store embeddings in a new column or a separate cache table (`track_embeddings`: `track_id FK, embedding BLOB`).
- At inference time, `ranker.rank()` loads cached embeddings from DB instead of recomputing them.
- Cache is invalidated and rebuilt on every retraining.
- For candidate tracks not yet in the cache (new tracks fetched at generation time), compute embeddings on the fly.

**Acceptance criteria**
- Generating a playlist uses cached embeddings for known tracks (verifiable by timing: generation is faster after cache is built).
- Cache is rebuilt after every retraining.
- New candidate tracks not in the cache are still scored correctly (on-the-fly computation).
- Cache build for 10,000 tracks completes in under 60 seconds on CPU.

**Notes**
_Orchestrator fills after completion._
