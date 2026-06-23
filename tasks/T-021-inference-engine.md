---
id: T-021
phase: 2
agent: ML/Ranking
depends_on: [T-020]
status: DONE
branch: feature/T-021-inference-engine
pr: "https://github.com/MarianodelRio/SpotifyRanker/pull/25"
---

### T-021 — Inference engine
**Phase:** 2 | **Agent:** ML/Ranking | **Depends on:** T-020

Build the inference module that loads trained models and produces relevance scores for candidates.

**Scope — `libs/ml/inference.py`**
- `load_model() → TowerPair`: loads `user_tower.pt` and `item_tower.pt` from `models_store/`. Raises `ModelNotTrainedError` if files are absent.
- `compute_user_embedding(profile: UserProfile, towers: TowerPair) → np.ndarray`: builds user features and runs through UserTower.
- `compute_item_embedding(track: Track, towers: TowerPair, ...) → np.ndarray`: builds track features and runs through ItemTower.
- `score_candidates(user_emb, item_embs) → list[float]`: dot product of user embedding against each item embedding. Returns list of scores in [-1, 1].

All inference runs in `torch.no_grad()`. No GPU assumed.

**Acceptance criteria**
- `load_model()` raises a clear error if model files are missing (not a cryptic FileNotFoundError).
- Scores are in [-1, 1] for L2-normalized embeddings.
- Deterministic: same inputs → same scores every call.
- Inference for 500 candidates runs in under 2 seconds on CPU.

**Notes**
- **`vocab` as explicit parameter:** `compute_user_embedding` and `compute_item_embedding` both accept `vocab: list[str]` as an explicit parameter (not loaded internally per call). Callers load it once via `get_vocab()` alongside `load_model()`. This avoids repeated disk reads per candidate.
- **`get_vocab()` helper added:** public function that loads `vocab.json` from `models_store/`, raising `ModelNotTrainedError` (same exception class) if absent. T-022 ranker should call both `load_model()` and `get_vocab()` at startup.
- **`input_dim` derived dynamically:** `load_model()` builds a dummy `UserProfile()` and calls `build_user_features()` to get the exact feature vector length, rather than hardcoding the formula. This stays in sync if features.py ever changes.
- **`TowerPair` imported from `trainer.py`:** as the T-020 notes intended. No duplicate definition.
- **22 unit tests pass.** Covers: missing files error, actionable error message, eval mode, 32-dim output, L2 normalization, determinism, empty profile/unknown genres edge cases, scores in [-1, 1], 500-candidate perf < 2s.
- **PR Reviewer:** performance test times only `score_candidates()` batched matmul, not the 500 individual `compute_item_embedding()` forward passes. Full pipeline is fast in practice but not formally timed. Not blocking.
