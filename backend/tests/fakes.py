"""In-memory stand-ins used by the tests, so no Azure resource is needed."""
from core.config import AppSettings, Secret

SETTINGS = AppSettings(env="local", allowed_origin="http://localhost:5173",
                       jwt_secret=Secret("unit-test-secret-" + "x" * 32), jwt_expiry_minutes=60)


class FakeUsers:
    """Same methods as repositories.users.UsersRepository."""

    def __init__(self):
        self.rows: dict[int, dict] = {}
        self.next_id = 1

    def get_by_email(self, email):
        return next((dict(u) for u in self.rows.values() if u["email"] == email), None)

    def get_by_id(self, user_id):
        return dict(self.rows[user_id]) if user_id in self.rows else None

    def create_user(self, *, full_name, email, password_hash, role, department_id, enrollment_id):
        uid = self.next_id
        self.next_id += 1
        self.rows[uid] = {"id": uid, "name": full_name, "email": email, "passwordHash": password_hash, "role": role,
                          "departmentId": department_id, "enrollmentId": enrollment_id, "isActive": True,
                          "failedLoginCount": 0, "lockoutUntil": None}
        return uid

    def set_login_state(self, user_id, failed_count, lockout_until):
        self.rows[user_id]["failedLoginCount"] = failed_count
        self.rows[user_id]["lockoutUntil"] = lockout_until


# ----------------------------------------------------------------------------------------------
# Fakes for the complaint features. They behave like repositories/complaints.py and repositories/reference.py,
# but keep everything in Python lists, so the tests need no database.
from datetime import datetime, timedelta  # noqa: E402

from core.errors import ConflictError  # noqa: E402

CATEGORIES = [
    {"id": 1, "name": "Electrical fault", "departmentId": 1, "defaultPriority": "High",
     "keywords": ["power", "electric", "switch", "socket", "light", "fan", "bulb", "wiring", "flicker", "projector"]},
    {"id": 2, "name": "Water & plumbing", "departmentId": 2, "defaultPriority": "Medium",
     "keywords": ["water", "leak", "tap", "pipe", "drain", "toilet", "flush", "overflow"]},
    {"id": 3, "name": "Wi-Fi & computers", "departmentId": 3, "defaultPriority": "Medium",
     "keywords": ["wifi", "wi fi", "internet", "network", "router", "computer", "login"]},
    {"id": 4, "name": "Cleanliness & waste", "departmentId": 4, "defaultPriority": "Low",
     "keywords": ["dirty", "garbage", "waste", "dustbin", "bin", "clean", "smell", "litter"]},
]
DEPARTMENTS = [{"id": 1, "name": "Electrical"}, {"id": 2, "name": "Plumbing & Water"},
               {"id": 3, "name": "IT & Network"}, {"id": 4, "name": "Housekeeping"}]
USERS = [
    {"id": 1, "name": "Meera Admin", "role": "admin", "departmentId": None, "isActive": True},
    {"id": 2, "name": "Ravi Electrician", "role": "staff", "departmentId": 1, "isActive": True},
    {"id": 3, "name": "Anil Plumber", "role": "staff", "departmentId": 2, "isActive": True},
    {"id": 4, "name": "Aarav Student", "role": "student", "departmentId": None, "isActive": True},
    {"id": 5, "name": "Ishita Student", "role": "student", "departmentId": None, "isActive": True},
]
NOW = datetime(2026, 11, 22, 12, 0, 0)  # a fixed "now" (naive UTC) for deterministic tests


class FakeReference:
    def __init__(self):
        self.depts = [dict(d) for d in DEPARTMENTS]
        self.cats = [dict(c) for c in CATEGORIES]
        self.users = [dict(u) for u in USERS]
        self.used_departments: set = set()
        self.used_categories: set = set()
        self.next_id = 100

    def departments(self):
        return [dict(d) for d in self.depts]

    def categories(self):
        return [dict(c) for c in self.cats]

    def users_visible_to(self, user):
        return [{k: u[k] for k in ("id", "name", "role", "departmentId")} for u in self.users
                if u["role"] in ("staff", "admin") or u["id"] == user.id or user.role == "admin"]

    def get_user(self, user_id):
        return next((dict(u) for u in self.users if u["id"] == user_id), None)

    def get_department(self, department_id):
        return next((dict(d) for d in self.depts if d["id"] == department_id), None)

    def create_department(self, name):
        if any(d["name"].lower() == name.lower() for d in self.depts):
            raise ConflictError("A department with this name already exists.")
        self.next_id += 1
        self.depts.append({"id": self.next_id, "name": name})
        return self.next_id

    def rename_department(self, department_id, name):
        for d in self.depts:
            if d["id"] == department_id:
                d["name"] = name
                return True
        return False

    def department_in_use(self, department_id):
        return department_id in self.used_departments

    def delete_department(self, department_id):
        self.depts = [d for d in self.depts if d["id"] != department_id]
        return True

    def create_category(self, name, department_id, default_priority, keywords):
        if any(c["name"].lower() == name.lower() for c in self.cats):
            raise ConflictError("A category with this name already exists.")
        self.next_id += 1
        self.cats.append({"id": self.next_id, "name": name, "departmentId": department_id,
                          "defaultPriority": default_priority, "keywords": list(keywords)})
        return self.next_id

    def update_category(self, category_id, name, department_id, default_priority, keywords):
        for c in self.cats:
            if c["id"] == category_id:
                c.update(name=name, departmentId=department_id, defaultPriority=default_priority, keywords=list(keywords))
                return True
        return False

    def category_in_use(self, category_id):
        return category_id in self.used_categories

    def delete_category(self, category_id):
        before = len(self.cats)
        self.cats = [c for c in self.cats if c["id"] != category_id]
        return len(self.cats) < before


class FakeComplaints:
    def __init__(self, now=NOW):
        self.now = now
        self.rows: list[dict] = []
        self.history: list[dict] = []
        self.feedback: list[dict] = []
        self.files: list[dict] = []
        self.escalations: set = set()
        self.counter = 0

    # reading
    def _find(self, reference):
        return next((r for r in self.rows if r["id"] == reference), None)

    def get(self, reference):
        r = self._find(reference)
        return dict(r) if r else None

    def _visible(self, user):
        if user.role == "admin":
            return list(self.rows)
        if user.role == "staff":
            return [r for r in self.rows if r["assignedStaffId"] == user.id]
        return [r for r in self.rows if r["studentId"] == user.id]

    def list_for(self, user):
        return [dict(r) for r in sorted(self._visible(user), key=lambda r: r["createdAt"], reverse=True)]

    def history_for(self, user):
        refs = {r["id"] for r in self._visible(user)}
        return [dict(h) for h in self.history if h["complaintId"] in refs]

    def feedback_for(self, user):
        refs = {r["id"] for r in self._visible(user)}
        return [dict(f) for f in self.feedback if f["complaintId"] in refs]

    def attachments_for(self, user):
        refs = {r["id"] for r in self._visible(user)}
        return [dict(f) for f in self.files if f["complaintId"] in refs]

    # writing
    def next_reference(self, year):
        self.counter += 1
        return f"CC-{year}-{self.counter:04d}"

    def create(self, *, reference, title, description, category_id, location, priority, student_id, due_at, ai):
        db_id = len(self.rows) + 1
        ai_row = None if not ai else {"categoryId": ai["categoryId"], "departmentId": ai["departmentId"], "priority": ai["priority"],
                                      "explanation": ai["explanation"], "source": ai["source"]}
        self.rows.append({"id": reference, "dbId": db_id, "title": title, "description": description, "categoryId": category_id,
                          "location": location, "priority": priority, "status": "Submitted", "studentId": student_id,
                          "departmentId": None, "assignedStaffId": None, "createdAt": self.now, "updatedAt": self.now,
                          "dueAt": due_at, "resolvedAt": None, "resolutionNote": None, "isEscalated": False,
                          "escalatedAt": None, "aiSuggestion": ai_row})
        return db_id

    def _by_db(self, db_id):
        return next(r for r in self.rows if r["dbId"] == db_id)

    def add_history(self, complaint_id, status, note, changed_by):
        self.history.append({"id": len(self.history) + 1, "complaintId": self._by_db(complaint_id)["id"], "status": status,
                             "note": note or "", "byId": changed_by, "at": self.now})

    def assign(self, *, complaint_id, department_id, staff_id, assigned_by, priority, due_at, status):
        r = self._by_db(complaint_id)
        r.update(departmentId=department_id, assignedStaffId=staff_id, priority=priority, dueAt=due_at, status=status)

    def set_status(self, complaint_id, status, resolution_note):
        r = self._by_db(complaint_id)
        r["status"] = status
        if status == "Resolved":
            r["resolvedAt"], r["resolutionNote"] = self.now, resolution_note

    def has_feedback(self, complaint_id):
        ref = self._by_db(complaint_id)["id"]
        return any(f["complaintId"] == ref for f in self.feedback)

    def add_feedback(self, complaint_id, student_id, rating, comment):
        self.feedback.append({"id": len(self.feedback) + 1, "complaintId": self._by_db(complaint_id)["id"],
                              "studentId": student_id, "rating": rating, "comment": comment, "createdAt": self.now})

    def count_attachments(self, complaint_id):
        ref = self._by_db(complaint_id)["id"]
        return sum(1 for f in self.files if f["complaintId"] == ref)

    def add_attachment(self, *, complaint_id, blob_name, original_name, content_type, size, uploaded_by):
        self.files.append({"id": len(self.files) + 1, "complaintId": self._by_db(complaint_id)["id"], "blobName": blob_name,
                           "name": original_name, "type": content_type, "size": size})
        return len(self.files)

    # duplicate detection, analytics, escalation
    def recent_open(self, days):
        limit = self.now - timedelta(days=days)
        return [{k: r[k] for k in ("id", "title", "description", "location", "status")}
                for r in self.rows if r["status"] != "Resolved" and r["createdAt"] >= limit]

    def analytics_rows(self):
        cats = {c["id"]: c for c in CATEGORIES}
        return [{"id": r["dbId"], "categoryName": cats[r["categoryId"]]["name"],
                 "departmentId": r["departmentId"] or cats[r["categoryId"]]["departmentId"], "priority": r["priority"],
                 "status": r["status"], "createdAt": r["createdAt"], "resolvedAt": r["resolvedAt"], "dueAt": r["dueAt"],
                 "isEscalated": r["isEscalated"]} for r in self.rows]

    def feedback_rows(self):
        cats = {c["id"]: c for c in CATEGORIES}
        out = []
        for f in self.feedback:
            r = self._find(f["complaintId"])
            out.append({"rating": f["rating"], "departmentId": r["departmentId"] or cats[r["categoryId"]]["departmentId"]})
        return out

    def open_for_escalation(self):
        return [{"id": r["dbId"], "reference": r["id"], "priority": r["priority"], "status": r["status"],
                 "createdAt": r["createdAt"], "dueAt": r["dueAt"]} for r in self.rows if r["status"] != "Resolved"]

    def record_escalation(self, complaint_id, reason, details):
        if (complaint_id, reason) in self.escalations:
            return False
        self.escalations.add((complaint_id, reason))
        return True

    def mark_escalated(self, complaint_id):
        r = self._by_db(complaint_id)
        r["isEscalated"] = True
        r["escalatedAt"] = r["escalatedAt"] or self.now
