"""Authentication & password lifecycle business logic."""
from __future__ import annotations

import re
from datetime import datetime, timezone

from jose import JWTError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import AuthError, ConflictError, NotFoundError
from app.core.logging_config import get_logger
from app.core.security import (
    TokenType,
    create_access_token,
    create_password_reset_token,
    create_password_setup_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.auth import PasswordToken
from app.models.enums import RoleName, UserStatus
from app.models.user import User
from app.repositories.user_repository import RoleRepository, UserRepository
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    RegisterRequest,
    SetPasswordRequest,
)
from app.services.audit_service import AuditService
from app.utils import email

logger = get_logger(__name__)


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.users = UserRepository(db)
        self.roles = RoleRepository(db)
        self.audit = AuditService(db)

    # ------------------------------------------------------------------ #
    # Registration + password setup
    # ------------------------------------------------------------------ #
    def register(self, data: RegisterRequest, base_url: str | None = None) -> tuple[User, str]:
        if self.users.get_by_email(data.email):
            raise ConflictError("Email is already registered")
        if data.employee_id and self.users.get_by_employee_id(data.employee_id):
            raise ConflictError("Employee ID is already in use")

        # Registration is by email; derive a username when one isn't supplied.
        raw_username = (data.username or "").strip()
        if raw_username:
            if self.users.get_by_username(raw_username):
                raise ConflictError("Username is already taken")
            username = raw_username
        else:
            username = self._unique_username(str(data.email).split("@")[0])

        role = self.roles.get_by_name(RoleName.EMPLOYEE)
        if not role:
            raise NotFoundError("Employee role is not configured")

        # Self-registration does not collect a password. The account starts
        # PENDING and the user receives a one-time link to set their own
        # password before they can sign in.
        user = User(
            first_name=data.first_name,
            last_name=data.last_name,
            username=username,
            email=str(data.email),
            employee_id=data.employee_id,
            department_id=data.department_id,
            role_id=role.id,
            hashed_password=None,
            status=UserStatus.PENDING,
            is_active=True,
        )
        self.users.add(user)

        setup_token = self._issue_password_token(user, TokenType.PASSWORD_SETUP)
        self.audit.record(action="user.register", user_id=user.id, entity_type="user",
                          entity_id=user.id)
        self.db.commit()
        email.send_password_setup_email(user, setup_token, base_url=base_url)
        # Auto-enroll self-registered employees into published mandatory courses.
        from app.services.assignment_service import AssignmentService
        AssignmentService(self.db).assign_mandatory_courses_to_user(user)
        return user, setup_token

    def set_password(self, data: SetPasswordRequest) -> User:
        return self._consume_password_token(
            data.token, data.new_password, TokenType.PASSWORD_SETUP
        )

    def reset_password(self, data: SetPasswordRequest) -> User:
        return self._consume_password_token(
            data.token, data.new_password, TokenType.PASSWORD_RESET
        )

    # ------------------------------------------------------------------ #
    # Login / refresh
    # ------------------------------------------------------------------ #
    def authenticate(self, data: LoginRequest, ip: str | None = None) -> tuple[User, dict]:
        # Accept either the username or the email address as the login identifier
        # (both are unique, case-insensitive), so users aren't tripped up when
        # their username happens to be an email or vice versa.
        identifier = data.username.strip()
        user = self.users.get_by_username(identifier) or self.users.get_by_email(identifier)
        if not user or not user.hashed_password or not verify_password(
            data.password, user.hashed_password
        ):
            self.audit.record(action="auth.login", entity_type="user",
                              detail=f"failed login for '{data.username}'",
                              ip_address=ip, success=False)
            self.db.commit()
            raise AuthError("Invalid username or password")

        if not user.is_active:
            raise AuthError("Account is disabled. Contact your administrator.")
        if user.status == UserStatus.PENDING:
            raise AuthError("Password not set. Please complete password setup.")

        user.last_login_at = datetime.now(timezone.utc)
        self.audit.record(action="auth.login", user_id=user.id, entity_type="user",
                          entity_id=user.id, ip_address=ip)
        self.db.commit()
        return user, self._build_tokens(user)

    # ------------------------------------------------------------------ #
    # SSO (OpenID Connect) login
    # ------------------------------------------------------------------ #
    def sso_login(self, claims: dict, ip: str | None = None) -> tuple[User, dict]:
        """Log a user in from validated OIDC claims, provisioning if allowed.

        SSO sits alongside password login: the provider vouches for the user's
        identity, so we match on email, optionally create the account, and issue
        the same JWTs the password flow does.
        """
        email = (claims.get("email") or claims.get("preferred_username") or "").strip().lower()
        if not email:
            raise AuthError("Your identity provider did not share an email address.")

        user = self.users.get_by_email(email)
        if not user:
            if not settings.SSO_AUTO_PROVISION:
                raise AuthError("No account exists for this email. Contact your administrator.")
            user = self._provision_sso_user(email, claims)

        if not user.is_active:
            raise AuthError("Account is disabled. Contact your administrator.")
        # SSO identities are pre-verified — a pending account is activated on first use.
        if user.status == UserStatus.PENDING:
            user.status = UserStatus.ACTIVE

        user.last_login_at = datetime.now(timezone.utc)
        self.audit.record(action="auth.sso_login", user_id=user.id, entity_type="user",
                          entity_id=user.id, ip_address=ip)
        self.db.commit()
        return user, self._build_tokens(user)

    def _provision_sso_user(self, email: str, claims: dict) -> User:
        role = self.roles.get_by_name(RoleName.EMPLOYEE)
        if not role:
            raise NotFoundError("Employee role is not configured")

        first = (claims.get("given_name") or "").strip()
        last = (claims.get("family_name") or "").strip()
        if not first and not last:
            name = (claims.get("name") or email.split("@")[0]).strip()
            parts = name.split(None, 1)
            first = parts[0]
            last = parts[1] if len(parts) > 1 else ""

        user = User(
            first_name=first or email.split("@")[0],
            last_name=last,
            username=self._unique_username(email.split("@")[0]),
            email=email,
            role_id=role.id,
            hashed_password=None,  # SSO users authenticate via the provider
            status=UserStatus.ACTIVE,
            is_active=True,
        )
        self.users.add(user)
        self.db.flush()
        self.audit.record(action="user.sso_provision", user_id=user.id,
                          entity_type="user", entity_id=user.id, detail=email)
        # Match the self-registration flow: enroll into published mandatory courses.
        from app.services.assignment_service import AssignmentService
        AssignmentService(self.db).assign_mandatory_courses_to_user(user)
        return user

    def _unique_username(self, base: str) -> str:
        base = re.sub(r"[^A-Za-z0-9._-]", "", base) or "user"
        candidate = base[:80]
        i = 1
        while self.users.get_by_username(candidate):
            suffix = str(i)
            candidate = f"{base[: 80 - len(suffix)]}{suffix}"
            i += 1
        return candidate

    def refresh(self, refresh_token: str) -> dict:
        try:
            payload = decode_token(refresh_token, TokenType.REFRESH)
        except JWTError as exc:
            raise AuthError("Invalid or expired refresh token") from exc
        user = self.users.get(int(payload["sub"]))
        if not user or not user.is_active:
            raise AuthError("User no longer active")
        return self._build_tokens(user)

    # ------------------------------------------------------------------ #
    # Forgot / change password
    # ------------------------------------------------------------------ #
    def forgot_password(self, email_addr: str, base_url: str | None = None) -> str | None:
        user = self.users.get_by_email(email_addr)
        # Do not reveal whether the email exists.
        if not user or not user.is_active:
            return None
        token = self._issue_password_token(user, TokenType.PASSWORD_RESET)
        self.audit.record(action="auth.forgot_password", user_id=user.id,
                          entity_type="user", entity_id=user.id)
        self.db.commit()

        base = (base_url or settings.FRONTEND_BASE_URL).rstrip("/")
        link = f"{base}/reset-password?token={token}"
        hours = settings.PASSWORD_RESET_TOKEN_EXPIRE_HOURS
        subject = "Reset your AI TMS password"
        text = (
            f"Hi {user.first_name},\n\n"
            f"We received a request to reset your password. "
            f"Open the link below to choose a new one (valid for {hours} hours):\n\n"
            f"{link}\n\n"
            f"If you didn't request this, you can safely ignore this email."
        )
        html = (
            f"<p>Hi {user.first_name},</p>"
            f"<p>We received a request to reset your password. "
            f"Click the button below to choose a new one "
            f"(this link is valid for {hours} hours):</p>"
            f'<p><a href="{link}" '
            f'style="display:inline-block;padding:10px 18px;background:#4f46e5;'
            f'color:#fff;border-radius:6px;text-decoration:none">Reset password</a></p>'
            f'<p>Or paste this link into your browser:<br><a href="{link}">{link}</a></p>'
            f"<p style=\"color:#666\">If you didn't request this, you can safely ignore this email.</p>"
        )
        email.send_email(user.email, subject, html, text)
        return token

    def change_password(self, user: User, data: ChangePasswordRequest) -> None:
        if not user.hashed_password or not verify_password(
            data.current_password, user.hashed_password
        ):
            raise AuthError("Current password is incorrect")
        user.hashed_password = hash_password(data.new_password)
        self.audit.record(action="auth.change_password", user_id=user.id,
                          entity_type="user", entity_id=user.id)
        self.db.commit()

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    def _build_tokens(self, user: User) -> dict:
        return {
            "access_token": create_access_token(user.id, user.role.name.value),
            "refresh_token": create_refresh_token(user.id),
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        }

    def _issue_password_token(self, user: User, token_type: TokenType) -> str:
        if token_type == TokenType.PASSWORD_SETUP:
            token = create_password_setup_token(user.id)
            purpose = "setup"
        else:
            token = create_password_reset_token(user.id)
            purpose = "reset"
        payload = decode_token(token)
        self.db.add(
            PasswordToken(
                user_id=user.id,
                jti=payload["jti"],
                purpose=purpose,
                expires_at=datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
            )
        )
        self.db.flush()
        return token

    def _consume_password_token(
        self, token: str, new_password: str, token_type: TokenType
    ) -> User:
        try:
            payload = decode_token(token, token_type)
        except JWTError as exc:
            raise AuthError("Invalid or expired token") from exc

        record = (
            self.db.query(PasswordToken)
            .filter(PasswordToken.jti == payload["jti"])
            .one_or_none()
        )
        if not record:
            raise AuthError("Token not recognised")
        if record.is_used:
            raise AuthError("This token has already been used")

        user = self.users.get(int(payload["sub"]))
        if not user:
            raise NotFoundError("User not found")

        user.hashed_password = hash_password(new_password)
        user.status = UserStatus.ACTIVE
        record.used_at = datetime.now(timezone.utc)
        self.audit.record(action=f"auth.{token_type.value}", user_id=user.id,
                          entity_type="user", entity_id=user.id)
        self.db.commit()
        return user
