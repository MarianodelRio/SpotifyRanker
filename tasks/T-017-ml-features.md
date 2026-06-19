---
id: T-017
phase: 2
agent: ML/Ranking
depends_on: [T-010]
status: TODO
branch: ""
pr: ""
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
_Orchestrator fills after completion._
