"""Helpers for reading requests and building JSON responses, plus one error handler for every endpoint."""
import functools
import json
import logging
from datetime import datetime

import azure.functions as func

from .config import ConfigError
from .errors import AppError, PayloadTooLarge, ValidationError

MAX_BODY_BYTES = 64 * 1024


def _default(value):
    if isinstance(value, datetime):
        return value.isoformat() + ("Z" if value.tzinfo is None else "")
    raise TypeError(f"Cannot serialise {type(value).__name__}")


def json_response(data, status: int = 200) -> func.HttpResponse:
    return func.HttpResponse(
        json.dumps(data, default=_default),
        status_code=status,
        mimetype="application/json",
        headers={"Cache-Control": "no-store"},
    )


def error_response(status: int, code: str, message: str, details: dict | None = None) -> func.HttpResponse:
    return json_response({"error": {"code": code, "message": message, "details": details or {}}}, status)


def read_json(req: func.HttpRequest, max_bytes: int = MAX_BODY_BYTES) -> dict:
    body = req.get_body()
    if len(body) > max_bytes:
        raise PayloadTooLarge("The request is too large.")
    if not body:
        raise ValidationError("The request body is empty.")
    try:
        data = json.loads(body)
    except (ValueError, UnicodeDecodeError):
        raise ValidationError("The request body must be valid JSON.")
    if not isinstance(data, dict):
        raise ValidationError("The request body must be a JSON object.")
    return data


def handle_errors(fn):
    """Wrap an endpoint so every failure becomes a clean JSON error and never leaks internals."""

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except AppError as err:
            return error_response(err.status, err.code, err.message, err.details)
        except ConfigError as err:
            logging.error("Configuration problem: %s", err)  # variable names only, never values
            return error_response(503, "service_unavailable", "The server is not configured correctly.")
        except Exception as err:  # noqa: BLE001 - last line of defence
            if type(err).__module__.startswith("pyodbc"):
                logging.exception("Database error")
                return error_response(503, "database_unavailable", "The database is not reachable right now. Please try again in a moment.")
            logging.exception("Unhandled error")
            return error_response(500, "server_error", "Something went wrong on our side.")

    return wrapper
