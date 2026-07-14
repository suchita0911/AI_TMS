"""Authentication request/response schemas."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.models.enums import RoleName
from app.schemas.common import Email, RequiredEmployeeId, USERNAME_PATTERN
from app.schemas.user import UserOut


class RegisterRequest(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=80)
    last_name: str = Field(..., min_length=1, max_length=80)
    # Optional: registration is by email; a username is derived when omitted.
    username: Optional[str] = Field(None, min_length=3, max_length=80, pattern=USERNAME_PATTERN)
    email: Email
    department_id: Optional[int] = None
    employee_id: RequiredEmployeeId = Field(..., max_length=50)
    designation: Optional[str] = Field(None, max_length=120)


class RegisterResponse(BaseModel):
    user: UserOut
    message: str = (
        "Registration successful. Check your email for a link to set your "
        "password, then sign in."
    )
    # Returned only in DEBUG so the flow can be exercised without email infra.
    setup_token: Optional[str] = None


class SetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def _strength(cls, v: str) -> str:
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        if not any(c.isalpha() for c in v):
            raise ValueError("Password must contain at least one letter")
        return v


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserOut


class RefreshRequest(BaseModel):
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    email: Email


class ForgotPasswordResponse(BaseModel):
    message: str
    # Returned only in DEBUG so the flow can be exercised without email infra.
    reset_token: Optional[str] = None


class ResetPasswordRequest(SetPasswordRequest):
    pass


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128)


class TokenPayload(BaseModel):
    sub: str
    role: Optional[RoleName] = None
    type: str
