import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.errors import AuthenticationError, ConflictError, TooManyAttempts, ValidationError  # noqa: E402
from core.security import decode_access_token, hash_password  # noqa: E402
from services.auth_service import AuthService, MAX_FAILED_LOGINS  # noqa: E402
from tests.fakes import SETTINGS, FakeUsers  # noqa: E402

GOOD = {"name": "Test Student", "email": "Test.Student@College.edu", "password": "Passw0rd-ok", "enrollmentId": "ST-1"}


class AuthServiceTests(unittest.TestCase):
    def setUp(self):
        self.users = FakeUsers()
        self.clock = [datetime(2026, 11, 22, 12, 0, tzinfo=timezone.utc)]
        self.svc = AuthService(self.users, SETTINGS, now=lambda: self.clock[0])

    def test_register_creates_student_and_returns_token(self):
        out = self.svc.register(GOOD)
        self.assertEqual(out["user"]["role"], "student")
        self.assertEqual(out["user"]["email"], "test.student@college.edu")
        self.assertNotIn("passwordHash", out["user"])
        self.assertEqual(decode_access_token(out["token"], SETTINGS)["role"], "student")
        stored = self.users.get_by_email("test.student@college.edu")
        self.assertNotEqual(stored["passwordHash"], GOOD["password"])

    def test_register_ignores_role_sent_by_the_browser(self):
        out = self.svc.register({**GOOD, "role": "admin", "departmentId": 3})
        self.assertEqual(out["user"]["role"], "student")
        self.assertIsNone(out["user"]["departmentId"])

    def test_register_rejects_duplicate_email(self):
        self.svc.register(GOOD)
        with self.assertRaises(ConflictError):
            self.svc.register({**GOOD, "email": "test.student@college.edu"})

    def test_register_validation_lists_fields(self):
        with self.assertRaises(ValidationError) as ctx:
            self.svc.register({"name": "A", "email": "nope", "password": "short"})
        self.assertEqual(set(ctx.exception.details), {"name", "email", "password"})

    def test_login_success_and_wrong_password_share_one_message(self):
        self.svc.register(GOOD)
        ok = self.svc.login({"email": GOOD["email"], "password": GOOD["password"]})
        self.assertIn("token", ok)
        with self.assertRaises(AuthenticationError) as wrong:
            self.svc.login({"email": GOOD["email"], "password": "Wrong-pass1"})
        with self.assertRaises(AuthenticationError) as unknown:
            self.svc.login({"email": "nobody@college.edu", "password": "Wrong-pass1"})
        self.assertEqual(str(wrong.exception), str(unknown.exception))

    def test_lockout_after_repeated_failures_then_recovers(self):
        self.svc.register(GOOD)
        bad = {"email": GOOD["email"], "password": "Wrong-pass1"}
        for _ in range(MAX_FAILED_LOGINS):
            with self.assertRaises(AuthenticationError):
                self.svc.login(bad)
        with self.assertRaises(TooManyAttempts):  # even the correct password is refused while locked
            self.svc.login({"email": GOOD["email"], "password": GOOD["password"]})
        self.clock[0] += timedelta(minutes=16)
        self.assertIn("token", self.svc.login({"email": GOOD["email"], "password": GOOD["password"]}))
        self.assertEqual(self.users.get_by_email("test.student@college.edu")["failedLoginCount"], 0)

    def test_successful_login_resets_the_failure_counter(self):
        self.svc.register(GOOD)
        with self.assertRaises(AuthenticationError):
            self.svc.login({"email": GOOD["email"], "password": "Wrong-pass1"})
        self.svc.login({"email": GOOD["email"], "password": GOOD["password"]})
        self.assertEqual(self.users.get_by_email("test.student@college.edu")["failedLoginCount"], 0)

    def test_disabled_account_cannot_sign_in(self):
        uid = self.users.create_user(full_name="Old Staff", email="old@college.edu", password_hash=hash_password("Passw0rd-ok"),
                                     role="staff", department_id=1, enrollment_id=None)
        self.users.rows[uid]["isActive"] = False
        with self.assertRaises(AuthenticationError):
            self.svc.login({"email": "old@college.edu", "password": "Passw0rd-ok"})

    def test_current_user(self):
        uid = self.svc.register(GOOD)["user"]["id"]
        self.assertEqual(self.svc.current_user(uid)["user"]["id"], uid)
        with self.assertRaises(AuthenticationError):
            self.svc.current_user(999)


if __name__ == "__main__":
    unittest.main()
