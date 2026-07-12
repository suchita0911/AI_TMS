"""Minimal OpenID Connect (authorization-code) client for Microsoft Entra ID.

Stateless by design: the CSRF ``state`` and the ``nonce`` are packed into a
short-lived JWT (signed with the app secret) that is passed as the OAuth
``state`` parameter, so no server-side session store or extra middleware is
needed. When SSO is not configured every entry point reports "disabled" and the
password-login flow is completely unaffected.
"""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlencode

import httpx
from jose import JWTError, jwt

from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)

_TIMEOUT = 10.0
_SCOPE = "openid profile email"
_STATE_TYPE = "sso_state"

# Discovery document + signing keys are fetched once and cached in-process.
_discovery_cache: dict[str, Any] = {}
_jwks_cache: dict[str, Any] = {}


class SSOError(Exception):
    """Any failure in the SSO exchange — surfaced to the user as a login error."""


def is_enabled() -> bool:
    return settings.sso_configured


def _authority() -> str:
    return f"https://login.microsoftonline.com/{settings.SSO_TENANT_ID}/v2.0"


def _discovery() -> dict:
    if not _discovery_cache:
        url = f"{_authority()}/.well-known/openid-configuration"
        try:
            resp = httpx.get(url, timeout=_TIMEOUT)
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise SSOError(f"Could not load the identity provider configuration: {exc}") from exc
        _discovery_cache.update(resp.json())
    return _discovery_cache


def _jwks() -> dict:
    if not _jwks_cache:
        try:
            resp = httpx.get(_discovery()["jwks_uri"], timeout=_TIMEOUT)
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise SSOError(f"Could not load the identity provider signing keys: {exc}") from exc
        _jwks_cache.update(resp.json())
    return _jwks_cache


# --------------------------------------------------------------------------- #
# Stateless state/nonce
# --------------------------------------------------------------------------- #
def _new_state() -> tuple[str, str]:
    """Return (state_jwt, nonce). The nonce is embedded in the signed state."""
    nonce = secrets.token_urlsafe(16)
    state = jwt.encode(
        {
            "nonce": nonce,
            "type": _STATE_TYPE,
            "exp": datetime.now(timezone.utc) + timedelta(minutes=10),
        },
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    return state, nonce


def read_state(state: str) -> str:
    """Validate the returned state JWT and recover the nonce."""
    try:
        payload = jwt.decode(state, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError as exc:
        raise SSOError("Login session expired or is invalid — please try again.") from exc
    if payload.get("type") != _STATE_TYPE:
        raise SSOError("Invalid login state.")
    return payload["nonce"]


# --------------------------------------------------------------------------- #
# Flow
# --------------------------------------------------------------------------- #
def authorization_url() -> str:
    state, nonce = _new_state()
    params = {
        "client_id": settings.SSO_CLIENT_ID,
        "response_type": "code",
        "redirect_uri": settings.SSO_REDIRECT_URI,
        "response_mode": "query",
        "scope": _SCOPE,
        "state": state,
        "nonce": nonce,
    }
    return f"{_discovery()['authorization_endpoint']}?{urlencode(params)}"


def exchange_code(code: str) -> dict:
    data = {
        "client_id": settings.SSO_CLIENT_ID,
        "client_secret": settings.SSO_CLIENT_SECRET,
        "code": code,
        "redirect_uri": settings.SSO_REDIRECT_URI,
        "grant_type": "authorization_code",
        "scope": _SCOPE,
    }
    try:
        resp = httpx.post(_discovery()["token_endpoint"], data=data, timeout=_TIMEOUT)
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        detail = ""
        if isinstance(exc, httpx.HTTPStatusError):
            detail = f" ({exc.response.text[:200]})"
        raise SSOError(f"Could not complete sign-in with the identity provider.{detail}") from exc
    return resp.json()


def validate_id_token(id_token: str, nonce: str) -> dict:
    """Verify signature (RS256 via JWKS), issuer, audience and nonce."""
    try:
        header = jwt.get_unverified_header(id_token)
    except JWTError as exc:
        raise SSOError("Malformed identity token.") from exc

    kid = header.get("kid")
    key = _find_key(kid)
    if key is None:
        # Keys rotate — refresh once and retry.
        _jwks_cache.clear()
        key = _find_key(kid)
    if key is None:
        raise SSOError("Could not find the signing key for the identity token.")

    try:
        claims = jwt.decode(
            id_token,
            key,
            algorithms=["RS256"],
            audience=settings.SSO_CLIENT_ID,
            issuer=_discovery().get("issuer"),
        )
    except JWTError as exc:
        raise SSOError(f"Identity token failed validation: {exc}") from exc

    if claims.get("nonce") != nonce:
        raise SSOError("Login nonce mismatch — please try again.")
    return claims


def _find_key(kid: str | None) -> dict | None:
    return next((k for k in _jwks().get("keys", []) if k.get("kid") == kid), None)
