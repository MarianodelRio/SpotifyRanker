from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import UserTrackData


class UserTrackDataRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert(
        self,
        *,
        track_id: str,
        is_saved: bool | None = None,
        save_source: str | None = None,
        saved_at: datetime | None = None,
        feedback: str | None = None,
        feedback_at: datetime | None = None,
        top_position_short: int | None = None,
        top_position_medium: int | None = None,
        top_position_long: int | None = None,
    ) -> None:
        values: dict[str, Any] = {"track_id": track_id}
        set_: dict[str, Any] = {}

        if is_saved is not None:
            values["is_saved"] = is_saved
            set_["is_saved"] = is_saved
        if save_source is not None:
            values["save_source"] = save_source
            set_["save_source"] = save_source
        if saved_at is not None:
            values["saved_at"] = saved_at
            set_["saved_at"] = saved_at
        if feedback is not None:
            values["feedback"] = feedback
            set_["feedback"] = feedback
        if feedback_at is not None:
            values["feedback_at"] = feedback_at
            set_["feedback_at"] = feedback_at
        if top_position_short is not None:
            values["top_position_short"] = top_position_short
            set_["top_position_short"] = top_position_short
        if top_position_medium is not None:
            values["top_position_medium"] = top_position_medium
            set_["top_position_medium"] = top_position_medium
        if top_position_long is not None:
            values["top_position_long"] = top_position_long
            set_["top_position_long"] = top_position_long

        stmt = insert(UserTrackData).values(**values)
        if set_:
            stmt = stmt.on_conflict_do_update(index_elements=["track_id"], set_=set_)
        else:
            stmt = stmt.on_conflict_do_nothing(index_elements=["track_id"])

        await self._session.execute(stmt)
        await self._session.commit()

    async def get_saved_tracks(self) -> list[UserTrackData]:
        result = await self._session.execute(
            select(UserTrackData).where(UserTrackData.is_saved.is_(True))
        )
        return list(result.scalars().all())

    async def get_liked_tracks(self) -> list[UserTrackData]:
        result = await self._session.execute(
            select(UserTrackData).where(UserTrackData.feedback == "like")
        )
        return list(result.scalars().all())

    async def get_all_known_ids(self) -> list[str]:
        result = await self._session.execute(select(UserTrackData.track_id))
        return list(result.scalars().all())
