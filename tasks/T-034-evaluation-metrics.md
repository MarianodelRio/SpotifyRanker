---
id: T-034
phase: 4
agent: ML/Ranking
depends_on: [T-028, T-025]
status: PR_OPEN
branch: feature/T-034-evaluation-metrics
pr: "https://github.com/MarianodelRio/SpotifyRanker/pull/36"
---

### T-034 — Evaluation metrics
**Phase:** 4 | **Agent:** ML/Ranking | **Depends on:** T-028, T-025

Add lightweight metrics to evaluate recommendation quality over time.

**Scope**
- `like_rate_on_generated`: fraction of generated playlist tracks that the user eventually liked (tracks `feedback='like'` where `playlist_id` is set). Updated on each feedback event.
- `playlist_diversity_score`: average number of distinct artists and genres in the last 5 generated playlists.
- `training_loss_history`: list of the last N training losses (already partially in TrainingResult).
- All metrics available at `GET /model/status` (added to the response).
- No external tracking, no dashboards — all computed from the local DB.

**Acceptance criteria**
- `GET /model/status` returns `like_rate`, `diversity_score`, and `loss_history`.
- `like_rate` is accurate: if the user liked 5 of the last 10 generated tracks, it returns 0.5.
- All metrics compute without errors on an empty history (return null or 0.0, not exceptions).

**Notes**
- `libs/ml/metrics.py` is a new file with three functions: `compute_like_rate`, `compute_diversity_score`, `append_loss_history`.
- `apps/api/routers/model_router.py` is out-of-agent-folder; touched to extend the `ModelStatus` response model and wire up the DB session dependency on `GET /model/status`. Justification: task scope explicitly requires adding metrics to this endpoint.
- `loss_history` is persisted in `training_state.json` (appended after each train run, capped at 20 entries).
- `like_rate` and `diversity_score` return `None` on empty DB (not 0.0), which serializes to JSON `null` — satisfies the acceptance criteria.
- Pre-existing mypy error in `libs/candidates/sources/artist_discography.py` (unrelated to this task) was present before and after.
- PR Reviewer: `test_diversity_score_uses_last_5_playlists` may be order-sensitive if multiple playlists share the same `created_at` (SQLite in-memory). Currently passing; flag for attention if it becomes flaky.
- PR Reviewer: rebase dropped the empty claim commit cleanly; branch rebased onto master with no design conflicts.
