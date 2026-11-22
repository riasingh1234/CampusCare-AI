"""Errors the API can raise on purpose. Each one maps to an HTTP status and a safe message."""


class AppError(Exception):
    status = 500
    code = "server_error"

    def __init__(self, message: str, *, details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ValidationError(AppError):
    status = 400
    code = "validation_failed"


class AuthenticationError(AppError):
    status = 401
    code = "unauthenticated"


class PermissionDenied(AppError):
    status = 403
    code = "forbidden"


class NotFoundError(AppError):
    status = 404
    code = "not_found"


class ConflictError(AppError):
    status = 409
    code = "conflict"


class PayloadTooLarge(AppError):
    status = 413
    code = "payload_too_large"


class TooManyAttempts(AppError):
    status = 429
    code = "too_many_attempts"


class ServiceUnavailable(AppError):
    status = 503
    code = "service_unavailable"
