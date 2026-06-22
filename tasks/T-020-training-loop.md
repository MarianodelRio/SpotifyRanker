---
id: T-020
phase: 2
agent: ML/Ranking
depends_on: [T-017, T-018, T-019]
status: READY_FOR_PR
branch: feature/T-020-training-loop
pr: ""
---

### T-020 — Training loop (InfoNCE)
**Phase:** 2 | **Agent:** ML/Ranking | **Depends on:** T-017, T-018, T-019

Implement the full training pipeline: build dataset, train UserTower + ItemTower with InfoNCE loss, save trained models.

**Scope — `libs/ml/trainer.py`**
`train(session) → TrainingResult`:
1. Calls `build_training_set` to get labeled examples.
2. Converts to PyTorch tensors. Builds DataLoader with in-batch negatives.
3. InfoNCE loss: for each positive pair (user_emb, item_emb), score against all other items in the batch as negatives. Loss = -log(exp(pos_score/τ) / sum(exp(all_scores/τ))) where τ is a temperature parameter (default 0.1).
4. Trains UserTower + ItemTower jointly for N epochs (configurable, default 20). Adam optimizer, lr=1e-3.
5. Saves `user_tower.pt` and `item_tower.pt` to `models_store/`. Also saves the genre vocabulary file.
6. Returns `TrainingResult`: epochs, final_loss, examples_count, trained_at.

**Acceptance criteria**
- Training on a dataset of 100+ examples completes without errors.
- Loss decreases over epochs (sanity check: final loss < initial loss).
- Model files are written to `models_store/` after training.
- Training on a 1000-example dataset completes in under 120 seconds on CPU.
- No GPU required. Training uses `device='cpu'` explicitly.

**Notes**
- **Signature deviation:** `train(session, profile) → TrainingResult` instead of the task-spec's `train(session)`. Importing `libs.profile` from `libs.ml` would violate the DAG (they are siblings under `common`). The API layer calls `build_profile(session)` then passes the result to `train()`. Human approved this before implementation.
- **`TowerPair` dataclass** also defined in `trainer.py` for use by T-021 (inference engine).
- **InfoNCE implementation:** single-user setting means all user feature vectors are identical within a run. In-batch negatives are all items in the batch; loss computed only over positives (label ≥ 0.5), weighted by `example.weight`. Gradient clipping (max_norm=1.0) added as safety net per agent guidance.
- **Track metadata query:** trainer does a separate `selectinload` DB query to load track → artist → genres for feature building, since `build_training_set` only returns `track_id`.
- **212 unit tests pass.** 6 new tests added in `tests/unit/test_trainer.py`.
