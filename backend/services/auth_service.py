"""Registration and sign-in rules. Talks to the database only through the repository it is given."""
from datetime import datetime, timedelta, timezone

from core.errors import AuthenticationError, ConflictError, TooManyAttempts
from core.security import DUMMY_HASH, create_access_token, hash_password, verify_password
from core.validation import validate_login, validate_registration

MAX_FAILED_LOGINS = 5
LOCK_MINUTES = 15
GENERIC_LOGIN_ERROR = "Email or password is incorrect."  # same text for unknown email, wrong password and disabled accounts


def public_user(user: dict) -> dict:
    """The only user fields that ever leave the server. Never includes the password hash."""
    return {"id": user["id"], "name": user["name"], "email": user["email"], "role": user["role"],
            "departmentId": user["departmentId"], "enrollmentId": user["enrollmentId"]}


def _as_utc(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


class AuthService:
    def __init__(self, users, settings, now=None):
        self.users = users
        self.settings = settings
        self._now = now or (lambda: datetime.now(timezone.utc))

    def _session(self, user: dict) -> dict:
        token, expires_in = create_access_token(user["id"], user["role"], self.settings)
        return {"token": token, "expiresIn": expires_in, "user": public_user(user)}

    def register(self, data: dict) -> dict:
        """Self-registration is for students only. The role is never read from the request."""
        cleaned = validate_registration(data)
        if self.users.get_by_email(cleaned["email"]):
            raise ConflictError("An account with this email already exists.", details={"email": "Already registered."})
        user_id = self.users.create_user(
            full_name=cleaned["name"], email=cleaned["email"], password_hash=hash_password(cleaned["password"]),
            role="student", department_id=None, enrollment_id=cleaned["enrollmentId"],
        )
        return self._session(self.users.get_by_id(user_id))

    def login(self, data: dict) -> dict:
        cleaned = validate_login(data)
        user = self.users.get_by_email(cleaned["email"])
        if user is None:
            verify_password(DUMMY_HASH, cleaned["password"])  # keep timing similar to a real check
            raise AuthenticationError(GENERIC_LOGIN_ERROR)

        now = self._now()
        if user["lockoutUntil"] and _as_utc(user["lockoutUntil"]) > now:
            raise TooManyAttempts("Too many failed attempts. Please try again in a few minutes.")
        if not user["isActive"]:
            raise AuthenticationError(GENERIC_LOGIN_ERROR)

        if not verify_password(user["passwordHash"], cleaned["password"]):
            failed = user["failedLoginCount"] + 1
            if failed >= MAX_FAILED_LOGINS:
                self.users.set_login_state(user["id"], 0, now + timedelta(minutes=LOCK_MINUTES))
            else:
                self.users.set_login_state(user["id"], failed, None)
            raise AuthenticationError(GENERIC_LOGIN_ERROR)

        if user["failedLoginCount"] or user["lockoutUntil"]:
            self.users.set_login_state(user["id"], 0, None)
        return self._session(user)

    def current_user(self, user_id: int) -> dict:
        user = self.users.get_by_id(user_id)
        if user is None or not user["isActive"]:
            raise AuthenticationError("Sign in to continue.")
        return {"user": public_user(user)}
