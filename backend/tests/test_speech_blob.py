"""Feature 9 (speech token endpoint) and the pure parts of Feature 4 (file checks)."""
import io
import json
import sys
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

import azure.functions as func

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import api.speech as speech_api  # noqa: E402
from core.config import Secret, SpeechSettings, get_speech_settings  # noqa: E402
from core.errors import PayloadTooLarge, ValidationError  # noqa: E402
from core.security import create_access_token  # noqa: E402
from services import blob_storage  # noqa: E402
from tests.fakes import SETTINGS  # noqa: E402

TOKEN = create_access_token(4, "student", SETTINGS)[0]
ON = SpeechSettings(True, "centralindia", Secret("super-secret-speech-key-0123456789"))
OFF = SpeechSettings(False, None, None)


def get_token(token=TOKEN):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    req = func.HttpRequest(method="GET", url="/api/speech/token", headers=headers, body=b"")
    res = speech_api.speech_token.build().get_user_function()(req)
    return res.status_code, res.get_body().decode()


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class SpeechTokenTests(unittest.TestCase):
    def setUp(self):
        p = patch("core.auth_guard.get_app_settings", return_value=SETTINGS)
        p.start()
        self.addCleanup(p.stop)

    def test_disabled_gives_clear_503_and_typing_message(self):
        with patch("services.speech.get_speech_settings", return_value=OFF):
            status, body = get_token()
        self.assertEqual(status, 503)
        self.assertEqual(json.loads(body)["error"]["details"]["reason"], "speech_disabled")
        self.assertIn("type", json.loads(body)["error"]["message"])

    def test_token_is_returned_and_the_key_is_not(self):
        seen = {}

        def fake_urlopen(request, timeout):
            seen["url"], seen["key"] = request.full_url, request.get_header("Ocp-apim-subscription-key")
            return FakeResponse(b"short-lived-token-value")

        with patch("services.speech.get_speech_settings", return_value=ON), patch("urllib.request.urlopen", fake_urlopen):
            status, body = get_token()
        self.assertEqual(status, 200)
        data = json.loads(body)
        self.assertEqual((data["token"], data["region"]), ("short-lived-token-value", "centralindia"))
        self.assertNotIn("super-secret-speech-key", body)
        self.assertEqual(seen["url"], "https://centralindia.api.cognitive.microsoft.com/sts/v1.0/issueToken")
        self.assertEqual(seen["key"], "super-secret-speech-key-0123456789")  # the key goes to Azure only

    def test_azure_unreachable_is_a_clean_503_without_the_key(self):
        with patch("services.speech.get_speech_settings", return_value=ON), \
             patch("urllib.request.urlopen", side_effect=urllib.error.URLError("boom super-secret-speech-key-0123456789")):
            status, body = get_token()
        self.assertEqual(status, 503)
        self.assertNotIn("super-secret", body)
        self.assertEqual(json.loads(body)["error"]["details"]["reason"], "speech_unreachable")

    def test_rejected_key_is_a_clean_503(self):
        err = urllib.error.HTTPError("https://x", 401, "Unauthorized", {}, None)
        with patch("services.speech.get_speech_settings", return_value=ON), patch("urllib.request.urlopen", side_effect=err):
            self.assertEqual(get_token()[0], 503)

    def test_requires_sign_in(self):
        with patch("services.speech.get_speech_settings", return_value=ON):
            self.assertEqual(get_token(None)[0], 401)

    def test_settings_default_off_and_validate_when_on(self):
        with patch.dict("os.environ", {}, clear=True):
            self.assertFalse(get_speech_settings().enabled)
        with patch.dict("os.environ", {"SPEECH_ENABLED": "true"}, clear=True):
            with self.assertRaises(Exception) as ctx:
                get_speech_settings()
        self.assertIn("SPEECH_REGION", str(ctx.exception))
        self.assertIn("SPEECH_KEY", str(ctx.exception))
        with patch.dict("os.environ", {"SPEECH_ENABLED": "true", "SPEECH_REGION": "Central India", "SPEECH_KEY": "k" * 32}, clear=True):
            with self.assertRaises(Exception) as ctx:
                get_speech_settings()
        self.assertIn("region code", str(ctx.exception))
        self.assertNotIn("k" * 32, str(ctx.exception))


class FileCheckTests(unittest.TestCase):
    def test_real_types_are_detected_from_bytes(self):
        cases = [(b"\xff\xd8\xff\xe0data", "image/jpeg", ".jpg"), (b"\x89PNG\r\n\x1a\nabc", "image/png", ".png"),
                 (b"RIFF1234WEBPdata", "image/webp", ".webp"), (b"%PDF-1.4 abc", "application/pdf", ".pdf")]
        for data, ctype, ext in cases:
            self.assertEqual(blob_storage.check_file(data, ctype), (ctype, ext))

    def test_declared_type_may_be_missing(self):
        self.assertEqual(blob_storage.check_file(b"%PDF-1.4 abc", "")[0], "application/pdf")

    def test_rejects_scripts_and_executables_pretending_to_be_images(self):
        for data in (b"<script>alert(1)</script>", b"MZ\x90\x00 program", b"GIF89a..."):
            with self.assertRaises(ValidationError):
                blob_storage.check_file(data, "image/png")

    def test_size_limit(self):
        with self.assertRaises(PayloadTooLarge):
            blob_storage.check_file(b"%PDF-" + b"0" * (5 * 1024 * 1024), "application/pdf")

    def test_display_name_cannot_carry_a_path(self):
        self.assertEqual(blob_storage.safe_display_name("../../etc/passwd"), "passwd")
        self.assertEqual(blob_storage.safe_display_name("C:\\a\\b\\pic.png"), "pic.png")
        self.assertEqual(blob_storage.safe_display_name(""), "file")

    def test_blob_name_is_random_and_ignores_user_input(self):
        a, b = blob_storage.new_blob_name(7, ".png"), blob_storage.new_blob_name(7, ".png")
        self.assertNotEqual(a, b)
        self.assertTrue(a.startswith("complaints/7/") and a.endswith(".png"))

    def test_links_fail_softly_when_storage_is_not_configured(self):
        with patch.dict("os.environ", {}, clear=True):
            self.assertEqual(blob_storage.make_read_urls(["complaints/1/x.png"]), {})
        self.assertEqual(blob_storage.make_read_urls([]), {})


if __name__ == "__main__":
    unittest.main()
