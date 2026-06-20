from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from libs.common.models import Track, UserProfile

_TOP_ARTISTS = 20
# Scalar features appended after genre slots and artist slots:
# [global_like_ratio, diversity_score] for user
# [norm_track_popularity, norm_artist_popularity, is_unknown_artist, release_recency] for track
# Both vectors have length: len(vocab) + _TOP_ARTISTS + 2
# (track's 4 scalars vs user's 2 scalars means different tail — see build_* for layout)
# Actual fixed dim = len(vocab) + _TOP_ARTISTS + 4; user's last 2 slots are always 0.


def build_genre_vocab(genres: list[str]) -> list[str]:
    """Return sorted, deduplicated genre vocabulary."""
    return sorted(set(genres))


def save_vocab(vocab: list[str], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(vocab))


def load_vocab(path: Path) -> list[str]:
    result: list[str] = json.loads(path.read_text())
    return result


def _fixed_dim(vocab: list[str]) -> int:
    # genre slots + top-artist slots + 4 scalar slots
    return len(vocab) + _TOP_ARTISTS + 4


def build_user_features(
    profile: UserProfile, vocab: list[str]
) -> np.ndarray[tuple[int], np.dtype[np.float32]]:
    """
    Build a fixed-length float32 feature vector for a user.

    Layout:
      [0 .. len(vocab)-1]         genre preference weights from profile.genre_weights
      [len(vocab) .. +20-1]       top-20 artist affinity scores
      [len(vocab)+20]             global_like_ratio
      [len(vocab)+21]             diversity_score
      [len(vocab)+22 .. +23]      zeros (padding to match track vector length)
    """
    dim = _fixed_dim(vocab)
    vec = np.zeros(dim, dtype=np.float32)

    # Genre slots: look up each vocab genre in the profile's weights dict
    genre_index = {g: i for i, g in enumerate(vocab)}
    for genre, weight in profile.genre_weights.items():
        idx = genre_index.get(genre)
        if idx is not None:
            vec[idx] = float(np.clip(weight, 0.0, 1.0))

    # Top-20 artist affinity slots
    offset = len(vocab)
    top_artists = sorted(profile.artist_affinities.items(), key=lambda kv: kv[1], reverse=True)
    for rank, (_, affinity) in enumerate(top_artists[:_TOP_ARTISTS]):
        vec[offset + rank] = float(np.clip(affinity, 0.0, 1.0))

    # Scalar slots
    scalar_offset = offset + _TOP_ARTISTS
    vec[scalar_offset] = float(np.clip(profile.global_like_ratio, 0.0, 1.0))
    vec[scalar_offset + 1] = float(np.clip(profile.diversity_score, 0.0, 1.0))
    # slots [scalar_offset+2] and [scalar_offset+3] stay 0 (padding)

    return vec


def build_track_features(
    track: Track,
    genres: list[str],
    artist_popularity: int,
    vocab: list[str],
) -> np.ndarray[tuple[int], np.dtype[np.float32]]:
    """
    Build a fixed-length float32 feature vector for a track.

    Layout:
      [0 .. len(vocab)-1]         genre multi-hot (1.0 if genre in vocab, else 0)
      [len(vocab) .. +20-1]       zeros (padding to match user artist-affinity slots)
      [len(vocab)+20]             normalized track popularity  (track.popularity / 100)
      [len(vocab)+21]             normalized artist popularity (artist_popularity / 100)
      [len(vocab)+22]             is_unknown_artist flag (1.0 if artist_popularity == 0)
      [len(vocab)+23]             release_recency score (0.0 — Track has no release_date field)
    """
    dim = _fixed_dim(vocab)
    vec = np.zeros(dim, dtype=np.float32)

    # Genre multi-hot
    genre_index = {g: i for i, g in enumerate(vocab)}
    for genre in genres:
        idx = genre_index.get(genre)
        if idx is not None:
            vec[idx] = 1.0

    # Artist-affinity padding slots stay 0

    scalar_offset = len(vocab) + _TOP_ARTISTS
    vec[scalar_offset] = float(np.clip(track.popularity / 100.0, 0.0, 1.0))
    vec[scalar_offset + 1] = float(np.clip(artist_popularity / 100.0, 0.0, 1.0))
    vec[scalar_offset + 2] = 1.0 if artist_popularity == 0 else 0.0
    # release_recency stays 0.0 (Track has no release_date field)

    return vec
