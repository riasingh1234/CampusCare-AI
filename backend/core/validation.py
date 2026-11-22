"""Input validation. Mirrors frontend/src/lib/validation.js. The server never trusts the browser's checks."""
import re

from .errors import ValidationError

_EMAIL = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def clean_text(data: dict, field: str, label: str, *, minimum: int = 1, maximum: int = 100, required: bool = True, errors: dict) -> str | None:
    value = data.get(field)
    if value is None or (isinstance(value, str) and not value.strip()):
        if required:
            errors[field] = f"{label} is required."
        return None
    if not isinstance(value, str):
        errors[field] = f"{label} must be text."
        return None
    value = " ".join(value.split())  # trims and collapses repeated spaces
    if len(value) < minimum:
        errors[field] = f"{label} must be at least {minimum} characters."
    elif len(value) > maximum:
        errors[field] = f"{label} must be at most {maximum} characters."
    return value


def check_password(password, errors: dict, field: str = "password") -> None:
    if not isinstance(password, str) or not password:
        errors[field] = "Password is required."
    elif len(password) < 8:
        errors[field] = "Use at least 8 characters."
    elif len(password) > 128:
        errors[field] = "Use at most 128 characters."
    elif not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
        errors[field] = "Include at least one letter and one number."


def _raise_if(errors: dict) -> None:
    if errors:
        raise ValidationError("Please fix the highlighted fields.", details=errors)


def validate_registration(data: dict) -> dict:
    errors: dict = {}
    name = clean_text(data, "name", "Full name", minimum=2, maximum=100, errors=errors)
    email = clean_text(data, "email", "Email", maximum=254, errors=errors)
    enrollment = clean_text(data, "enrollmentId", "Enrollment ID", maximum=40, required=False, errors=errors)
    if email and not _EMAIL.match(email):
        errors["email"] = "Enter a valid email address."
    password = data.get("password")
    check_password(password, errors)
    _raise_if(errors)
    return {"name": name, "email": email.lower(), "enrollmentId": enrollment, "password": password}


def validate_login(data: dict) -> dict:
    errors: dict = {}
    email = clean_text(data, "email", "Email", maximum=254, errors=errors)
    password = data.get("password")
    if not isinstance(password, str) or not password:
        errors["password"] = "Password is required."
    elif len(password) > 128:
        errors["password"] = "Use at most 128 characters."
    _raise_if(errors)
    return {"email": email.lower(), "password": password}


# ------------------------------------------------------------------ complaints
# Everything below mirrors frontend/src/lib/validation.js. IDs may arrive as numbers or digit strings.
from .constants import PRIORITIES, STATUSES  # noqa: E402


def to_id(data: dict, field: str, label: str, errors: dict, required: bool = True) -> int | None:
    value = data.get(field)
    if value is None or value == "":
        if required:
            errors[field] = f"{label} is required."
        return None
    if isinstance(value, bool) or not (isinstance(value, int) or (isinstance(value, str) and value.strip().isdigit())):
        errors[field] = f"{label} is not valid."
        return None
    return int(value)


def text_block(data: dict, field: str, label: str, *, minimum: int, maximum: int, required: bool, errors: dict) -> str | None:
    """Like clean_text, but keeps line breaks (descriptions and notes can have several lines)."""
    value = data.get(field)
    if value is None or (isinstance(value, str) and not value.strip()):
        if required:
            errors[field] = f"{label} is required."
        return None
    if not isinstance(value, str):
        errors[field] = f"{label} must be text."
        return None
    value = value.replace("\r\n", "\n").strip()
    if len(value) < minimum:
        errors[field] = f"{label} must be at least {minimum} characters."
    elif len(value) > maximum:
        errors[field] = f"{label} must be at most {maximum} characters."
    return value


def validate_complaint(data: dict) -> dict:
    errors: dict = {}
    title = clean_text(data, "title", "Title", minimum=5, maximum=100, errors=errors)
    description = text_block(data, "description", "Description", minimum=20, maximum=1000, required=True, errors=errors)
    location = clean_text(data, "location", "Location", minimum=2, maximum=100, errors=errors)
    category_id = to_id(data, "categoryId", "Category", errors)
    _raise_if(errors)
    return {"title": title, "description": description, "location": location, "categoryId": category_id}


def validate_classify_input(data: dict) -> dict:
    """Lenient: a short or empty text just gives no suggestion. Long text is cut, never rejected."""
    title = data.get("title") if isinstance(data.get("title"), str) else ""
    description = data.get("description") if isinstance(data.get("description"), str) else ""
    return {"title": " ".join(title.split())[:100], "description": description.strip()[:1000]}


def validate_duplicate_input(data: dict) -> dict:
    cleaned = validate_classify_input(data)
    location = data.get("location") if isinstance(data.get("location"), str) else ""
    cleaned["location"] = " ".join(location.split())[:100]
    return cleaned


def validate_assignment(data: dict) -> dict:
    errors: dict = {}
    department_id = to_id(data, "departmentId", "Department", errors)
    staff_id = to_id(data, "staffId", "Staff member", errors)
    priority = data.get("priority")
    if priority not in PRIORITIES:
        errors["priority"] = "Choose a priority."
    _raise_if(errors)
    return {"departmentId": department_id, "staffId": staff_id, "priority": priority}


def validate_status_update(data: dict) -> dict:
    errors: dict = {}
    status = data.get("status")
    if status not in STATUSES:
        errors["status"] = "Choose a valid status."
    note = text_block(data, "note", "Note", minimum=0, maximum=500, required=False, errors=errors) or ""
    if status == "Resolved" and len(note) < 10:
        errors["note"] = "Add a resolution note of at least 10 characters."
    _raise_if(errors)
    return {"status": status, "note": note}


def validate_feedback(data: dict) -> dict:
    errors: dict = {}
    rating = data.get("rating")
    if isinstance(rating, bool) or not isinstance(rating, int) or not 1 <= rating <= 5:
        errors["rating"] = "Choose a rating from 1 to 5."
    comment = text_block(data, "comment", "Comment", minimum=0, maximum=500, required=False, errors=errors) or ""
    _raise_if(errors)
    return {"rating": rating, "comment": comment}


def validate_department(data: dict) -> dict:
    errors: dict = {}
    name = clean_text(data, "name", "Department name", minimum=2, maximum=100, errors=errors)
    _raise_if(errors)
    return {"name": name}


def validate_category(data: dict) -> dict:
    errors: dict = {}
    name = clean_text(data, "name", "Category name", minimum=2, maximum=100, errors=errors)
    department_id = to_id(data, "departmentId", "Department", errors)
    priority = data.get("defaultPriority")
    if priority not in PRIORITIES:
        errors["defaultPriority"] = "Choose a default priority."
    raw = data.get("keywords", [])
    if isinstance(raw, str):
        raw = raw.split(",")
    if not isinstance(raw, list):
        errors["keywords"] = "Keywords must be a list or comma separated text."
        raw = []
    keywords = []
    for item in raw:
        word = " ".join(str(item).lower().split())
        if word and word not in keywords:
            keywords.append(word)
    if len(keywords) > 40 or any(len(k) > 40 for k in keywords) or len(",".join(keywords)) > 1000:
        errors["keywords"] = "Use at most 40 keywords of up to 40 characters each."
    _raise_if(errors)
    return {"name": name, "departmentId": department_id, "defaultPriority": priority, "keywords": keywords}
