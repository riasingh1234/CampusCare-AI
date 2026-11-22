"""Azure AI Speech: hands the browser a short-lived token so it can recognise speech itself.

Why a token? The Speech key is a secret. If it were in React, anyone could copy it. Instead:
  1. The browser (signed in) asks our backend:  GET /api/speech/token
  2. The backend uses SPEECH_KEY (an app setting, never sent out) to ask Azure for a token that lives 10 minutes.
  3. The browser gives that token to the Speech SDK, which streams the microphone to Azure and gets text back.
We never receive or store any audio.
"""
import logging
import urllib.error
import urllib.request

from core.config import get_speech_settings
from core.errors import ServiceUnavailable

TOKEN_LIFETIME_SECONDS = 540  # Azure tokens last 10 minutes. We tell the browser to renew a minute early.


def issue_speech_token() -> dict:
    settings = get_speech_settings()  # may raise ConfigError, which the endpoint turns into a clean 503
    if not settings.enabled:
        raise ServiceUnavailable("Voice input is not switched on for this server. You can still type your complaint.",
                                 details={"reason": "speech_disabled"})
    url = f"https://{settings.region}.api.cognitive.microsoft.com/sts/v1.0/issueToken"
    request = urllib.request.Request(url, data=b"", method="POST", headers={
        "Ocp-Apim-Subscription-Key": settings.key.reveal(),
        "Content-Length": "0",
    })
    try:
        with urllib.request.urlopen(request, timeout=10) as response:  # noqa: S310 - fixed https URL built from a validated region
            token = response.read().decode("ascii")
    except (urllib.error.URLError, TimeoutError, UnicodeDecodeError) as err:
        # Log the type only. The message of some errors can echo request details.
        logging.warning("Speech token request failed: %s", type(err).__name__)
        raise ServiceUnavailable("Voice input is not available right now. You can still type your complaint.",
                                 details={"reason": "speech_unreachable"})
    if not token:
        raise ServiceUnavailable("Voice input is not available right now. You can still type your complaint.",
                                 details={"reason": "speech_unreachable"})
    return {"token": token, "region": settings.region, "expiresIn": TOKEN_LIFETIME_SECONDS}
