"""Tests for build_training_set — signal labeling and weighting logic."""

import numpy as np
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from db.models import Base, PlayEvent, Track, UserTrackData
from libs.common.enums import FeedbackType, PlaySource, SaveSource
from libs.common.models import UserProfile
from libs.ml.training_set import TrainingExample, build_training_set


@pytest.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as s:
        yield s
    await engine.dispose()


def _empty_profile() -> UserProfile:
    return UserProfile()


async def _add_track(session: AsyncSession, track_id: str, duration_ms: int = 200_000) -> str:
    track = Track(
        id=track_id,
        spotify_id=f"sp_{track_id}",
        title=f"Track {track_id}",
        duration_ms=duration_ms,
        popularity=50,
    )
    session.add(track)
    await session.flush()
    return track_id


async def _add_utd(session: AsyncSession, track_id: str, **kwargs) -> UserTrackData:
    utd = UserTrackData(track_id=track_id, **kwargs)
    session.add(utd)
    await session.flush()
    return utd


# ── Count guarantee ────────────────────────────────────────────────────────────


async def test_200_tracks_produce_200_examples(session):
    for i in range(200):
        tid = f"t{i:04d}"
        await _add_track(session, tid)
        await _add_utd(session, tid, is_saved=True, save_source=SaveSource.spotify)
    await session.commit()

    examples = await build_training_set(session, _empty_profile())
    assert len(examples) >= 200


# ── Label / weight table ───────────────────────────────────────────────────────


async def test_saved_spotify_label(session):
    await _add_track(session, "t1")
    await _add_utd(session, "t1", is_saved=True, save_source=SaveSource.spotify)
    await session.commit()

    examples = await build_training_set(session, _empty_profile())
    ex = examples[0]
    assert ex.label == 1.0
    assert ex.weight == 1.0


async def test_app_like_label(session):
    await _add_track(session, "t1")
    await _add_utd(
        session, "t1", is_saved=True, save_source=SaveSource.app, feedback=FeedbackType.like
    )
    await session.commit()

    examples = await build_training_set(session, _empty_profile())
    assert examples[0].label == 1.0
    assert examples[0].weight == 1.0


async def test_app_dislike_label(session):
    await _add_track(session, "t1")
    await _add_utd(session, "t1", feedback=FeedbackType.dislike)
    await session.commit()

    examples = await build_training_set(session, _empty_profile())
    assert examples[0].label == 0.0
    assert examples[0].weight == 1.0


async def test_top_short_1_to_10_label(session):
    await _add_track(session, "t1")
    await _add_utd(session, "t1", top_position_short=5)
    await session.commit()

    examples = await build_training_set(session, _empty_profile())
    assert examples[0].label == 0.95
    assert examples[0].weight == 0.9


async def test_top_short_11_to_50_label(session):
    await _add_track(session, "t1")
    await _add_utd(session, "t1", top_position_short=30)
    await session.commit()

    examples = await build_training_set(session, _empty_profile())
    assert examples[0].label == 0.80
    assert examples[0].weight == 0.7


async def test_top_medium_term_label(session):
    await _add_track(session, "t1")
    await _add_utd(session, "t1", top_position_medium=20)
    await session.commit()

    examples = await build_training_set(session, _empty_profile())
    assert examples[0].label == 0.70
    assert examples[0].weight == 0.6


async def test_top_long_term_label(session):
    await _add_track(session, "t1")
    await _add_utd(session, "t1", top_position_long=40)
    await session.commit()

    examples = await build_training_set(session, _empty_profile())
    assert examples[0].label == 0.55
    assert examples[0].weight == 0.5


async def test_implicit_negative_label(session):
    """A track with no interactions gets implicit-negative label."""
    await _add_track(session, "t1")
    await _add_utd(session, "t1")
    await session.commit()

    examples = await build_training_set(session, _empty_profile())
    assert examples[0].label == 0.1
    assert examples[0].weight == 0.3


async def test_skip_signal_label(session):
    """A track where all plays are < 10% duration gets the skip label."""
    await _add_track(session, "t1", duration_ms=200_000)
    await _add_utd(session, "t1")
    event = PlayEvent(
        track_id="t1",
        ms_played=5_000,  # 2.5% of 200_000 — well below 10%
        source=PlaySource.my_music,
    )
    session.add(event)
    await session.commit()

    examples = await build_training_set(session, _empty_profile())
    assert examples[0].label == 0.1
    assert examples[0].weight == 0.7


# ── No double-counting: max label wins ────────────────────────────────────────


async def test_save_and_top_short_returns_max_label(session):
    """A track with both a Spotify save (1.0) and top-short pos 5 (0.95) → label=1.0."""
    await _add_track(session, "t1")
    await _add_utd(
        session,
        "t1",
        is_saved=True,
        save_source=SaveSource.spotify,
        top_position_short=5,
    )
    await session.commit()

    examples = await build_training_set(session, _empty_profile())
    assert examples[0].label == 1.0
    assert examples[0].weight == 1.0


async def test_top_medium_and_top_long_returns_max_label(session):
    """top_medium (0.70) beats top_long (0.55) → label=0.70."""
    await _add_track(session, "t1")
    await _add_utd(session, "t1", top_position_medium=10, top_position_long=40)
    await session.commit()

    examples = await build_training_set(session, _empty_profile())
    assert examples[0].label == 0.70
    assert examples[0].weight == 0.6


async def test_dislike_does_not_override_save(session):
    """A disliked-but-also-saved track: max label = 1.0 (save wins over dislike=0.0)."""
    await _add_track(session, "t1")
    await _add_utd(
        session,
        "t1",
        is_saved=True,
        save_source=SaveSource.spotify,
        feedback=FeedbackType.dislike,
    )
    await session.commit()

    examples = await build_training_set(session, _empty_profile())
    assert examples[0].label == 1.0


# ── TrainingExample structure ─────────────────────────────────────────────────


async def test_training_example_has_numpy_feature_arrays(session):
    await _add_track(session, "t1")
    await _add_utd(session, "t1", is_saved=True, save_source=SaveSource.spotify)
    await session.commit()

    examples = await build_training_set(session, _empty_profile())
    ex = examples[0]
    assert isinstance(ex, TrainingExample)
    assert isinstance(ex.user_features, np.ndarray)
    assert isinstance(ex.track_features, np.ndarray)
    assert ex.track_id == "t1"
