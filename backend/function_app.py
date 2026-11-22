"""Azure Functions entry point (Python v2 programming model).

Endpoints live in api/*.py as blueprints and are registered here.
"""
import json
import logging

import azure.functions as func

from api.admin import bp as admin_bp
from api.auth import bp as auth_bp
from api.complaints import bp as complaints_bp
from api.speech import bp as speech_bp
from core.config import validate_all
from timers.escalation import bp as escalation_bp

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)
app.register_functions(auth_bp)
app.register_functions(complaints_bp)
app.register_functions(admin_bp)
app.register_functions(speech_bp)
app.register_functions(escalation_bp)


@app.route(route="health", methods=["GET"])
def health(req: func.HttpRequest) -> func.HttpResponse:
    """Config-only health check. It does NOT contact Azure.

    The public response says only ok / misconfigured. Variable names go to the log, not to the caller.
    """
    problems = {group: p for group, p in validate_all().items() if p}
    for group, items in problems.items():
        for item in items:
            logging.warning("Config problem [%s]: %s", group, item)
    status = "misconfigured" if problems else "ok"
    return func.HttpResponse(
        json.dumps({"status": status, "checks": "configuration only"}),
        status_code=503 if problems else 200,
        mimetype="application/json",
    )
