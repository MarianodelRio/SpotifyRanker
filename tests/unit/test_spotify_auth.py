"""Unit tests for libs/spotify/auth.py — PKCE utilities and token functions."""

import base64
import hashlib
from unittest.mock import AsyncMock, MagicMock, patch
from urllib.parse import parse_qs, urlparse

import pytest

from libs.spotify.auth import (
    build_authorization_url,
    exchange_code_for_tokens,
    fetch_current_user,
    generate_code_challenge,
    generate_code_verifier,
    pop_code_verifier,
    refresh_access_token,
)

# ── PKCE helpers ─────────────────────────────────────────────────────────────


def test_generate_code_verifier_length():
    v = generate_code_verifier()
    assert 43 <= len(v) <= 128


def test_generate_code_verifier_is_url_safe():
    v = generate_code_verifier()
    allowed = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_")
    assert set(v) <= allowed


def test_generate_code_verifier_is_random():
    assert generate_code_verifier() != generate_code_verifier()


def test_generate_code_challenge_is_s256():
    verifier = "test_verifier_value_that_is_long_enough_to_be_valid"
    challenge = generate_code_challenge(verifier)
    expected = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    )
    assert challenge == expected


def test_generate_code_challenge_no_padding():
    verifier = generate_code_verifier()
    challenge = generate_code_challenge(verifier)
    assert "=" not in challenge


# ── build_authorization_url ───────────────────────────────────────────────────


def test_build_authorization_url_returns_spotify_host():
    url = build_authorization_url("client123", "http://localhost:8000/auth/callback")
    assert "accounts.spotify.com" in url


def test_build_authorization_url_includes_required_params():
    url = build_authorization_url("client123", "http://localhost:8000/auth/callback")
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    assert params["response_type"] == ["code"]
    assert params["client_id"] == ["client123"]
    assert params["code_challenge_method"] == ["S256"]
    assert "state" in params
    assert "code_challenge" in params


def test_build_authorization_url_includes_all_scopes():
    url = build_authorization_url("client123", "http://localhost:8000/auth/callback")
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    scope = params["scope"][0]
    for expected_scope in [
        "user-library-read",
        "user-top-read",
        "user-read-playback-state",
        "streaming",
        "playlist-modify-public",
        "playlist-modify-private",
    ]:
        assert expected_scope in scope


def test_build_authorization_url_stores_verifier():
    url = build_authorization_url("client123", "http://localhost:8000/auth/callback")
    parsed = urlparse(url)
    state = parse_qs(parsed.query)["state"][0]
    verifier = pop_code_verifier(state)
    assert verifier is not None
    assert len(verifier) >= 43


def test_pop_code_verifier_returns_none_for_unknown_state():
    assert pop_code_verifier("nonexistent-state-xyz") is None


def test_pop_code_verifier_removes_entry():
    url = build_authorization_url("client123", "http://localhost:8000/auth/callback")
    state = parse_qs(urlparse(url).query)["state"][0]
    pop_code_verifier(state)
    assert pop_code_verifier(state) is None


# ── exchange_code_for_tokens ──────────────────────────────────────────────────


async def test_exchange_code_for_tokens_success():
    url = build_authorization_url("client_id", "http://localhost:8000/auth/callback")
    state = parse_qs(urlparse(url).query)["state"][0]

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "access_token": "acc_tok",
        "refresh_token": "ref_tok",
        "expires_in": 3600,
        "token_type": "Bearer",
    }
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=mock_response)

    with patch("libs.spotify.auth.httpx.AsyncClient", return_value=mock_client):
        result = await exchange_code_for_tokens(
            "auth_code", state, "client_id", "http://localhost:8000/auth/callback"
        )

    assert result["access_token"] == "acc_tok"
    assert result["refresh_token"] == "ref_tok"


async def test_exchange_code_for_tokens_unknown_state():
    with pytest.raises(ValueError, match="Unknown or expired OAuth state"):
        await exchange_code_for_tokens("code", "bad_state", "client", "http://localhost")


# ── refresh_access_token ──────────────────────────────────────────────────────


async def test_refresh_access_token_success():
    mock_response = MagicMock()
    mock_response.json.return_value = {"access_token": "new_acc", "expires_in": 3600}
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=mock_response)

    with patch("libs.spotify.auth.httpx.AsyncClient", return_value=mock_client):
        result = await refresh_access_token("ref_tok", "client_id")

    assert result["access_token"] == "new_acc"


# ── fetch_current_user ────────────────────────────────────────────────────────


async def test_fetch_current_user_success():
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": "user123", "display_name": "Test User"}
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(return_value=mock_response)

    with patch("libs.spotify.auth.httpx.AsyncClient", return_value=mock_client):
        result = await fetch_current_user("access_token_value")

    assert result["id"] == "user123"
    assert result["display_name"] == "Test User"
