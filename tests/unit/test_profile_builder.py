"""Unit tests for libs/profile/builder.py using in-memory SQLite."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from db.models import (
    Artist,
    ArtistGenre,
    Base,
    Genre,
    Track,
    TrackArtist,
    UserTrackData,
)
from libs.profile.builder import build_profile

# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as s:
        yield s
    await engine.dispose()


async def _add_track(
    session: AsyncSession,
    *,
    spotify_id: str,
    title: str = "Track",
    artist_spotify_id: str | None = None,
    artist_name: str = "Artist",
    genres: list[str] | None = None,
) -> tuple[str, str | None]:
    """Insert a Track (and optionally an Artist + Genres). Returns (track_id, artist_id)."""
    track = Track(spotify_id=spotify_id, title=title)
    session.add(track)
    await session.flush()

    artist_id: str | None = None
    if artist_spotify_id is not None:
        # Reuse existing artist if already in DB.
        from sqlalchemy import select

        row = (
            await session.execute(select(Artist).where(Artist.spotify_id == artist_spotify_id))
        ).scalar_one_or_none()
        if row is None:
            row = Artist(spotify_id=artist_spotify_id, name=artist_name, popularity=50)
            session.add(row)
            await session.flush()
            for g_name in genres or []:
                genre_row = (
                    await session.execute(select(Genre).where(Genre.name == g_name))
                ).scalar_one_or_none()
                if genre_row is None:
                    genre_row = Genre(name=g_name)
                    session.add(genre_row)
                    await session.flush()
                session.add(ArtistGenre(artist_id=row.id, genre_id=genre_row.id))
                await session.flush()
        artist_id = row.id
        session.add(TrackArtist(track_id=track.id, artist_id=artist_id, is_primary=True))
        await session.flush()

    await session.commit()
    return track.id, artist_id


async def _add_utd(
    session: AsyncSession,
    track_id: str,
    *,
    is_saved: bool = False,
    feedback: str | None = None,
    top_position_short: int | None = None,
    top_position_medium: int | None = None,
    top_position_long: int | None = None,
) -> None:
    session.add(
        UserTrackData(
            track_id=track_id,
            is_saved=is_saved,
            feedback=feedback,
            top_position_short=top_position_short,
            top_position_medium=top_position_medium,
            top_position_long=top_position_long,
        )
    )
    await session.commit()


# ── Tests ─────────────────────────────────────────────────────────────────────


async def test_empty_db_returns_valid_defaults(session):
    profile = await build_profile(session)

    assert profile.genre_weights == {}
    assert profile.artist_affinities == {}
    assert profile.known_track_ids == set()
    assert profile.global_like_ratio == 0.0
    assert profile.diversity_score == 0.0


async def test_genre_weights_sum_to_one(session):
    t1, _ = await _add_track(
        session, spotify_id="sp1", artist_spotify_id="a1", genres=["rock", "indie"]
    )
    t2, _ = await _add_track(session, spotify_id="sp2", artist_spotify_id="a2", genres=["pop"])
    await _add_utd(session, t1, is_saved=True)
    await _add_utd(session, t2, is_saved=True)

    profile = await build_profile(session)

    assert profile.genre_weights, "Expected non-empty genre weights"
    total = sum(profile.genre_weights.values())
    assert abs(total - 1.0) < 1e-9


async def test_known_track_ids_covers_all_signal_types(session):
    t_saved, _ = await _add_track(session, spotify_id="saved")
    t_liked, _ = await _add_track(session, spotify_id="liked")
    t_disliked, _ = await _add_track(session, spotify_id="disliked")
    t_top, _ = await _add_track(session, spotify_id="top")

    await _add_utd(session, t_saved, is_saved=True)
    await _add_utd(session, t_liked, feedback="like")
    await _add_utd(session, t_disliked, feedback="dislike")
    await _add_utd(session, t_top, top_position_short=5)

    profile = await build_profile(session)

    assert "saved" in profile.known_track_ids
    assert "liked" in profile.known_track_ids
    assert "disliked" in profile.known_track_ids
    assert "top" in profile.known_track_ids


async def test_global_like_ratio_correct(session):
    t1, _ = await _add_track(session, spotify_id="l1")
    t2, _ = await _add_track(session, spotify_id="l2")
    t3, _ = await _add_track(session, spotify_id="d1")

    await _add_utd(session, t1, feedback="like")
    await _add_utd(session, t2, feedback="like")
    await _add_utd(session, t3, feedback="dislike")

    profile = await build_profile(session)

    assert abs(profile.global_like_ratio - 2 / 3) < 1e-9


async def test_no_feedback_like_ratio_is_zero(session):
    t, _ = await _add_track(session, spotify_id="s1")
    await _add_utd(session, t, is_saved=True)

    profile = await build_profile(session)

    assert profile.global_like_ratio == 0.0


async def test_short_term_top_outweighs_long_term(session):
    """A genre appearing only in short-term top tracks should weigh more than one
    appearing only in long-term top tracks."""
    t_short, _ = await _add_track(
        session, spotify_id="short", artist_spotify_id="a_short", genres=["jazz"]
    )
    t_long, _ = await _add_track(
        session, spotify_id="long", artist_spotify_id="a_long", genres=["classical"]
    )
    await _add_utd(session, t_short, top_position_short=5)  # weight 0.9
    await _add_utd(session, t_long, top_position_long=1)  # weight 0.5

    profile = await build_profile(session)

    assert profile.genre_weights["jazz"] > profile.genre_weights["classical"]


async def test_dislike_excluded_from_positive_signals(session):
    """A disliked track should appear in known_track_ids but not contribute
    genre or artist weights."""
    t, _ = await _add_track(session, spotify_id="dis", artist_spotify_id="a_dis", genres=["metal"])
    await _add_utd(session, t, feedback="dislike")

    profile = await build_profile(session)

    assert "dis" in profile.known_track_ids
    assert "metal" not in profile.genre_weights
    assert "a_dis" not in profile.artist_affinities


async def test_artist_affinities_bounded_zero_to_one(session):
    t1, _ = await _add_track(session, spotify_id="x1", artist_spotify_id="art1", genres=["pop"])
    t2, _ = await _add_track(session, spotify_id="x2", artist_spotify_id="art2", genres=["pop"])
    await _add_utd(session, t1, is_saved=True)
    await _add_utd(session, t2, top_position_long=10)

    profile = await build_profile(session)

    for score in profile.artist_affinities.values():
        assert 0.0 <= score <= 1.0


async def test_deterministic_same_db_same_result(session):
    t, _ = await _add_track(session, spotify_id="det", artist_spotify_id="a_det", genres=["soul"])
    await _add_utd(session, t, is_saved=True, feedback="like")

    p1 = await build_profile(session)
    p2 = await build_profile(session)

    assert p1.genre_weights == p2.genre_weights
    assert p1.artist_affinities == p2.artist_affinities
    assert p1.known_track_ids == p2.known_track_ids
    assert p1.global_like_ratio == p2.global_like_ratio
    assert p1.diversity_score == p2.diversity_score


async def test_diversity_score_bounded_zero_to_one(session):
    for i in range(15):
        t, _ = await _add_track(
            session,
            spotify_id=f"d{i}",
            artist_spotify_id=f"a{i}",
            genres=[f"genre_{i}"],
        )
        await _add_utd(session, t, is_saved=True)

    profile = await build_profile(session)

    assert 0.0 <= profile.diversity_score <= 1.0


async def test_track_without_artist_still_in_known_ids(session):
    t = Track(spotify_id="no_artist", title="Orphan Track")
    session.add(t)
    await session.flush()
    await _add_utd(session, t.id, is_saved=True)

    profile = await build_profile(session)

    assert "no_artist" in profile.known_track_ids
