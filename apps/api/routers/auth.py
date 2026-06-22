import logging
from datetime import datetime, timedelta
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query  # noqa: F401
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.config import Settings, get_settings
from db.models import Auth
from db.session import get_db
from libs.common.enums import ImportStatus
from libs.spotify.auth import (
    build_authorization_url,
    exchange_code_for_tokens,
    fetch_current_user,
    refresh_access_token,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

_FRONTEND_URL = "http://localhost:5173"


async def _get_auth_row(db: AsyncSession) -> Auth | None:
    result = await db.execute(select(Auth))
    return result.scalars().first()


@router.get("/login")
async def login(settings: Settings = Depends(get_settings)) -> RedirectResponse:  # noqa: B008
    url = build_authorization_url(settings.SPOTIFY_CLIENT_ID, settings.SPOTIFY_REDIRECT_URI)
    return RedirectResponse(url)


@router.get("/callback")
async def callback(
    code: str = Query(...),  # noqa: B008
    state: str = Query(...),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
    settings: Settings = Depends(get_settings),  # noqa: B008
) -> RedirectResponse:
    try:
        token_data = await exchange_code_for_tokens(
            code, state, settings.SPOTIFY_CLIENT_ID, settings.SPOTIFY_REDIRECT_URI
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("Token exchange failed: %s", exc)
        raise HTTPException(
            status_code=502, detail="Failed to exchange authorization code"
        ) from exc

    access_token: str = token_data["access_token"]
    refresh_token: str | None = token_data.get("refresh_token")
    expires_in: int = token_data.get("expires_in", 3600)
    token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

    try:
        user_data = await fetch_current_user(access_token)
    except Exception as exc:
        body = exc.response.text if isinstance(exc, httpx.HTTPStatusError) else ""
        logger.error("fetch_current_user failed: %s | body: %s", exc, body)
        raise HTTPException(
            status_code=502, detail="Failed to fetch user profile from Spotify"
        ) from exc

    spotify_user_id: str = user_data["id"]
    display_name: str | None = user_data.get("display_name")

    existing = await db.get(Auth, spotify_user_id)
    if existing is None:
        db.add(
            Auth(
                spotify_user_id=spotify_user_id,
                display_name=display_name,
                access_token=access_token,
                refresh_token=refresh_token,
                token_expires_at=token_expires_at,
                import_status=ImportStatus.idle,
            )
        )
    else:
        existing.display_name = display_name
        existing.access_token = access_token
        if refresh_token:
            existing.refresh_token = refresh_token
        existing.token_expires_at = token_expires_at

    await db.commit()
    return RedirectResponse(_FRONTEND_URL)


@router.get("/status")
async def status(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:  # noqa: B008
    auth = await _get_auth_row(db)
    if auth is None or auth.access_token is None:
        return {"is_authenticated": False, "display_name": None}
    return {"is_authenticated": True, "display_name": auth.display_name}


@router.post("/logout")
async def logout(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:  # noqa: B008
    auth = await _get_auth_row(db)
    if auth is not None:
        auth.access_token = None
        auth.refresh_token = None
        auth.display_name = None
        auth.token_expires_at = None
        await db.commit()
    return {"detail": "Logged out"}


@router.get("/token")
async def token(
    db: AsyncSession = Depends(get_db),  # noqa: B008
    settings: Settings = Depends(get_settings),  # noqa: B008
) -> dict[str, Any]:
    auth = await _get_auth_row(db)
    if auth is None or auth.access_token is None:
        raise HTTPException(status_code=401, detail="Not authenticated")

    now = datetime.utcnow()
    needs_refresh = auth.token_expires_at is None or auth.token_expires_at <= now + timedelta(
        seconds=60
    )

    if needs_refresh:
        if auth.refresh_token is None:
            auth.access_token = None
            await db.commit()
            raise HTTPException(status_code=401, detail="Session expired — please log in again")
        try:
            token_data = await refresh_access_token(auth.refresh_token, settings.SPOTIFY_CLIENT_ID)
        except Exception as exc:
            auth.access_token = None
            auth.refresh_token = None
            await db.commit()
            raise HTTPException(
                status_code=401, detail="Token refresh failed — please log in again"
            ) from exc

        auth.access_token = token_data["access_token"]
        if "refresh_token" in token_data:
            auth.refresh_token = token_data["refresh_token"]
        expires_in = token_data.get("expires_in", 3600)
        auth.token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
        await db.commit()

    return {"access_token": auth.access_token}
