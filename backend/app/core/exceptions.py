"""Domain exceptions mapped to HTTP responses by handlers in main.py."""
from __future__ import annotations


class AppError(Exception):
    """Base application error."""

    status_code: int = 400
    default_detail: str = "Application error"

    def __init__(self, detail: str | None = None):
        self.detail = detail or self.default_detail
        super().__init__(self.detail)


class NotFoundError(AppError):
    status_code = 404
    default_detail = "Resource not found"


class ConflictError(AppError):
    status_code = 409
    default_detail = "Resource already exists"


class AuthError(AppError):
    status_code = 401
    default_detail = "Authentication failed"


class PermissionDeniedError(AppError):
    status_code = 403
    default_detail = "You do not have permission to perform this action"


class ValidationError(AppError):
    status_code = 422
    default_detail = "Validation failed"


class BusinessRuleError(AppError):
    status_code = 400
    default_detail = "Operation not allowed"
