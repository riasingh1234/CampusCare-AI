"""Complaint endpoints. Each one: check who is calling, read the input, call a service function, return JSON.

  GET  /api/workspace                         everything the signed-in person may see
  POST /api/ai/classify                       suggested category / priority / department (Foundry, else rules)
  POST /api/complaints/duplicates             possible look-alike complaints (warning only)
  POST /api/complaints                        submit a complaint            (students)
  POST /api/complaints/{reference}/assign     assign to staff               (admin)
  POST /api/complaints/{reference}/status     update status                 (assigned staff, admin)
  POST /api/complaints/{reference}/feedback   rate a resolved complaint     (the student who reported it)
  POST /api/complaints/{reference}/attachments?name=photo.jpg   upload a file; the request body IS the file
"""
import re

import azure.functions as func

from core.auth_guard import authenticate
from core.constants import MAX_ATTACHMENT_BYTES, MAX_ATTACHMENTS_PER_COMPLAINT
from core.errors import ConflictError, NotFoundError, PayloadTooLarge
from core.responses import handle_errors, json_response, read_json
from core.validation import validate_classify_input, validate_duplicate_input
from repositories import open_repos
from services import complaint_service as svc
from services.blob_storage import check_file, make_read_urls, new_blob_name, safe_display_name, upload_blob

bp = func.Blueprint()

_REFERENCE = re.compile(r"^CC-\d{4}-\d{4,}$")


def _reference(req: func.HttpRequest) -> str:
    value = req.route_params.get("reference", "")
    if not _REFERENCE.match(value):
        raise NotFoundError("Complaint not found.")
    return value


@bp.route(route="workspace", methods=["GET"])
@handle_errors
def workspace(req: func.HttpRequest) -> func.HttpResponse:
    user = authenticate(req)
    with open_repos() as (repo, ref):
        return json_response(svc.load_workspace(repo, ref, user, make_read_urls))


@bp.route(route="ai/classify", methods=["POST"])
@handle_errors
def classify_text(req: func.HttpRequest) -> func.HttpResponse:
    authenticate(req)
    data = validate_classify_input(read_json(req))
    with open_repos() as (_repo, ref):
        return json_response({"suggestion": svc.suggest(ref, data)})


@bp.route(route="complaints/duplicates", methods=["POST"])
@handle_errors
def duplicates(req: func.HttpRequest) -> func.HttpResponse:
    authenticate(req)
    data = validate_duplicate_input(read_json(req))
    with open_repos() as (repo, _ref):
        return json_response({"duplicates": svc.check_duplicates(repo, data)})


@bp.route(route="complaints", methods=["POST"])
@handle_errors
def submit(req: func.HttpRequest) -> func.HttpResponse:
    user = authenticate(req, roles=("student",))
    data = read_json(req)
    with open_repos() as (repo, ref):
        return json_response(svc.submit_complaint(repo, ref, user, data), 201)


@bp.route(route="complaints/{reference}/assign", methods=["POST"])
@handle_errors
def assign(req: func.HttpRequest) -> func.HttpResponse:
    admin = authenticate(req, roles=("admin",))
    reference = _reference(req)
    data = read_json(req)
    with open_repos() as (repo, ref):
        return json_response(svc.assign_complaint(repo, ref, admin, reference, data))


@bp.route(route="complaints/{reference}/status", methods=["POST"])
@handle_errors
def update_status(req: func.HttpRequest) -> func.HttpResponse:
    user = authenticate(req, roles=("staff", "admin"))
    reference = _reference(req)
    data = read_json(req)
    with open_repos() as (repo, _ref):
        return json_response(svc.change_status(repo, user, reference, data))


@bp.route(route="complaints/{reference}/feedback", methods=["POST"])
@handle_errors
def feedback(req: func.HttpRequest) -> func.HttpResponse:
    user = authenticate(req, roles=("student",))
    reference = _reference(req)
    data = read_json(req)
    with open_repos() as (repo, _ref):
        return json_response(svc.add_feedback(repo, user, reference, data), 201)


@bp.route(route="complaints/{reference}/attachments", methods=["POST"])
@handle_errors
def upload_attachment(req: func.HttpRequest) -> func.HttpResponse:
    user = authenticate(req)
    reference = _reference(req)
    data = req.get_body()
    if len(data) > MAX_ATTACHMENT_BYTES:
        raise PayloadTooLarge("The file must be under 5 MB.")
    content_type, extension = check_file(data, req.headers.get("Content-Type", ""))

    with open_repos() as (repo, _ref):
        complaint = svc.get_complaint_or_404(repo, reference)
        if not svc.can_see(user, complaint):
            raise NotFoundError("Complaint not found.")  # same answer as a missing complaint
        if repo.count_attachments(complaint["dbId"]) >= MAX_ATTACHMENTS_PER_COMPLAINT:
            raise ConflictError(f"A complaint can have at most {MAX_ATTACHMENTS_PER_COMPLAINT} files.")
        blob_name = new_blob_name(complaint["dbId"], extension)
        upload_blob(blob_name, data, content_type)  # file goes to Blob Storage first...
        attachment_id = repo.add_attachment(        # ...then only its name is stored in Azure SQL
            complaint_id=complaint["dbId"], blob_name=blob_name, original_name=safe_display_name(req.params.get("name", "")),
            content_type=content_type, size=len(data), uploaded_by=user.id)
    return json_response({"id": attachment_id, "type": content_type}, 201)
