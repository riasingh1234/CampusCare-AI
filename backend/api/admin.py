"""Admin endpoints (all need an admin sign-in).

  GET    /api/admin/analytics?tz=330         charts and statistics from Azure SQL
  POST   /api/admin/escalation/run           run the escalation check now (same code as the 6-hourly timer)
  POST   /api/admin/departments              add            PUT/DELETE /api/admin/departments/{id}
  POST   /api/admin/categories               add            PUT/DELETE /api/admin/categories/{id}
"""
import azure.functions as func

from core.auth_guard import authenticate
from core.errors import ConflictError, NotFoundError, ValidationError
from core.responses import handle_errors, json_response, read_json
from core.validation import validate_category, validate_department
from repositories import open_repos
from services.analytics import build_analytics
from services.complaint_service import ids_in_path
from services.escalation import run_escalation, utc_now

bp = func.Blueprint()


@bp.route(route="admin/analytics", methods=["GET"])
@handle_errors
def analytics(req: func.HttpRequest) -> func.HttpResponse:
    authenticate(req, roles=("admin",))
    try:  # the browser sends its own UTC offset in minutes so "per day" matches the admin's local day
        tz = max(-840, min(840, int(req.params.get("tz", "0"))))
    except ValueError:
        tz = 0
    with open_repos() as (repo, ref):
        result = build_analytics(repo.analytics_rows(), repo.feedback_rows(), ref.departments(), utc_now(), tz)
    return json_response(result)


@bp.route(route="admin/escalation/run", methods=["POST"])
@handle_errors
def run_escalation_now(req: func.HttpRequest) -> func.HttpResponse:
    authenticate(req, roles=("admin",))
    with open_repos() as (repo, _ref):
        return json_response(run_escalation(repo))


# ------------------------------------------------------------------ departments
@bp.route(route="admin/departments", methods=["POST"])
@handle_errors
def add_department(req: func.HttpRequest) -> func.HttpResponse:
    authenticate(req, roles=("admin",))
    data = validate_department(read_json(req))
    with open_repos() as (_repo, ref):
        return json_response({"id": ref.create_department(data["name"])}, 201)


@bp.route(route="admin/departments/{id}", methods=["PUT"])
@handle_errors
def edit_department(req: func.HttpRequest) -> func.HttpResponse:
    authenticate(req, roles=("admin",))
    department_id = ids_in_path(req.route_params.get("id", ""), "Department")
    data = validate_department(read_json(req))
    with open_repos() as (_repo, ref):
        if not ref.rename_department(department_id, data["name"]):
            raise NotFoundError("Department not found.")
    return json_response({"id": department_id})


@bp.route(route="admin/departments/{id}", methods=["DELETE"])
@handle_errors
def remove_department(req: func.HttpRequest) -> func.HttpResponse:
    authenticate(req, roles=("admin",))
    department_id = ids_in_path(req.route_params.get("id", ""), "Department")
    with open_repos() as (_repo, ref):
        if ref.get_department(department_id) is None:
            raise NotFoundError("Department not found.")
        if ref.department_in_use(department_id):
            raise ConflictError("This department still has categories, staff or complaints. Move them first.")
        ref.delete_department(department_id)
    return json_response({"id": department_id})


# ------------------------------------------------------------------- categories
@bp.route(route="admin/categories", methods=["POST"])
@handle_errors
def add_category(req: func.HttpRequest) -> func.HttpResponse:
    authenticate(req, roles=("admin",))
    data = validate_category(read_json(req))
    with open_repos() as (_repo, ref):
        _check_department_exists(ref, data["departmentId"])
        new_id = ref.create_category(data["name"], data["departmentId"], data["defaultPriority"], data["keywords"])
    return json_response({"id": new_id}, 201)


@bp.route(route="admin/categories/{id}", methods=["PUT"])
@handle_errors
def edit_category(req: func.HttpRequest) -> func.HttpResponse:
    authenticate(req, roles=("admin",))
    category_id = ids_in_path(req.route_params.get("id", ""), "Category")
    data = validate_category(read_json(req))
    with open_repos() as (_repo, ref):
        _check_department_exists(ref, data["departmentId"])
        if not ref.update_category(category_id, data["name"], data["departmentId"], data["defaultPriority"], data["keywords"]):
            raise NotFoundError("Category not found.")
    return json_response({"id": category_id})


@bp.route(route="admin/categories/{id}", methods=["DELETE"])
@handle_errors
def remove_category(req: func.HttpRequest) -> func.HttpResponse:
    authenticate(req, roles=("admin",))
    category_id = ids_in_path(req.route_params.get("id", ""), "Category")
    with open_repos() as (_repo, ref):
        if ref.category_in_use(category_id):
            raise ConflictError("Complaints already use this category, so it cannot be deleted.")
        if not ref.delete_category(category_id):
            raise NotFoundError("Category not found.")
    return json_response({"id": category_id})


def _check_department_exists(ref, department_id: int) -> None:
    if ref.get_department(department_id) is None:
        raise ValidationError("Please fix the highlighted fields.", details={"departmentId": "Department not found."})
