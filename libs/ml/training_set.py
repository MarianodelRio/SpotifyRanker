from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from db.models import Track, UserTrackData
from libs.common.enums import FeedbackType, SaveSource
from libs.common.models import UserProfile


@dataclass
class TrainingExample:
    track_id: str
    label: float
    weight: float
    # Populated by T-020 via T-017's build_user_features / build_track_features
    user_features: np.ndarray[Any, Any] = field(default_factory=lambda: np.zeros(0))
    track_features: np.ndarray[Any, Any] = field(default_factory=lambda: np.zeros(0))


async def build_training_set(session: AsyncSession, profile: UserProfile) -> list[TrainingExample]:
    """Build labeled training examples from all user signals in the database."""
    stmt = select(UserTrackData).options(
        joinedload(UserTrackData.track).joinedload(Track.play_events),
    )
    result = await session.scalars(stmt)
    rows: list[UserTrackData] = list(result.unique())

    examples: list[TrainingExample] = []
    for utd in rows:
        label, weight = _compute_label_weight(utd)
        examples.append(TrainingExample(track_id=utd.track_id, label=label, weight=weight))

    return examples


def _compute_label_weight(utd: UserTrackData) -> tuple[float, float]:
    """Return (label, weight) for a single user_track_data row.

    Applies the signal weight table from design.md §10.
    When multiple signals apply, returns the pair with the highest label.
    """
    signals: list[tuple[float, float]] = []  # (label, weight)

    # Saved from Spotify
    if utd.is_saved and utd.save_source == SaveSource.spotify:
        signals.append((1.0, 1.0))

    # App like
    if utd.feedback == FeedbackType.like:
        signals.append((1.0, 1.0))

    # App dislike
    if utd.feedback == FeedbackType.dislike:
        signals.append((0.0, 1.0))

    # Top tracks short term
    if utd.top_position_short is not None:
        if 1 <= utd.top_position_short <= 10:
            signals.append((0.95, 0.9))
        elif 11 <= utd.top_position_short <= 50:
            signals.append((0.80, 0.7))

    # Top tracks medium term
    if utd.top_position_medium is not None:
        signals.append((0.70, 0.6))

    # Top tracks long term
    if utd.top_position_long is not None:
        signals.append((0.55, 0.5))

    # Skip signal: any play event where ms_played < 10% of track duration
    track = utd.track
    if track and track.duration_ms and track.duration_ms > 0:
        for event in track.play_events:
            if event.ms_played / track.duration_ms < 0.1:
                signals.append((0.1, 0.7))
                break

    if not signals:
        return (0.1, 0.3)  # implicit negative — no recorded interaction

    return max(signals, key=lambda s: s[0])
