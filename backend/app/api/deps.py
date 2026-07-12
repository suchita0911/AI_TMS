"""Shared FastAPI dependencies: DB session, current user, RBAC guards."""
from __future__ import annotations

from typing import Annotated
from urllib.parse import urlsplit

from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import AuthError, PermissionDeniedError
from app.core.security import TokenType, decode_token
from app.models.enums import RoleName, UserStatus
from app.models.user import User
from app.repositories.user_repository import UserRepository

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_PREFIX}/auth/login", auto_error=False
)

DbSession = Annotated[Session, Depends(get_db)]


def get_current_user(
    db: DbSession, token: Annotated[str | None, Depends(oauth2_scheme)]
) -> User:
    if not token:
        raise AuthError("Not authenticated")
    try:
        payload = decode_token(token, TokenType.ACCESS)
    except JWTError as exc:
        raise AuthError("Invalid or expired token") from exc

    user = UserRepository(db).get(int(payload["sub"]))
    if not user:
        raise AuthError("User not found")
    if not user.is_active or user.status != UserStatus.ACTIVE:
        raise AuthError("Account is inactive")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*roles: RoleName):
    """Dependency factory enforcing that the current user has one of *roles*."""

    def _guard(user: CurrentUser) -> User:
        if user.role.name not in roles:
            raise PermissionDeniedError()
        return user

    return _guard


require_admin = require_roles(RoleName.ADMIN)
require_employee = require_roles(RoleName.EMPLOYEE, RoleName.ADMIN)


def client_ip(request: Request) -> str | None:
    if request.client:
        return request.client.host
    return request.headers.get("x-forwarded-for")


def frontend_base_url(request: Request) -> str:
    """The origin the browser actually used to reach the app, so emailed links
    (set-password, reset-password) point back to the same host/port — whether
    that's localhost, a LAN IP, or a shared dev tunnel. The ``Origin`` header
    is forwarded intact through Vite's ``/api`` proxy (``changeOrigin`` only
    rewrites ``Host``); ``Referer`` is a fallback, and the configured
    ``FRONTEND_BASE_URL`` is the final default (e.g. background jobs)."""
    origin = request.headers.get("origin")
    if origin:
        return origin.rstrip("/")
    referer = request.headers.get("referer")
    if referer:
        parts = urlsplit(referer)
        if parts.scheme and parts.netloc:
            return f"{parts.scheme}://{parts.netloc}"
    return settings.FRONTEND_BASE_URL.rstrip("/")
