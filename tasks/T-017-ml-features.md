---
id: T-017
phase: 2
agent: ML/Ranking
depends_on: [T-010]
status: DONE
branch: feature/T-017-ml-features
pr: "https://github.com/MarianodelRio/SpotifyRanker/pull/15"
---

### T-017 — ML feature engineering
**Phase:** 2 | **Agent:** ML/Ranking | **Depends on:** T-010

Build the feature vector builders that convert `UserProfile` and `Track` domain objects into numeric vectors for the Two-Tower model.

**Scope — `libs/ml/features.py`**
- `build_user_features(profile: UserProfile) → np.ndarray`: genre preference weights (top N genres), artist affinity scores (top 20 artists), global like/ratio, diversity score. Output: fixed-length float vector.
- `build_track_features(track: Track, genres: list[str], artist_popularity: int) → np.ndarray`: genre multi-hot (same N genres as user vector), normalized popularity, normalized artist popularity, is-unknown-artist flag, release recency score. Output: same fixed dimension as user vector.
- Genre vocabulary: derived from all genres in DB, fixed after first build. Stored as a simple JSON file in `models_store/`.

**Acceptance criteria**
- Both functions produce float vectors of the same fixed dimension.
- All values are in [0, 1] (normalized).
- Deterministic: same inputs always produce the same vector.
- Unknown genres map to zero (no errors on unseen genres).
- Tested with synthetic UserProfile and Track objects (no DB required).

**Notes**
- Vector dimension is `len(vocab) + 20 + 4` for both user and track (genre slots + 20 artist affinity slots + 4 scalar slots). User's last 2 scalar slots are zero-padded; track's artist-affinity slots (positions [len(vocab)..+19]) are zero-padded. Same fixed shape guaranteed.
- `Track` has no `release_date` field, so `release_recency` is always 0.0. This is intentional — the slot is reserved and will become meaningful when the field is added (T-002 frozen contract).
- `_fixed_dim()` is exported from `libs/ml/features.py` and used directly by the Two-Tower models (T-018, T-019) to derive `input_dim`.
- Vocab helpers (`build_genre_vocab`, `save_vocab`, `load_vocab`) are ready for use by the training dataset builder (T-018).
- 30 unit tests, all passing. No DB, no network.
- PR Reviewer note: the original feature branch had a stale `chore(T-015): claim [IN_PROGRESS]` commit that would have downgraded T-015's status on merge. The branch was rebuilt clean from origin/master via cherry-pick before opening the PR. The spurious commit came from git state confusion in the shared main-repo working directory during the orchestration session.
- All checks at PR open: 197 tests passed (98% libs coverage), ruff clean, mypy clean (29 source files).
