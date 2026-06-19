# TasteRanker — Software Design Document

> **Status:** Design complete. Source of truth for plan and task generation.
> **Scope:** Single-user, local-first, personal music discovery engine with in-app playback.

---

## 1. Overview

TasteRanker is a personal music discovery web application that connects to Spotify and builds a transparent, user-controlled recommendation engine. The system learns the user's taste from their Spotify library and explicit declarations, generates candidate songs from the Spotify catalog, ranks them using a deep learning model (Two-Tower), and plays them directly in the browser.

The core differentiator is that the recommendation pipeline is entirely owned by the system — it does not rely on Spotify's restricted recommendation endpoints. The user can listen, give feedback, and the system improves over time.

---

## 2. Goals and Non-Goals

### Goals

- Import personal Spotify data (saved tracks, top tracks) as the initial taste signal.
- Allow users to explicitly declare favorite artists and playlists to bootstrap the recommendation model.
- Generate personalized discovery playlists using a Two-Tower deep learning model.
- Play music directly in the browser via Spotify Web Playback SDK.
- Collect like/dislike feedback to continuously improve recommendations.
- Export generated playlists to Spotify.

### Non-Goals (MVP)

- Multi-user support. Single user only.
- Integration with Last.fm, MusicBrainz, or ListenBrainz. Spotify only.
- Audio feature analysis (Spotify's endpoints are restricted for new apps).
- Mobile application.
- Cloud deployment. Local-first.
- Full Spotify client replacement (no browse, no social features, no podcasts).

---

## 3. User and Context

**Single user. Spotify Premium required.**

The user is a personal Spotify listener who wants discovery recommendations beyond what Spotify's native Discover Weekly provides. They use the app on a desktop browser and interact regularly to give feedback that improves the model.

**Hardware context:** personal laptop (no GPU). The ML pipeline must run efficiently on CPU.

**Spotify Premium** is required for the Web Playback SDK (in-browser audio playback).

---

## 4. Functional Requirements

### Authentication

- FR-01: User logs in via Spotify OAuth 2.0 PKCE flow.
- FR-02: Access token and refresh token are stored locally in the database.
- FR-03: Token refresh is handled automatically and transparently.

### Data Import

- FR-04: On first login, the system automatically imports saved tracks and top tracks (short, medium, long term) from Spotify in the background.
- FR-05: The frontend shows import progress while the user can already navigate the app. Playlist generation activates when import completes.
- FR-06: A manual "refresh" button triggers a full reimport of Spotify data.
- FR-07: Artist and album metadata (including genres) is fetched and cached for all imported tracks.

### Onboarding — Explicit Taste Declaration

- FR-08: The user can search and declare favorite artists. The system imports their full discography and assigns training labels.
- FR-09: The user can search and declare favorite playlists. The system imports all their tracks and assigns training labels.
- FR-10: Declared artists and playlists are stored and can be reviewed or removed.

### My Music Section

- FR-11: Displays all tracks where the user has a positive signal: saved on Spotify or liked within the app. Unified view.
- FR-12: Tracks are shown with album art, title, artist, and duration.

### Search Section

- FR-13: User can search the full Spotify catalog (any track, artist, or album) via Spotify Search API.
- FR-14: Search results are displayed but not persisted. Only tracks the user interacts with (play, like, dislike) are stored.

### Discover Section

- FR-15: User selects a discovery tone: **Segura** (safe, familiar), **Mezcla** (balanced), or **Novedad** (adventurous, new artists).
- FR-16: User selects the number of songs (numeric input).
- FR-17: The system generates a playlist synchronously (spinner while generating).
- FR-18: Generated tracks are shown in the list column. The user can listen, give feedback, and then export to Spotify.
- FR-19: History of previously generated playlists is accessible.

### Playback

- FR-20: Clicking any track in any section plays it immediately via Spotify Web Playback SDK.
- FR-21: The player panel (right column) shows album art, title, artist, progress bar, and playback controls.
- FR-22: No automatic queue. The user clicks to play one track at a time.
- FR-23: Every play event (track, duration played, source section, playlist if applicable) is recorded.

### Feedback

- FR-24: Like and dislike buttons are available in the player panel and on every track card.
- FR-25: Feedback is binary: like or dislike. One entry per track, updated if the user changes opinion.
- FR-26: Feedback is recorded with its source (my_music, search, discover) and the playlist it came from if applicable.
- FR-27: Accumulated feedback triggers automatic model retraining in the background every 20 new interactions.

### Playlist Export

- FR-28: A generated playlist can be exported to Spotify with one button. The system creates the playlist in the user's Spotify account and returns the URL.

### Model

- FR-29: The user can manually trigger model retraining from the interface.
- FR-30: The interface shows when the model was last trained and how many training examples it has.

---

## 5. Non-Functional Requirements

- NFR-01: The app runs on a standard laptop without GPU. ML training must complete in under 2 minutes.
- NFR-02: Playlist generation (candidate fetch + ranking) must complete in under 15 seconds.
- NFR-03: The database is SQLite. No external database server required.
- NFR-04: All Spotify tokens are stored locally. No data leaves the machine except to Spotify's API.
- NFR-05: The backend must handle Spotify API rate limiting gracefully (retry with backoff).
- NFR-06: The modular architecture must allow parallel development by multiple agents with no cross-module conflicts.
- NFR-07: The development environment runs via Docker Compose. `docker compose up` must start the full stack (api + frontend) from a clean checkout with no manual Python or Node setup.

---

## 6. System Architecture

### Pattern: Modular Monolith

A single deployable unit with strict internal module boundaries. Modules communicate only through shared domain models in `libs/common/`. No microservices in v1. Module boundaries are designed so each module could be extracted to a service later without changing its interface.

### Repository Structure

```
tasteranker/
├── Dockerfile                ← backend image (Python 3.11, PyTorch CPU-only)
├── docker-compose.yml        ← dev orchestration (api + frontend + volumes)
├── .dockerignore
├── apps/
│   ├── api/                  ← FastAPI HTTP entry point
│   └── frontend/
│       ├── Dockerfile        ← frontend image (Node, Vite dev server)
│       └── ...               ← React + Vite + TypeScript
├── libs/
│   ├── common/               ← PROTECTED: shared Pydantic models and enums
│   ├── spotify/              ← Spotify API adapter (pure I/O)
│   ├── profile/              ← User taste profile builder (stateless)
│   ├── candidates/           ← Candidate track generation
│   ├── ml/                   ← Feature engineering, Two-Tower training and inference
│   ├── ranker/               ← Scoring, mode configuration, diversification
│   ├── playlist/             ← Playlist assembly and Spotify export
│   └── feedback/             ← Feedback persistence and retraining trigger
├── db/                       ← SQLAlchemy engine, ORM models, repositories
├── models_store/             ← Trained PyTorch model files
├── tests/                    ← Unit and integration tests
└── scripts/                  ← Dev CLI utilities
```

### Dependency Graph (strict DAG, no reverse imports)

```
common
  ↑
  ├── spotify          (I/O only)
  ├── profile          (stateless, reads from DB)
  ├── ml               (feature engineering + model)
  │
  ├── candidates       (uses spotify + profile)
  ├── ranker           (uses ml + profile)
  │
  ├── playlist         (uses spotify + ranker)
  ├── feedback         (reads/writes DB only)
  │
  └── api              (orchestrates all modules)
```

### Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11+, FastAPI, Uvicorn |
| ORM | SQLAlchemy 2.0, Alembic |
| Database | SQLite |
| ML | PyTorch, scikit-learn, NumPy |
| Spotify | httpx (async HTTP client) |
| Frontend | React 18, TypeScript, Vite, Tailwind CSS |
| Playback | Spotify Web Playback SDK |
| Testing | pytest, pytest-asyncio, httpx (TestClient) |
| Dev environment | Docker, Docker Compose |

---

## 7. Data Model

### Design Principles

- Surrogate UUIDs as primary keys everywhere. Spotify IDs are external identifiers stored as UNIQUE constraints.
- All mutable tables have `created_at` and `updated_at` timestamps.
- Cache tables (tracks, artists, albums) use UPSERT on reimport.
- User data tables (user_track_data, play_events) are append-only or single-row-per-track.

### Schema

```
── Music Metadata Cache (from Spotify, upserted on import) ──────────────

artists
  id UUID PK | spotify_id UNIQUE | name | popularity | image_url
  is_blocked BOOL DEFAULT false | created_at | updated_at

genres
  id INT PK AUTOINCREMENT | name UNIQUE

artist_genres
  artist_id FK→artists | genre_id FK→genres | PK(artist_id, genre_id)

albums
  id UUID PK | spotify_id UNIQUE | title | artist_id FK→artists
  release_year | total_tracks | image_url | created_at | updated_at

tracks
  id UUID PK | spotify_id UNIQUE | title | album_id FK→albums
  duration_ms | popularity | preview_url | created_at | updated_at

track_artists
  track_id FK→tracks | artist_id FK→artists | is_primary BOOL
  PK(track_id, artist_id)

── User Signals ─────────────────────────────────────────────────────────

user_track_data                    ← all user signals per track, one row per track
  track_id FK→tracks UNIQUE
  is_saved BOOL DEFAULT false      ← saved on Spotify or liked in app
  save_source ENUM(spotify, app)   ← origin of the save
  saved_at TIMESTAMP
  feedback ENUM(like, dislike)     ← explicit feedback, nullable
  feedback_at TIMESTAMP
  play_count INT DEFAULT 0         ← plays within the app
  last_played_at TIMESTAMP
  top_position_short INT           ← 1-50 or null (Spotify top tracks)
  top_position_medium INT
  top_position_long INT

play_events                        ← individual play history
  id UUID PK | track_id FK→tracks
  played_at TIMESTAMP | ms_played INT
  source ENUM(my_music, search, discover)
  playlist_id FK→playlists nullable

── Generated Content ────────────────────────────────────────────────────

playlists
  id UUID PK | name | mode ENUM(safe, balanced, adventurous)
  size INT | created_at | exported_at | spotify_playlist_id | spotify_url

playlist_tracks
  id UUID PK | playlist_id FK→playlists | track_id FK→tracks
  rank INT | final_score FLOAT | score_breakdown JSON
  UNIQUE(playlist_id, rank) | UNIQUE(playlist_id, track_id)

── System ───────────────────────────────────────────────────────────────

auth
  spotify_user_id | display_name | access_token | refresh_token
  token_expires_at | import_status ENUM(idle, running, completed, failed)
  import_started_at | import_completed_at
```

---

## 8. API Design

All endpoints return JSON. Authentication is validated via the stored token on every request.

```
── Auth ─────────────────────────────────────────────────────────────────
GET  /auth/login           → redirect to Spotify OAuth
GET  /auth/callback        → exchange code for token, store in auth table
GET  /auth/status          → {is_authenticated, display_name}
POST /auth/logout          → clear token
GET  /auth/token           → return fresh access_token (for Web Playback SDK)

── Import ───────────────────────────────────────────────────────────────
POST /import/start         → trigger background import from Spotify
GET  /import/status        → {status, tracks_imported, artists_imported}

── Profile / Onboarding ─────────────────────────────────────────────────
GET  /profile              → {genre_weights, top_artists, stats}
POST /profile/artist       → {spotify_id} → import discography + assign labels
POST /profile/playlist     → {spotify_id} → import tracks + assign labels
GET  /profile/declared     → list of declared artists and playlists
DELETE /profile/artist/{id} → remove declared artist

── Library ──────────────────────────────────────────────────────────────
GET  /library              → paginated list of saved + liked tracks with metadata

── Search ───────────────────────────────────────────────────────────────
GET  /search?q=&type=      → proxy to Spotify Search, returns tracks/artists

── Player ───────────────────────────────────────────────────────────────
POST /player/event         → {track_id, ms_played, source, playlist_id}
                             records play event, updates play_count

── Playlist ─────────────────────────────────────────────────────────────
POST /playlist/generate    → {mode, size} → runs full pipeline, returns playlist
GET  /playlist/history     → list of previously generated playlists
GET  /playlist/{id}        → full playlist detail with tracks and scores
POST /playlist/{id}/export → create playlist in Spotify, return URL

── Feedback ─────────────────────────────────────────────────────────────
POST /feedback             → {track_id, feedback_type, source, playlist_id}
                             updates user_track_data, triggers retraining if threshold

── Model ────────────────────────────────────────────────────────────────
POST /model/train          → manually trigger retraining (background task)
GET  /model/status         → {trained_at, examples_count, active_level}
```

---

## 9. Frontend Design

### Layout

Desktop-first single page application. Fixed three-panel layout:

```
┌──────────────────────────────────────────────────────────────────┐
│                           HEADER                                 │
│   [Logo]                     [Import status]  [User name]        │
├────────────┬─────────────────────────────┬───────────────────────┤
│            │                             │                       │
│  SIDEBAR   │      TRACK LIST             │   PLAYER PANEL        │
│            │                             │                       │
│  Mi música │   [section controls]        │   [Album art]         │
│  Buscar    │                             │                       │
│  Descubrir │   TrackCard                 │   Title               │
│            │   TrackCard                 │   Artist              │
│            │   TrackCard                 │                       │
│            │   ...                       │   ━━━●━━━━━━━━        │
│            │                             │   ◀  ▶  ♥  ✕         │
│            │                             │                       │
└────────────┴─────────────────────────────┴───────────────────────┘
```

- **Sidebar:** navigation between the three sections.
- **Track list column:** content of the active section. Changes based on sidebar selection.
- **Player panel:** always visible on the right. Updates when a track is clicked. Contains album art, title, artist, progress bar, play/pause, like and dislike buttons.

### Sections

**Mi música:**
Flat list of tracks where `is_saved = true OR feedback = 'like'`. Shows Spotify-saved tracks and in-app liked tracks unified. Includes onboarding prompt if library is sparse.

**Buscar:**
Search input at the top. Results fetched from Spotify Search API on each query. No persistence until the user interacts (play, like, dislike). Results clear when the user navigates away.

**Descubrir:**
Controls at the top: tone selector (Segura · Mezcla · Novedad) and size input. Generate button triggers the recommendation pipeline. Results shown as a track list. Export button creates the playlist in Spotify.

### Key Interactions

| Action | Result |
|--------|--------|
| Click track | Plays in player panel immediately |
| Click ♥ (like) | Saves feedback, track appears in Mi música |
| Click ✕ (dislike) | Saves feedback, excluded from future recommendations |
| Click Generate | Spinner → track list populated with recommendations |
| Click Export | Playlist created in Spotify, URL returned |
| Click Refresh (header) | Triggers full reimport from Spotify |

### Playback

Powered by **Spotify Web Playback SDK** running entirely in the browser. The browser becomes a Spotify Connect device. The backend only provides a fresh access token — all playback control is client-side.

The frontend records every play event by calling `POST /player/event` when:
- A track finishes playing.
- The user switches to a different track (recording ms_played so far).

---

## 10. Recommendation Pipeline

### Overview

The pipeline runs every time the user generates a playlist. It has four sequential stages:

```
[Training Data] → [Two-Tower Training] → [Candidate Generation] → [Ranking] → [Playlist]
```

Training is decoupled from inference: the model is trained periodically in the background, and inference always uses the latest trained model.

### Training Data Construction

Training examples are built from all user signals in the database, weighted by confidence:

| Source | Label | Weight |
|--------|-------|--------|
| saved_tracks (Spotify) | 1.0 | 1.0 |
| app likes | 1.0 | 1.0 |
| top_tracks short term (pos 1-10) | 0.95 | 0.9 |
| top_tracks short term (pos 11-50) | 0.80 | 0.7 |
| top_tracks medium term | 0.70 | 0.6 |
| top_tracks long term | 0.55 | 0.5 |
| declared artist tracks (popular) | 0.90 | 0.8 |
| declared artist tracks (rest) | 0.60 | 0.6 |
| declared playlist tracks | 0.80 | 0.7 |
| app dislikes | 0.0 | 1.0 |
| skipped < 10% duration | 0.1 | 0.7 |
| unknown tracks (implicit negatives) | 0.1 | 0.3 |

### Two-Tower Architecture

Two independent MLPs that project user profile and track features into the same 32-dimensional embedding space. Score is the dot product (cosine similarity, as both are L2-normalized).

**UserTower** encodes the user's current taste state:
- Genre preference weights (N genres, each 0–1)
- Top artist affinity scores (top 20 artists, each 0–1)
- Global like/dislike ratio
- Listening diversity score

**ItemTower** encodes track properties:
- Genre multi-hot vector (N genres, 0/1)
- Normalized track popularity
- Normalized artist popularity
- Is-unknown-artist flag
- Release recency score

**Training objective:** InfoNCE contrastive loss. Positive pairs (user, liked track) should score high; negative pairs (user, disliked/random track) should score low. In-batch negatives are used as implicit hard negatives.

**Refinement:** Hard Negative Mining every N epochs. Negatives that score unexpectedly high are added back with increased weight. This forces the model to improve on its blind spots.

**Retraining triggers:**
- Every 20 new feedback events (automatic, background task).
- After each Spotify import or artist declaration (manual).
- User-initiated via `/model/train`.

### Candidate Generation

Before ranking, the system fetches unknown tracks from Spotify:

1. **Artist discographies:** top N artists by affinity → fetch all their albums and tracks via Spotify API → filter out known tracks.
2. **Genre search:** top 5 genres by weight → Spotify Search by genre → filter out known tracks.

Candidate tracks are upserted into the database and their item embeddings are computed with the ItemTower. Only tracks not in `user_track_data` (or with no interactions) are eligible as candidates.

### Ranking and Modes

The ranker scores all candidates using the trained model, then applies mode-specific adjustments:

| Signal | Segura | Mezcla | Novedad |
|--------|--------|--------|---------|
| Two-Tower score | high | medium | medium |
| Artist affinity | high | medium | low |
| Novelty (unknown artist) | penalized | neutral | boosted |
| Popularity | high preference | neutral | low preference |

After scoring, a diversifier ensures no more than 3 tracks per artist and prevents any single genre from exceeding 40% of the playlist.

---

## 11. Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Single user | Yes | Eliminates auth complexity, simplifies DB, fits the personal use case |
| Database | SQLite | Zero config, local-first, sufficient for one user's data volume |
| Playback | Spotify Web Playback SDK | Only option for full in-browser playback; requires Premium |
| Recommendation model | Two-Tower (PyTorch) | Production-grade architecture; educational; extensible to more data |
| Cold start | Explicit onboarding declarations | More reliable than algorithmic bootstrapping; user-verified data |
| Retraining | Background task, threshold-triggered | Non-blocking UX; model improves passively |
| Candidate source | Spotify Search + artist discographies | Avoids restricted endpoints; stays within Spotify TOS |
| Feedback | Binary like/dislike | Minimal friction; sufficient signal for the model |
| Import strategy | Async on first login + manual refresh | Data is static between refreshes; predictable behavior |
| Architecture | Modular monolith | Fast to develop, parallelizable by agents, extractable to services later |
| Playlist generation | Synchronous | Simpler implementation; acceptable latency for personal use |
