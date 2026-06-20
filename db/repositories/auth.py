from datetime import datetime

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Auth
from libs.common.enums import ImportStatus


class AuthRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_auth(self) -> Auth | None:
        result = await self._session.execute(select(Auth).limit(1))
        return result.scalar_one_or_none()

    async def upsert_auth(
        self,
        *,
        spotify_user_id: str,
        display_name: str | None = None,
        access_token: str | None = None,
        refresh_token: str | None = None,
        token_expires_at: datetime | None = None,
    ) -> Auth:
        stmt = (
            insert(Auth)
            .values(
                spotify_user_id=spotify_user_id,
                display_name=display_name,
                access_token=access_token,
                refresh_token=refresh_token,
                token_expires_at=token_expires_at,
                import_status=ImportStatus.idle,
            )
            .on_conflict_do_update(
                index_elements=["spotify_user_id"],
                set_={
                    "display_name": display_name,
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "token_expires_at": token_expires_at,
                },
            )
        )
        await self._session.execute(stmt)
        await self._session.commit()
        row = await self.get_auth()
        assert row is not None
        return row

    async def update_import_status(
        self,
        spotify_user_id: str,
        status: ImportStatus,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
    ) -> None:
        result = await self._session.execute(
            select(Auth).where(Auth.spotify_user_id == spotify_user_id)
        )
        row = result.scalar_one_or_none()
        if row is None:
            return
        row.import_status = status
        if started_at is not None:
            row.import_started_at = started_at
        if completed_at is not None:
            row.import_completed_at = completed_at
        await self._session.commit()

    async def update_token(
        self,
        spotify_user_id: str,
        *,
        access_token: str,
        refresh_token: str,
        token_expires_at: datetime,
    ) -> None:
        result = await self._session.execute(
            select(Auth).where(Auth.spotify_user_id == spotify_user_id)
        )
        row = result.scalar_one_or_none()
        if row is None:
            return
        row.access_token = access_token
        row.refresh_token = refresh_token
        row.token_expires_at = token_expires_at
        await self._session.commit()
