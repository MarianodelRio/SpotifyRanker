---
id: T-019
phase: 2
agent: ML/Ranking
depends_on: [T-002]
status: IN_PROGRESS
branch: feature/T-019-two-tower-model
pr: ""
---

### T-019 — Two-Tower model definition
**Phase:** 2 | **Agent:** ML/Ranking | **Depends on:** T-002

Define the PyTorch neural network architecture for UserTower and ItemTower. Architecture only — no training, no inference.

**Scope — `libs/ml/models/user_tower.py` and `item_tower.py`**
Both are 2-layer MLPs:
- Input → 64 hidden (ReLU + Dropout 0.2) → 32 output → L2 normalize.
- Input dimension is the feature vector length from T-017 (configured as a constructor parameter).
- Output is a 32-dimensional L2-normalized embedding.

`libs/ml/models/__init__.py` exports `UserTower`, `ItemTower`.

**Acceptance criteria**
- `UserTower(input_dim=N).forward(x)` returns a tensor of shape `(batch, 32)` with L2-normalized rows.
- `ItemTower(input_dim=N).forward(x)` same shape guarantee.
- Dot product of two L2-normalized embeddings is in [-1, 1].
- Models are serializable via `torch.save` and loadable via `torch.load`.

**Notes**
_Orchestrator fills after completion._
