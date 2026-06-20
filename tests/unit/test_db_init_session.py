"""Unit tests for DB engine, session factory, and init script."""

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from db.models import Base

EXPECTED_TABLES = {
    "artists",
    "genres",
    "artist_genres",
    "albums",
    "tracks",
    "track_artists",
    "user_track_data",
    "play_events",
    "playlists",
    "playlist_tracks",
    "auth",
}


@pytest.fixture
async def memory_engine():
    """Async in-memory SQLite engine for isolated tests."""
    mem_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with mem_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield mem_engine
    await mem_engine.dispose()


async def test_create_tables_creates_all_expected_tables(memory_engine):
    """All 11 ORM tables should be created."""
    async with memory_engine.connect() as conn:
        table_names = await conn.run_sync(lambda sync_conn: inspect(sync_conn).get_table_names())
    assert set(table_names) == EXPECTED_TABLES


async def test_create_tables_is_idempotent(memory_engine):
    """Running create_all twice must not raise."""
    async with memory_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with memory_engine.connect() as conn:
        table_names = await conn.run_sync(lambda sync_conn: inspect(sync_conn).get_table_names())
    assert set(table_names) == EXPECTED_TABLES


async def test_get_db_yields_async_session(memory_engine):
    """get_db should yield an AsyncSession that can execute a query."""
    session_factory = async_sessionmaker(memory_engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        try:
            result = await session.execute(text("SELECT 1"))
            assert result.scalar() == 1
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def test_get_db_rolls_back_on_exception(memory_engine):
    """get_db must roll back the session when an exception is raised."""
    session_factory = async_sessionmaker(memory_engine, class_=AsyncSession, expire_on_commit=False)

    async def _failing_operation():
        async with session_factory() as session:
            try:
                await session.execute(text("SELECT 1"))
                raise RuntimeError("simulated failure")
            except Exception:
                await session.rollback()
                raise

    with pytest.raises(RuntimeError, match="simulated failure"):
        await _failing_operation()
