"""Migration: add artist_name, album_title, image_url to tracks table (T-035)."""

import asyncio

from sqlalchemy import text

from db.engine import engine


async def migrate() -> None:
    async with engine.begin() as conn:
        for stmt in (
            "ALTER TABLE tracks ADD COLUMN artist_name TEXT",
            "ALTER TABLE tracks ADD COLUMN album_title TEXT",
            "ALTER TABLE tracks ADD COLUMN image_url TEXT",
        ):
            try:
                await conn.execute(text(stmt))
                print(f"OK: {stmt}")
            except Exception as e:
                if "duplicate column name" in str(e).lower():
                    print(f"SKIP (already exists): {stmt}")
                else:
                    raise


if __name__ == "__main__":
    asyncio.run(migrate())
