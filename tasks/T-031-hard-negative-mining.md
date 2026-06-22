---
id: T-031
phase: 4
agent: ML/Ranking
depends_on: [T-020]
status: READY_FOR_PR
branch: feature/T-031-hard-negative-mining
pr: ""
---

### T-031 — Hard Negative Mining
**Phase:** 4 | **Agent:** ML/Ranking | **Depends on:** T-020

Add Hard Negative Mining to the training loop to improve model quality on edge cases.

**Scope — extends `libs/ml/trainer.py`**
After N initial training epochs, run HNM cycles:
1. Score all training examples with the current model.
2. Find negatives (label=0) that score unexpectedly high (above a threshold, e.g., top 20% of negative scores).
3. Add these "hard negatives" back to the training batch with increased weight.
4. Train for additional epochs with the augmented set.

HNM is optional and controlled by a flag in the trainer config (`use_hnm: bool`, default True). The base training loop (T-020) must still work correctly without HNM.

**Acceptance criteria**
- HNM runs after the base training epochs without errors.
- Hard negatives identified by HNM have score > threshold before retraining.
- Training loss with HNM is lower than without HNM on the same dataset (sanity test with synthetic data).
- `use_hnm=False` produces the same result as the T-020 training loop (no regression).

**Notes**
- Refactored the inner training loop into `_run_epochs()` helper so it can be called once for base training and once for HNM retraining without duplication.
- `_mine_hard_negatives()` runs in `torch.no_grad()` / eval mode; calls `user_tower.train()` / `item_tower.train()` before HNM epochs resume.
- HNM augments tensors by appending hard-negative rows with weight × `hnm_weight_multiplier` (default 2.0); does not mutate the original examples list.
- All 4 new tests pass: run-without-errors, score-above-threshold, loss-lower-with-HNM, use_hnm=False regression guard. Full suite: 254 passed.
