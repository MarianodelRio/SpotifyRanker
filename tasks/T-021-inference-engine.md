---
id: T-021
phase: 2
agent: ML/Ranking
depends_on: [T-020]
status: TODO
branch: ""
pr: ""
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
_Orchestrator fills after completion._
