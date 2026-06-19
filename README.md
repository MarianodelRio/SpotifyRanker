# TasteRanker

A personal music discovery engine connected to Spotify. Reads your library, listening history, and playlists; builds a taste profile using a Two-Tower deep learning model; and generates personalized discovery playlists that Spotify doesn't offer natively.

Music plays directly in the browser via the Spotify Web Playback SDK.

## What makes it different

Fully transparent, user-controllable recommendation pipeline — candidate generation → Two-Tower ranking → playlist export — with no dependency on Spotify's restricted recommendation endpoints.

Single-user, local-first. No cloud deployment required.

## Stack

| Layer | Tech |
|-------|------|
| Backend | Python, FastAPI, SQLAlchemy, SQLite |
| ML | PyTorch (Two-Tower model) |
| Frontend | React, TypeScript, Vite |
| Music playback | Spotify Web Playback SDK |
| Auth | Spotify OAuth 2.0 (PKCE) |
| Dev environment | Docker, Docker Compose |

## Architecture

```
apps/
  api/          ← FastAPI HTTP entry point
  frontend/     ← React + Vite + TypeScript UI

libs/
  common/       ← Shared Pydantic models and enums
  spotify/      ← Spotify API adapter
  profile/      ← User taste profile builder
  candidates/   ← Candidate track generation
  ml/           ← Two-Tower feature engineering, training, inference
  ranker/       ← Scoring, mode configuration, diversification
  playlist/     ← Playlist assembly and Spotify export
  feedback/     ← Feedback persistence and retraining trigger

db/             ← ORM models, repositories, migrations
models_store/   ← Trained PyTorch model files
```

## Setup

### Prerequisites

- A Spotify Developer app ([create one here](https://developer.spotify.com/dashboard)) — set the redirect URI to `http://localhost:8000/auth/callback`
- Docker and Docker Compose (recommended), or Python 3.11+ and Node.js 18+

### With Docker (recommended)

```bash
# Copy and fill in your Spotify credentials
cp .env.example .env

# Start the full stack
docker compose up
```

API at `http://localhost:8000` — Frontend at `http://localhost:5173`.

### Without Docker

```bash
# Create a .env file with your Spotify credentials
SPOTIFY_CLIENT_ID=your_client_id
SPOTIFY_CLIENT_SECRET=your_client_secret
SPOTIFY_REDIRECT_URI=http://localhost:8000/auth/callback

# Backend
pip install -e ".[dev]"
python db/init_db.py
uvicorn apps.api.main:app --reload

# Frontend (separate terminal)
cd apps/frontend
npm install
npm run dev
```

The app will be available at `http://localhost:5173`.

## Development

```bash
# Tests
pytest
pytest --cov=libs --cov-report=term-missing

# Linting
ruff check .
ruff format .
mypy libs/ apps/api/

# Frontend
cd apps/frontend
npm run lint
npx tsc --noEmit
```

## Status

Currently in active development. See [`plan.md`](plan.md) for the full roadmap and [`tasks/`](tasks/) for task status.
