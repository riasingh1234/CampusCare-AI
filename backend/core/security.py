"""Password hashing (Argon2) and login tokens (JWT signed with JWT_SECRET)."""
from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from .errors import AuthenticationError

ISSUER = "campuscare-ai"
_hasher = PasswordHasher()
# Used to spend the same time when an email is unknown, so response time does not reveal which emails exist.
DUMMY_HASH = _hasher.hash("this-is-not-a-real-password-1")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def create_access_token(user_id: int, role: str, settings) -> tuple[str, int]:
    """Returns (token, seconds_until_expiry)."""
    now = datetime.now(timezone.utc)
    lifetime = timedelta(minutes=settings.jwt_expiry_minutes)
    payload = {"sub": str(user_id), "role": role, "iss": ISSUER, "iat": now, "exp": now + lifetime}
    token = jwt.encode(payload, settings.jwt_secret.reveal(), algorithm="HS256")
    return token, int(lifetime.total_seconds())


def decode_access_token(token: str, settings) -> dict:
    try:
        return jwt.decode(
            token,
            settings.jwt_secret.reveal(),
            algorithms=["HS256"],  # fixed list: never trust the algorithm named inside the token
            issuer=ISSUER,
            options={"require": ["exp", "iat", "sub", "iss"]},
        )
    except jwt.ExpiredSignatureError:
        raise AuthenticationError("Your session has expired. Please sign in again.")
    except jwt.PyJWTError:
        raise AuthenticationError("Sign in to continue.")
