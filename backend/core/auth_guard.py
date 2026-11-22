"""Call authenticate() at the top of an endpoint to require a signed-in user with the right role.

    user = authenticate(req, roles=("admin",))

The role comes from the signed token, never from anything the browser sends in the request body.
"""
from dataclasses import dataclass

import azure.functions as func

from .config import get_app_settings
from .errors import AuthenticationError, PermissionDenied
from .security import decode_access_token


@dataclass(frozen=True)
class CurrentUser:
    id: int
    role: str


def authenticate(req: func.HttpRequest, roles: tuple[str, ...] | None = None) -> CurrentUser:
    header = req.headers.get("Authorization", "")
    if not header.lower().startswith("bearer "):
        raise AuthenticationError("Sign in to continue.")
    claims = decode_access_token(header[7:].strip(), get_app_settings())
    try:
        user = CurrentUser(id=int(claims["sub"]), role=str(claims["role"]))
    except (KeyError, ValueError):
        raise AuthenticationError("Sign in to continue.")
    if roles and user.role not in roles:
        raise PermissionDenied("You do not have access to this action.")
    return user
