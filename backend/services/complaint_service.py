"""Complaint rules (who may do what). Plain functions: each takes the repositories it needs, so tests can pass fakes.

`user` is the signed-in CurrentUser (id and role from the verified token).
"""
from datetime import timedelta

from core.constants import DUPLICATE_WINDOW_DAYS, SLA_HOURS
from core.errors import ConflictError, NotFoundError, PermissionDenied, ValidationError
from core.validation import (to_id, validate_assignment, validate_complaint, validate_feedback,
                             validate_status_update)
from services.classifier import classify
from services.duplicates import find_duplicates
from services.escalation import utc_now


def load_workspace(repo, ref, user, make_urls) -> dict:
    """Everything the signed-in person may see, in the shape the React app already uses."""
    complaints = repo.list_for(user)
    attachments = repo.attachments_for(user)
    urls = make_urls([a["blobName"] for a in attachments])
    files: dict = {}
    for a in attachments:
        files.setdefault(a["complaintId"], []).append(
            {"id": a["id"], "name": a["name"], "type": a["type"], "size": a["size"], "url": urls.get(a["blobName"])})
    for c in complaints:
        c["attachments"] = files.get(c["id"], [])
        del c["dbId"]
    return {
        "departments": ref.departments(),
        "categories": ref.categories(),
        "users": ref.users_visible_to(user),
        "complaints": complaints,
        "history": repo.history_for(user),
        "feedback": repo.feedback_for(user),
    }


def get_complaint_or_404(repo, reference: str) -> dict:
    complaint = repo.get(reference)
    if complaint is None:
        raise NotFoundError("Complaint not found.")
    return complaint


def can_see(user, complaint: dict) -> bool:
    return (user.role == "admin"
            or (user.role == "student" and complaint["studentId"] == user.id)
            or (user.role == "staff" and complaint["assignedStaffId"] == user.id))


def suggest(ref, data: dict) -> dict | None:
    """Used by POST /ai/classify. Foundry first, rules as the fallback (see services/classifier.py)."""
    return classify(data["title"], data["description"], ref.categories())


def check_duplicates(repo, data: dict) -> list[dict]:
    """Used by POST /complaints/duplicates. Only warns, never blocks."""
    return find_duplicates(repo.recent_open(DUPLICATE_WINDOW_DAYS), data["title"], data["description"], data["location"])


def submit_complaint(repo, ref, user, data: dict) -> dict:
    cleaned = validate_complaint(data)
    categories = ref.categories()
    category = next((c for c in categories if c["id"] == cleaned["categoryId"]), None)
    if category is None:
        raise ValidationError("Please fix the highlighted fields.", details={"categoryId": "Choose a category from the list."})

    ai = classify(cleaned["title"], cleaned["description"], categories)  # may be None: then the category default is used
    priority = ai["priority"] if ai else category["defaultPriority"]
    now = utc_now()
    reference = repo.next_reference(now.year)
    complaint_id = repo.create(
        reference=reference, title=cleaned["title"], description=cleaned["description"], category_id=category["id"],
        location=cleaned["location"], priority=priority, student_id=user.id,
        due_at=now + timedelta(hours=SLA_HOURS[priority]), ai=ai,
    )
    repo.add_history(complaint_id, "Submitted", "Complaint submitted.", user.id)
    return {"id": reference, "priority": priority, "status": "Submitted", "aiSource": ai["source"] if ai else None}


def assign_complaint(repo, ref, admin, reference: str, data: dict) -> dict:
    cleaned = validate_assignment(data)
    complaint = get_complaint_or_404(repo, reference)
    if complaint["status"] == "Resolved":
        raise ConflictError("This complaint is resolved, so it can no longer be reassigned.")
    department = ref.get_department(cleaned["departmentId"])
    staff = ref.get_user(cleaned["staffId"])
    if department is None:
        raise ValidationError("Please fix the highlighted fields.", details={"departmentId": "Department not found."})
    if staff is None or staff["role"] != "staff" or not staff["isActive"] or staff["departmentId"] != department["id"]:
        raise ValidationError("Please fix the highlighted fields.", details={"staffId": "Choose an active staff member of that department."})

    status = "Assigned" if complaint["status"] == "Submitted" else complaint["status"]
    due_at = complaint["createdAt"] + timedelta(hours=SLA_HOURS[cleaned["priority"]])
    repo.assign(complaint_id=complaint["dbId"], department_id=department["id"], staff_id=staff["id"], assigned_by=admin.id,
                priority=cleaned["priority"], due_at=due_at, status=status)
    repo.add_history(complaint["dbId"], status, f"Assigned to {staff['name']} ({department['name']}). Priority: {cleaned['priority']}.", admin.id)
    return {"id": reference, "status": status}


ALLOWED_NEXT = {"Assigned": ("In Progress", "Resolved"), "In Progress": ("Resolved",)}


def change_status(repo, user, reference: str, data: dict) -> dict:
    cleaned = validate_status_update(data)
    complaint = get_complaint_or_404(repo, reference)
    if user.role == "staff" and complaint["assignedStaffId"] != user.id:
        raise NotFoundError("Complaint not found.")  # same answer as a missing one, so staff cannot probe other complaints
    if cleaned["status"] not in ALLOWED_NEXT.get(complaint["status"], ()):
        raise ConflictError(f"A complaint that is {complaint['status']} cannot be moved to {cleaned['status']}.")
    note = cleaned["note"] or ("Work started." if cleaned["status"] == "In Progress" else "")
    repo.set_status(complaint["dbId"], cleaned["status"], cleaned["note"])
    repo.add_history(complaint["dbId"], cleaned["status"], note, user.id)
    return {"id": reference, "status": cleaned["status"]}


def add_feedback(repo, user, reference: str, data: dict) -> dict:
    cleaned = validate_feedback(data)
    complaint = get_complaint_or_404(repo, reference)
    if complaint["studentId"] != user.id:
        raise NotFoundError("Complaint not found.")
    if complaint["status"] != "Resolved":
        raise ConflictError("You can rate a complaint once it is resolved.")
    if repo.has_feedback(complaint["dbId"]):
        raise ConflictError("You have already sent feedback for this complaint.")
    repo.add_feedback(complaint["dbId"], user.id, cleaned["rating"], cleaned["comment"])
    return {"id": reference}


def ids_in_path(value: str, label: str) -> int:
    errors: dict = {}
    number = to_id({"id": value}, "id", label, errors)
    if errors:
        raise NotFoundError(f"{label} not found.")
    return number
