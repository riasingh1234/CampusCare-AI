"""Authentication endpoints:  POST /api/auth/register   POST /api/auth/login   GET /api/auth/me"""
from contextlib import contextmanager

import azure.functions as func

from core.auth_guard import authenticate
from core.azure_clients import sql_connection
from core.config import get_app_settings
from core.responses import handle_errors, json_response, read_json
from repositories.users import UsersRepository
from services.auth_service import AuthService

bp = func.Blueprint()


@contextmanager
def _auth_service():
    """Opens one database connection for the request. Tests replace this function with a fake."""
    with sql_connection() as conn:
        yield AuthService(UsersRepository(conn), get_app_settings())


@bp.route(route="auth/register", methods=["POST"])
@handle_errors
def register(req: func.HttpRequest) -> func.HttpResponse:
    data = read_json(req)
    with _auth_service() as service:
        return json_response(service.register(data), 201)


@bp.route(route="auth/login", methods=["POST"])
@handle_errors
def login(req: func.HttpRequest) -> func.HttpResponse:
    data = read_json(req)
    with _auth_service() as service:
        return json_response(service.login(data))


@bp.route(route="auth/me", methods=["GET"])
@handle_errors
def me(req: func.HttpRequest) -> func.HttpResponse:
    user = authenticate(req)
    with _auth_service() as service:
        return json_response(service.current_user(user.id))
