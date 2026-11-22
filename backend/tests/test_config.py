"""Run with:  python -m unittest discover -s tests"""
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.config import ConfigError, get_ai_settings, get_app_settings, get_sql_settings, validate_all  # noqa: E402

SECRET = "super-secret-value-that-must-never-appear-0123456789"
GOOD = {
    "ALLOWED_ORIGIN": "http://localhost:5173",
    "JWT_SECRET": SECRET,
    "SQL_SERVER": "demo-server.database.windows.net",
    "SQL_DATABASE": "campuscare",
    "BLOB_ACCOUNT_URL": "https://demoaccount.blob.core.windows.net",
    "BLOB_CONTAINER_NAME": "complaint-images",
}


class ConfigTests(unittest.TestCase):
    def test_all_good(self):
        with patch.dict(os.environ, GOOD, clear=True):
            self.assertTrue(all(not p for p in validate_all().values()))

    def test_missing_names_only(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ConfigError) as ctx:
                get_sql_settings()
        self.assertIn("SQL_SERVER", str(ctx.exception))
        self.assertIn("SQL_DATABASE", str(ctx.exception))

    def test_placeholder_rejected(self):
        env = {**GOOD, "SQL_SERVER": "<your-sql-server-name>.database.windows.net"}
        with patch.dict(os.environ, env, clear=True):
            with self.assertRaises(ConfigError) as ctx:
                get_sql_settings()
        self.assertIn("placeholder", str(ctx.exception))

    def test_bad_value_is_not_echoed(self):
        env = {**GOOD, "JWT_SECRET": "short-secret-xyz"}
        with patch.dict(os.environ, env, clear=True):
            with self.assertRaises(ConfigError) as ctx:
                get_app_settings()
        self.assertNotIn("short-secret-xyz", str(ctx.exception))

    def test_secret_hidden_in_repr(self):
        with patch.dict(os.environ, GOOD, clear=True):
            settings = get_app_settings()
        self.assertNotIn(SECRET, repr(settings))
        self.assertNotIn(SECRET, str(settings.jwt_secret))
        self.assertEqual(settings.jwt_secret.reveal(), SECRET)

    def test_sql_server_must_be_plain_host(self):
        env = {**GOOD, "SQL_SERVER": "tcp:demo-server.database.windows.net,1433"}
        with patch.dict(os.environ, env, clear=True):
            with self.assertRaises(ConfigError):
                get_sql_settings()

    def test_ai_off_needs_nothing(self):
        with patch.dict(os.environ, {"AI_ENABLED": "false"}, clear=True):
            self.assertFalse(get_ai_settings().enabled)

    def test_ai_entra_needs_project_endpoint(self):
        env = {"AI_ENABLED": "true", "AI_FOUNDRY_DEPLOYMENT": "my-model"}
        with patch.dict(os.environ, env, clear=True):
            with self.assertRaises(ConfigError) as ctx:
                get_ai_settings()
        self.assertIn("AI_FOUNDRY_PROJECT_ENDPOINT", str(ctx.exception))

    def test_ai_api_key_mode_hides_key(self):
        env = {"AI_ENABLED": "true", "AI_AUTH_MODE": "api_key", "AI_FOUNDRY_DEPLOYMENT": "my-model",
               "AI_FOUNDRY_RESOURCE_ENDPOINT": "https://demo.services.ai.azure.com", "AI_FOUNDRY_API_KEY": SECRET}
        with patch.dict(os.environ, env, clear=True):
            settings = get_ai_settings()
        self.assertNotIn(SECRET, repr(settings))


if __name__ == "__main__":
    unittest.main()
