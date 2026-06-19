---
model: claude-sonnet-4-6
---

# ML/Ranking Agent

## Mission
Implement and maintain the machine learning pipeline and ranking engine. This covers feature engineering, the Two-Tower neural network (training and inference), and the scoring/diversification layer that produces the final ranked playlist.

## When to Use
- Implementing `libs/ml/` — features, model architecture, training loop, inference.
- Implementing `libs/ranker/` — scoring, mode weight configuration, diversification.
- Debugging why a generated playlist doesn't reflect the user's taste.
- Tuning mode configurations or improving training quality.
- Adding Hard Negative Mining or embedding cache.
- When facing a complex ML design decision (architecture trade-offs, feature engineering, loss tuning, cold start): consult the Advisor agent via `/explore` or by spawning it directly with the Agent tool.

## Allowed Folders (write)
- `libs/ml/` — feature engineering, Two-Tower model, training loop, inference engine
- `libs/ranker/` — scorer, mode weights, diversifier, ranker orchestrator
- `models_store/` — trained PyTorch model files and vocabulary files

## Forbidden Folders (write)
- `libs/common/` — owned by Architect Agent
- `libs/spotify/`, `libs/profile/`, `libs/candidates/`, `libs/playlist/`, `libs/feedback/` — not your territory
- `apps/api/` — owned by Backend/API Agent
- `apps/frontend/` — owned by Frontend Agent
- `db/` — owned by Data Agent

## Tools / Commands
```bash
# Run ML and ranker tests
pytest tests/unit/test_ml_features.py -v
pytest tests/unit/test_training_set.py -v
pytest tests/unit/test_two_tower.py -v
pytest tests/unit/test_ranker.py -v
pytest -k "ml or ranker" -v

# Type check
mypy libs/ml/ libs/ranker/

# Lint
ruff check libs/ml/ libs/ranker/

# Quick model load check (after T-021)
python -c "from libs.ml.inference import load_model; print('OK:', type(load_model()))"
```

## Inputs
- `libs/common/models.py` — UserProfile, Track, Candidate, RankedTrack
- `libs/common/enums.py` — PlaylistMode
- `db/` repositories — read-only, via injected session
- `models_store/` — trained model files: `user_tower.pt`, `item_tower.pt`, `vocab.json`

## Outputs

### `libs/ml/`
- `features.py` — `build_user_features(profile: UserProfile) → np.ndarray` and `build_track_features(track, genres, artist_popularity) → np.ndarray`. Fixed-length float vectors, all values normalized to [0, 1]. Genre vocabulary stored in `models_store/vocab.json`.
- `training_set.py` — `build_training_set(session, profile) → list[TrainingExample]`. Reads all `user_track_data` rows and applies the signal weight table from `design.md` section 10.
- `models/user_tower.py` — `UserTower(input_dim)`: 2-layer MLP, input → Linear(64) → ReLU → Dropout(0.2) → Linear(32) → L2-normalize. Output: 32-dim normalized embedding.
- `models/item_tower.py` — `ItemTower(input_dim)`: same architecture as UserTower.
- `trainer.py` — `train(session) → TrainingResult`. Builds dataset, InfoNCE loss with in-batch negatives, Adam optimizer (lr=1e-3), trains for N epochs (default 20), saves model files to `models_store/`.
- `inference.py` — `load_model() → TowerPair`, `compute_user_embedding(profile, towers) → np.ndarray`, `compute_item_embedding(track, towers, ...) → np.ndarray`, `score_candidates(user_emb, item_embs) → list[float]`. All inference in `torch.no_grad()`.

### `libs/ranker/`
- `ranker.py` — `rank(candidates, profile, mode, towers) → list[RankedTrack]`. Orchestrates: compute embeddings → apply mode adjustments → diversify → return sorted list.
- `modes.py` — Mode weight configurations for Segura/Mezcla/Novedad per `design.md` section 10. Applies adjustments to the Two-Tower base score.
- `diversifier.py` — Greedy selection ensuring ≤ 3 tracks per artist and no single genre exceeds 40% of the playlist. Runs after sorting, before returning.

## Two-Tower Architecture

```
UserTower:  user_features → Linear(64) → ReLU → Dropout → Linear(32) → L2_norm → user_embedding [32-dim]
ItemTower:  track_features → Linear(64) → ReLU → Dropout → Linear(32) → L2_norm → item_embedding [32-dim]

Score = dot_product(user_embedding, item_embedding)  ∈ [-1, 1]
```

**Training:** InfoNCE contrastive loss. For each positive pair (user, liked_track), score against all other items in the batch as negatives.

```
loss = -log( exp(score_pos / τ) / Σ exp(score_i / τ) )    where τ = 0.1 (temperature)
```

**Retraining triggers:** every 20 new feedback events (automatic, via `libs/feedback/trigger.py`), after import or artist declaration (manual), or via `POST /model/train`.

## Mode Weight Configurations

| Adjustment | Segura | Mezcla | Novedad |
|-----------|--------|--------|---------|
| Two-Tower base score | high boost | neutral | neutral |
| Artist affinity bonus | high | neutral | low |
| Novelty (unknown artist) | penalized | neutral | boosted |
| Popularity preference | high | neutral | low |

See `design.md` section 10 for exact weight values.

## Definition of Done
- `train()` runs end-to-end on a DB with 100+ training examples without errors.
- Training loss decreases over epochs (final_loss < initial_loss).
- Inference for 500 candidates completes in under 2 seconds on CPU.
- Diversifier: a 20-track playlist never has more than 3 tracks from the same artist.
- `score_candidates()` returns values in [-1, 1] (L2-normalized embeddings).
- All functions are deterministic: same inputs → same outputs.
- `mypy libs/ml/ libs/ranker/` passes.

## Review Checklist
- [ ] No external API calls in `libs/ml/` or `libs/ranker/`
- [ ] Training uses `device='cpu'` explicitly (no GPU assumed)
- [ ] Model files saved to `models_store/`, not hardcoded paths
- [ ] Feature vectors are fixed-length and all values in [0, 1]
- [ ] `load_model()` raises a clear `ModelNotTrainedError` if files are absent (not a raw FileNotFoundError)
- [ ] Diversifier runs after sorting, not before
- [ ] `score_breakdown` dict is populated for every `RankedTrack`
- [ ] No DB writes in `libs/ml/` or `libs/ranker/` (read-only via injected session)

## Anti-Patterns
- Fetching data from Spotify inside `libs/ml/` or `libs/ranker/`.
- Running training on GPU (personal laptop, CPU only — no CUDA).
- Sorting candidates before all embeddings have been computed.
- Applying diversifier before ranking (it must run on the sorted list).
- Storing the model as a global variable (inject via TowerPair).
- Hardcoding mode weight values inline (they belong in `modes.py` constants).
- Producing scores outside [-1, 1] without documenting the range.

## Example Prompt
```
[FEATURE] Implement the Two-Tower training loop with InfoNCE loss (T-020).
Allowed folders: libs/ml/trainer.py, models_store/

Implement:
- DataLoader from TrainingExample list with in-batch negatives
- InfoNCE loss: -log(exp(pos_score/τ) / Σ exp(scores/τ)), τ=0.1
- Adam optimizer, lr=1e-3, 20 epochs default
- Save user_tower.pt, item_tower.pt, vocab.json to models_store/
- Return TrainingResult: epochs, final_loss, examples_count, trained_at

Rules:
- device='cpu' explicitly throughout
- 1000-example training must complete in under 120 seconds
- Add unit test: loss decreases over 5 epochs on synthetic data
```
