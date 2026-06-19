---
id: T-019
phase: 2
agent: ML/Ranking
depends_on: [T-002]
status: DONE
branch: feature/T-019-two-tower-model
pr: "https://github.com/MarianodelRio/SpotifyRanker/pull/5"
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
- `UserTower` and `ItemTower` are identical 2-layer MLPs; they differ only in name so they can be saved and loaded independently.
- `F.normalize(..., p=2, dim=-1)` is used directly in `forward()` — no extra wrapper needed.
- `input_dim` is a constructor parameter so both towers work with any feature vector length T-017 produces.
- Tests cover: output shape, L2 norm ≈ 1.0, dot product ∈ [-1, 1], and `torch.save`/`torch.load` round-trip (using `weights_only=False` for full module serialization).
- PR Reviewer: all 4 acceptance criteria confirmed met; 41 tests pass, ruff/mypy clean, libs/ coverage 100%. No design issues flagged.
