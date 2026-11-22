"""All SQL for the Users table. Every query is parameterized: values are passed separately, never joined into the text."""
from datetime import datetime

from core.errors import ConflictError

_COLUMNS = ("UserId, FullName, Email, PasswordHash, Role, DepartmentId, EnrollmentId, "
            "IsActive, FailedLoginCount, LockoutUntil")


def _to_user(row) -> dict:
    return {
        "id": row.UserId,
        "name": row.FullName,
        "email": row.Email,
        "passwordHash": row.PasswordHash,
        "role": row.Role,
        "departmentId": row.DepartmentId,
        "enrollmentId": row.EnrollmentId,
        "isActive": bool(row.IsActive),
        "failedLoginCount": row.FailedLoginCount,
        "lockoutUntil": row.LockoutUntil,
    }


class UsersRepository:
    def __init__(self, conn):
        self.conn = conn

    def get_by_email(self, email: str) -> dict | None:
        cur = self.conn.cursor()
        cur.execute(f"SELECT {_COLUMNS} FROM dbo.Users WHERE Email = ?", email)
        row = cur.fetchone()
        return _to_user(row) if row else None

    def get_by_id(self, user_id: int) -> dict | None:
        cur = self.conn.cursor()
        cur.execute(f"SELECT {_COLUMNS} FROM dbo.Users WHERE UserId = ?", user_id)
        row = cur.fetchone()
        return _to_user(row) if row else None

    def create_user(self, *, full_name: str, email: str, password_hash: str, role: str,
                    department_id: int | None, enrollment_id: str | None) -> int:
        import pyodbc  # imported here so tests and config checks work without the driver

        cur = self.conn.cursor()
        try:
            cur.execute(
                "INSERT INTO dbo.Users (FullName, Email, PasswordHash, Role, DepartmentId, EnrollmentId) "
                "OUTPUT INSERTED.UserId VALUES (?, ?, ?, ?, ?, ?)",
                full_name, email, password_hash, role, department_id, enrollment_id,
            )
            return int(cur.fetchone()[0])
        except pyodbc.IntegrityError:
            # Two people registering the same email at once: the unique index decides.
            raise ConflictError("An account with this email already exists.", details={"email": "Already registered."})

    def set_login_state(self, user_id: int, failed_count: int, lockout_until: datetime | None) -> None:
        stored = lockout_until.replace(tzinfo=None) if lockout_until else None  # DATETIME2 holds UTC without a zone
        self.conn.cursor().execute(
            "UPDATE dbo.Users SET FailedLoginCount = ?, LockoutUntil = ? WHERE UserId = ?",
            failed_count, stored, user_id,
        )
