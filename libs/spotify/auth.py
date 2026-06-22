import base64
import hashlib
import secrets
from typing import Any
from urllib.parse import urlencode

import httpx

_SPOTIFY_AUTH_URL = "https://accounts.spotify.com/authorize"
_SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
_SPOTIFY_ME_URL = "https://api.spotify.com/v1/me"

_SCOPES = " ".join(
    [
        "user-library-read",
        "user-top-read",
        "user-read-playback-state",
        "user-read-private",
        "user-read-email",
        "user-modify-playback-state",
        "streaming",
        "playlist-modify-public",
        "playlist-modify-private",
    ]
)

# In-memory PKCE state storage: state → code_verifier.
# Single-user local app; the login window is seconds so memory is sufficient.
_pending_verifiers: dict[str, str] = {}


def generate_code_verifier() -> str:
    return secrets.token_urlsafe(64)


def generate_code_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode()


def build_authorization_url(client_id: str, redirect_uri: str) -> str:
    """Return Spotify authorization URL and store state→verifier for /callback."""
    state = secrets.token_urlsafe(16)
    verifier = generate_code_verifier()
    challenge = generate_code_challenge(verifier)
    _pending_verifiers[state] = verifier

    params = {
        "response_type": "code",
        "client_id": client_id,
        "scope": _SCOPES,
        "redirect_uri": redirect_uri,
        "state": state,
        "code_challenge_method": "S256",
        "code_challenge": challenge,
    }
    return f"{_SPOTIFY_AUTH_URL}?{urlencode(params)}"


def pop_code_verifier(state: str) -> str | None:
    return _pending_verifiers.pop(state, None)


async def exchange_code_for_tokens(
    code: str,
    state: str,
    client_id: str,
    redirect_uri: str,
) -> dict[str, Any]:
    """Exchange authorization code for access + refresh tokens."""
    verifier = pop_code_verifier(state)
    if verifier is None:
        raise ValueError("Unknown or expired OAuth state")

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            _SPOTIFY_TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "client_id": client_id,
                "code_verifier": verifier,
            },
        )
        resp.raise_for_status()
        data: dict[str, Any] = resp.json()
        return data


async def refresh_access_token(refresh_token: str, client_id: str) -> dict[str, Any]:
    """Request a new access token using the stored refresh token."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            _SPOTIFY_TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": client_id,
            },
        )
        resp.raise_for_status()
        data: dict[str, Any] = resp.json()
        return data


async def fetch_current_user(access_token: str) -> dict[str, Any]:
    """Fetch authenticated user's Spotify profile."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            _SPOTIFY_ME_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        resp.raise_for_status()
        data: dict[str, Any] = resp.json()
        return data
