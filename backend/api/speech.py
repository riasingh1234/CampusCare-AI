"""GET /api/speech/token  ->  {token, region, expiresIn}. The browser uses it with the Azure Speech SDK.

Needs a signed-in user. The Speech key itself never leaves the server (see services/speech.py).
"""
import azure.functions as func

from core.auth_guard import authenticate
from core.responses import handle_errors, json_response
from services.speech import issue_speech_token

bp = func.Blueprint()


@bp.route(route="speech/token", methods=["GET"])
@handle_errors
def speech_token(req: func.HttpRequest) -> func.HttpResponse:
    authenticate(req)
    return json_response(issue_speech_token())
