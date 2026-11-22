"""Calls the real endpoint functions with real HTTP request objects. Only the database is faked."""
import json
import sys
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

import azure.functions as func

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import api.auth as auth_api  # noqa: E402
from core.auth_guard import authenticate  # noqa: E402
from core.errors import PermissionDenied  # noqa: E402
from core.responses import handle_errors  # noqa: E402
from core.security import create_access_token  # noqa: E402
from services.auth_service import AuthService  # noqa: E402
from tests.fakes import SETTINGS, FakeUsers  # noqa: E402


def call(route_fn, method="POST", body=None, headers=None, raw=None):
    data = raw if raw is not None else (json.dumps(body).encode() if body is not None else b"")
    req = func.HttpRequest(method=method, url="/api/x", headers=headers or {}, body=data)
    # The decorated function is wrapped by the Functions library; get_user_function() returns our function.
    return route_fn.build().get_user_function()(req)


class ApiAuthTests(unittest.TestCase):
    def setUp(self):
        self.users = FakeUsers()

        @contextmanager
        def fake_service():
            yield AuthService(self.users, SETTINGS)

        patches = [patch.object(auth_api, "_auth_service", fake_service),
                   patch("core.auth_guard.get_app_settings", return_value=SETTINGS)]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def reg(self, **extra):
        body = {"name": "Test Student", "email": "t@college.edu", "password": "Passw0rd-ok", **extra}
        return call(auth_api.register, body=body)

    def test_register_then_login_then_me(self):
        r = self.reg()
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.headers.get("Cache-Control"), "no-store")
        login = call(auth_api.login, body={"email": "t@college.edu", "password": "Passw0rd-ok"})
        self.assertEqual(login.status_code, 200)
        token = json.loads(login.get_body())["token"]
        me = call(auth_api.me, method="GET", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(me.status_code, 200)
        self.assertEqual(json.loads(me.get_body())["user"]["email"], "t@college.edu")

    def test_me_without_token_is_401_with_json_error(self):
        r = call(auth_api.me, method="GET")
        self.assertEqual(r.status_code, 401)
        self.assertEqual(json.loads(r.get_body())["error"]["code"], "unauthenticated")

    def test_me_with_garbage_token_is_401(self):
        self.assertEqual(call(auth_api.me, method="GET", headers={"Authorization": "Bearer abc.def.ghi"}).status_code, 401)

    def test_wrong_password_is_401_and_not_500(self):
        self.reg()
        r = call(auth_api.login, body={"email": "t@college.edu", "password": "Nope-nope-1"})
        self.assertEqual(r.status_code, 401)

    def test_validation_error_is_400_with_field_details(self):
        r = call(auth_api.register, body={"name": "x", "email": "bad", "password": "1"})
        body = json.loads(r.get_body())
        self.assertEqual(r.status_code, 400)
        self.assertIn("email", body["error"]["details"])

    def test_duplicate_is_409(self):
        self.reg()
        self.assertEqual(self.reg().status_code, 409)

    def test_bad_bodies(self):
        self.assertEqual(call(auth_api.login, raw=b"").status_code, 400)
        self.assertEqual(call(auth_api.login, raw=b"{not json").status_code, 400)
        self.assertEqual(call(auth_api.login, raw=b"[1,2]").status_code, 400)
        self.assertEqual(call(auth_api.login, raw=b"x" * 70_000).status_code, 413)

    def test_unexpected_error_hides_details(self):
        @handle_errors
        def boom(req):
            raise RuntimeError("secret connection detail")

        r = boom(None)
        self.assertEqual(r.status_code, 500)
        self.assertNotIn("secret", r.get_body().decode())

    def test_role_guard(self):
        token, _ = create_access_token(1, "student", SETTINGS)
        req = func.HttpRequest("GET", "/api/x", headers={"Authorization": f"Bearer {token}"}, body=b"")
        self.assertEqual(authenticate(req).role, "student")
        with self.assertRaises(PermissionDenied):
            authenticate(req, roles=("admin",))


if __name__ == "__main__":
    unittest.main()
