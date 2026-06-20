from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Genre


class GenreRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_or_create(self, name: str) -> Genre:
        result = await self._session.execute(select(Genre).where(Genre.name == name))
        existing = result.scalar_one_or_none()
        if existing is not None:
            return existing

        stmt = insert(Genre).values(name=name).on_conflict_do_nothing(index_elements=["name"])
        await self._session.execute(stmt)
        await self._session.commit()

        result = await self._session.execute(select(Genre).where(Genre.name == name))
        row = result.scalar_one()
        return row

    async def get_all(self) -> list[Genre]:
        result = await self._session.execute(select(Genre).order_by(Genre.name))
        return list(result.scalars().all())
