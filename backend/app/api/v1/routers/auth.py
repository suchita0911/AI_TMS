"""Authentication endpoints."""
from __future__ import annotations

from urllib.parse import quote, urlencode

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import RedirectResponse

from app.api.deps import CurrentUser, DbSession, client_ip, frontend_base_url
from app.core import oidc
from app.core.config import settings
from app.core.exceptions import AppError
from app.core.security import TokenType, decode_token
from app.schemas.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    RegisterResponse,
    ResetPasswordRequest,
    SetPasswordRequest,
    TokenResponse,
)
from app.schemas.common import Message
from app.schemas.user import DepartmentBrief, UserOut
from app.services.auth_service import AuthService
from app.services.user_service import UserService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.get("/departments", response_model=list[DepartmentBrief])
def public_departments(db: DbSession):
    """Active departments for the public registration form (id + name only)."""
    items, _ = UserService(db).list_departments(limit=100)
    return [DepartmentBrief(id=d.id, name=d.name) for d in items if d.is_active]


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, request: Request, db: DbSession):
    user, setup_token = AuthService(db).register(payload, base_url=frontend_base_url(request))
    return RegisterResponse(
        user=UserOut.from_model(user),
        setup_token=setup_token if settings.DEBUG else None,
    )


@router.post("/set-password", response_model=UserOut)
def set_password(payload: SetPasswordRequest, db: DbSession):
    user = AuthService(db).set_password(payload)
    return UserOut.from_model(user)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request, db: DbSession):
    user, tokens = AuthService(db).authenticate(payload, ip=client_ip(request))
    return TokenResponse(**tokens, user=UserOut.from_model(user))


# --------------------------------- SSO ------------------------------------- #
@router.get("/sso/status")
def sso_status(email: str | None = None):
    """Whether SSO is available and, if an email is given, whether that email is
    eligible for SSO — so the login page enables the button only for SSO emails."""
    return {
        "enabled": oidc.is_enabled(),
        "provider": "microsoft",
        "domains": settings.sso_domains,
        "eligible": settings.sso_eligible_email(email) if email else False,
    }


def _sso_error_redirect(message: str) -> RedirectResponse:
    return RedirectResponse(f"{settings.SSO_POST_LOGIN_URL}#error={quote(message)}")


@router.get("/sso/login")
def sso_login():
    """Kick off the OIDC authorization-code flow (browser redirect to provider)."""
    if not oidc.is_enabled():
        return _sso_error_redirect("Single sign-on is not configured.")
    try:
        return RedirectResponse(oidc.authorization_url())
    except oidc.SSOError as exc:
        return _sso_error_redirect(str(exc))


@router.get("/sso/callback")
def sso_callback(request: Request, db: DbSession, code: str | None = None,
                 state: str | None = None, error: str | None = None,
                 error_description: str | None = None):
    """Handle the provider redirect, then hand tokens to the frontend."""
    if error:
        return _sso_error_redirect(error_description or error)
    if not code or not state:
        return _sso_error_redirect("The sign-in response was incomplete.")
    try:
        nonce = oidc.read_state(state)
        token_response = oidc.exchange_code(code)
        id_token = token_response.get("id_token")
        if not id_token:
            raise oidc.SSOError("The identity provider did not return an identity token.")
        claims = oidc.validate_id_token(id_token, nonce)
        _, tokens = AuthService(db).sso_login(claims, ip=client_ip(request))
    except oidc.SSOError as exc:
        return _sso_error_redirect(str(exc))
    except AppError as exc:
        return _sso_error_redirect(exc.detail)

    fragment = urlencode({
        "access_token": tokens["access_token"],
        "refresh_token": tokens["refresh_token"],
        "expires_in": tokens["expires_in"],
    })
    return RedirectResponse(f"{settings.SSO_POST_LOGIN_URL}#{fragment}")


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, db: DbSession):
    service = AuthService(db)
    tokens = service.refresh(payload.refresh_token)
    sub = int(decode_token(payload.refresh_token, TokenType.REFRESH)["sub"])
    user = service.users.get(sub)
    return TokenResponse(**tokens, user=UserOut.from_model(user))


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
def forgot_password(payload: ForgotPasswordRequest, request: Request, db: DbSession):
    token = AuthService(db).forgot_password(str(payload.email), base_url=frontend_base_url(request))
    return ForgotPasswordResponse(
        message="If the email exists, a password reset link has been sent.",
        reset_token=token if settings.DEBUG else None,
    )


@router.post("/reset-password", response_model=UserOut)
def reset_password(payload: ResetPasswordRequest, db: DbSession):
    user = AuthService(db).reset_password(payload)
    return UserOut.from_model(user)


@router.get("/me", response_model=UserOut)
def me(current_user: CurrentUser):
    return UserOut.from_model(current_user)


@router.post("/change-password", response_model=Message)
def change_password(payload: ChangePasswordRequest, current_user: CurrentUser, db: DbSession):
    AuthService(db).change_password(current_user, payload)
    return Message(detail="Password updated successfully")
