import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.errors import AuthenticationError  # noqa: E402
from core.security import ISSUER, create_access_token, decode_access_token, hash_password, verify_password  # noqa: E402
from tests.fakes import SETTINGS  # noqa: E402


class PasswordTests(unittest.TestCase):
    def test_hash_is_not_plaintext_and_verifies(self):
        h = hash_password("Correct-horse-1")
        self.assertNotIn("Correct-horse-1", h)
        self.assertTrue(verify_password(h, "Correct-horse-1"))
        self.assertFalse(verify_password(h, "wrong-password-1"))

    def test_same_password_gets_different_hashes(self):
        self.assertNotEqual(hash_password("Same-pass-1"), hash_password("Same-pass-1"))

    def test_garbage_hash_is_a_failed_check_not_a_crash(self):
        self.assertFalse(verify_password("not-a-hash", "whatever1"))


class TokenTests(unittest.TestCase):
    def test_round_trip(self):
        token, expires_in = create_access_token(7, "staff", SETTINGS)
        claims = decode_access_token(token, SETTINGS)
        self.assertEqual((claims["sub"], claims["role"]), ("7", "staff"))
        self.assertEqual(expires_in, 3600)

    def _forge(self, **overrides):
        now = datetime.now(timezone.utc)
        payload = {"sub": "1", "role": "admin", "iss": ISSUER, "iat": now, "exp": now + timedelta(minutes=5)}
        payload.update(overrides)
        return jwt.encode(payload, SETTINGS.jwt_secret.reveal(), algorithm="HS256")

    def test_expired_token_rejected(self):
        old = datetime.now(timezone.utc) - timedelta(hours=2)
        with self.assertRaises(AuthenticationError) as ctx:
            decode_access_token(self._forge(iat=old, exp=old + timedelta(minutes=1)), SETTINGS)
        self.assertIn("expired", str(ctx.exception))

    def test_wrong_secret_rejected(self):
        bad = jwt.encode({"sub": "1", "role": "admin", "iss": ISSUER, "iat": datetime.now(timezone.utc),
                          "exp": datetime.now(timezone.utc) + timedelta(minutes=5)}, "another-secret-" + "y" * 32, algorithm="HS256")
        with self.assertRaises(AuthenticationError):
            decode_access_token(bad, SETTINGS)

    def test_wrong_issuer_rejected(self):
        with self.assertRaises(AuthenticationError):
            decode_access_token(self._forge(iss="someone-else"), SETTINGS)

    def test_alg_none_rejected(self):
        unsigned = jwt.encode({"sub": "1", "role": "admin", "iss": ISSUER, "iat": 1, "exp": 9999999999}, key=None, algorithm="none")
        with self.assertRaises(AuthenticationError):
            decode_access_token(unsigned, SETTINGS)

    def test_missing_claim_rejected(self):
        token = jwt.encode({"sub": "1", "iss": ISSUER, "exp": datetime.now(timezone.utc) + timedelta(minutes=5)},
                           SETTINGS.jwt_secret.reveal(), algorithm="HS256")  # no iat
        with self.assertRaises(AuthenticationError):
            decode_access_token(token, SETTINGS)


if __name__ == "__main__":
    unittest.main()
