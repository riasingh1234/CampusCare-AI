"""All SQL for complaints and everything attached to them. Every query is parameterized (values are never joined into the text).

`user` arguments are core.auth_guard.CurrentUser objects. The WHERE part decides what each role may see:
  student -> own complaints   staff -> complaints currently assigned to them   admin -> all
"""
# One complaint plus who it is currently assigned to (if anyone).
_FROM = "FROM dbo.Complaints c LEFT JOIN dbo.Assignments a ON a.ComplaintId = c.ComplaintId AND a.IsCurrent = 1 "


def _scope(user) -> tuple[str, list]:
    if user.role == "admin":
        return "", []
    if user.role == "staff":
        return "WHERE a.StaffId = ? ", [user.id]
    return "WHERE c.StudentId = ? ", [user.id]


def _complaint(r) -> dict:
    ai = None
    if r.AiSource:
        ai = {"categoryId": r.AiCategoryId, "departmentId": r.AiDepartmentId, "priority": r.AiPriority,
              "explanation": r.AiExplanation, "source": r.AiSource}
    return {
        "id": r.Reference, "dbId": r.ComplaintId, "title": r.Title, "description": r.Description,
        "categoryId": r.CategoryId, "location": r.Location, "priority": r.Priority, "status": r.Status,
        "studentId": r.StudentId, "departmentId": r.AssignedDepartmentId, "assignedStaffId": r.StaffId,
        "createdAt": r.CreatedAt, "updatedAt": r.UpdatedAt, "dueAt": r.DueAt, "resolvedAt": r.ResolvedAt,
        "resolutionNote": r.ResolutionNote, "isEscalated": bool(r.IsEscalated), "escalatedAt": r.EscalatedAt,
        "aiSuggestion": ai,
    }


_COMPLAINT_COLUMNS = (
    "SELECT c.ComplaintId, c.Reference, c.Title, c.Description, c.CategoryId, c.Location, c.Priority, c.Status, c.StudentId, "
    "c.DueAt, c.ResolvedAt, c.ResolutionNote, c.IsEscalated, c.EscalatedAt, c.AiCategoryId, c.AiDepartmentId, c.AiPriority, "
    "c.AiExplanation, c.AiSource, c.CreatedAt, c.UpdatedAt, a.DepartmentId AS AssignedDepartmentId, a.StaffId "
)


class ComplaintsRepository:
    def __init__(self, conn):
        self.conn = conn

    def _all(self, sql, params=()):
        cur = self.conn.cursor()
        cur.execute(sql, *params)
        return cur.fetchall()

    def _one(self, sql, params=()):
        cur = self.conn.cursor()
        cur.execute(sql, *params)
        return cur.fetchone()

    def _run(self, sql, params=()) -> int:
        cur = self.conn.cursor()
        cur.execute(sql, *params)
        return cur.rowcount

    # ------------------------------------------------------------- reading
    def get(self, reference: str) -> dict | None:
        row = self._one(_COMPLAINT_COLUMNS + _FROM + "WHERE c.Reference = ?", [reference])
        return None if row is None else _complaint(row)

    def list_for(self, user) -> list[dict]:
        where, params = _scope(user)
        return [_complaint(r) for r in self._all(_COMPLAINT_COLUMNS + _FROM + where + "ORDER BY c.CreatedAt DESC", params)]

    def history_for(self, user) -> list[dict]:
        where, params = _scope(user)
        sql = ("SELECT h.HistoryId, c.Reference, h.Status, h.Note, h.ChangedBy, h.ChangedAt FROM dbo.StatusHistory h "
               "JOIN dbo.Complaints c ON c.ComplaintId = h.ComplaintId "
               "LEFT JOIN dbo.Assignments a ON a.ComplaintId = c.ComplaintId AND a.IsCurrent = 1 " + where + "ORDER BY h.ChangedAt, h.HistoryId")
        return [{"id": r.HistoryId, "complaintId": r.Reference, "status": r.Status, "note": r.Note or "", "byId": r.ChangedBy, "at": r.ChangedAt}
                for r in self._all(sql, params)]

    def feedback_for(self, user) -> list[dict]:
        where, params = _scope(user)
        sql = ("SELECT f.FeedbackId, c.Reference, f.StudentId, f.Rating, f.Comment, f.CreatedAt FROM dbo.Feedback f "
               "JOIN dbo.Complaints c ON c.ComplaintId = f.ComplaintId "
               "LEFT JOIN dbo.Assignments a ON a.ComplaintId = c.ComplaintId AND a.IsCurrent = 1 " + where)
        return [{"id": r.FeedbackId, "complaintId": r.Reference, "studentId": r.StudentId, "rating": r.Rating,
                 "comment": r.Comment or "", "createdAt": r.CreatedAt} for r in self._all(sql, params)]

    def attachments_for(self, user) -> list[dict]:
        where, params = _scope(user)
        sql = ("SELECT t.AttachmentId, c.Reference, t.BlobName, t.OriginalName, t.ContentType, t.SizeBytes FROM dbo.Attachments t "
               "JOIN dbo.Complaints c ON c.ComplaintId = t.ComplaintId "
               "LEFT JOIN dbo.Assignments a ON a.ComplaintId = c.ComplaintId AND a.IsCurrent = 1 " + where + "ORDER BY t.AttachmentId")
        return [{"id": r.AttachmentId, "complaintId": r.Reference, "blobName": r.BlobName, "name": r.OriginalName,
                 "type": r.ContentType, "size": r.SizeBytes} for r in self._all(sql, params)]

    # ------------------------------------------------------------- writing
    def next_reference(self, year: int) -> str:
        number = self._one("SELECT NEXT VALUE FOR dbo.ComplaintNumberSeq")[0]
        return f"CC-{year}-{number:04d}"

    def create(self, *, reference, title, description, category_id, location, priority, student_id, due_at, ai) -> int:
        """`ai` is the classifier result (or None). Returns the new internal ComplaintId."""
        sql = ("INSERT INTO dbo.Complaints (Reference, Title, Description, CategoryId, Location, Priority, StudentId, DueAt, "
               "AiCategoryId, AiDepartmentId, AiPriority, AiExplanation, AiSource) OUTPUT INSERTED.ComplaintId "
               "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)")
        params = [reference, title, description, category_id, location, priority, student_id, due_at,
                  ai["categoryId"] if ai else None, ai["departmentId"] if ai else None, ai["priority"] if ai else None,
                  ai["explanation"][:500] if ai else None, ai["source"] if ai else None]
        return self._one(sql, params)[0]

    def add_history(self, complaint_id: int, status: str, note: str, changed_by: int | None) -> None:
        self._run("INSERT INTO dbo.StatusHistory (ComplaintId, Status, Note, ChangedBy) VALUES (?, ?, ?, ?)",
                  [complaint_id, status, note or None, changed_by])

    def assign(self, *, complaint_id, department_id, staff_id, assigned_by, priority, due_at, status) -> None:
        """Closes the current assignment, adds the new one and updates the complaint, all in one transaction."""
        self._run("UPDATE dbo.Assignments SET IsCurrent = 0 WHERE ComplaintId = ? AND IsCurrent = 1", [complaint_id])
        self._run("INSERT INTO dbo.Assignments (ComplaintId, DepartmentId, StaffId, AssignedBy) VALUES (?, ?, ?, ?)",
                  [complaint_id, department_id, staff_id, assigned_by])
        self._run("UPDATE dbo.Complaints SET Priority = ?, DueAt = ?, Status = ?, UpdatedAt = SYSUTCDATETIME() WHERE ComplaintId = ?",
                  [priority, due_at, status, complaint_id])

    def set_status(self, complaint_id: int, status: str, resolution_note: str | None) -> None:
        if status == "Resolved":
            self._run("UPDATE dbo.Complaints SET Status = ?, ResolvedAt = SYSUTCDATETIME(), ResolutionNote = ?, UpdatedAt = SYSUTCDATETIME() "
                      "WHERE ComplaintId = ?", [status, resolution_note, complaint_id])
        else:
            self._run("UPDATE dbo.Complaints SET Status = ?, UpdatedAt = SYSUTCDATETIME() WHERE ComplaintId = ?", [status, complaint_id])

    def has_feedback(self, complaint_id: int) -> bool:
        return self._one("SELECT 1 AS x FROM dbo.Feedback WHERE ComplaintId = ?", [complaint_id]) is not None

    def add_feedback(self, complaint_id: int, student_id: int, rating: int, comment: str) -> None:
        self._run("INSERT INTO dbo.Feedback (ComplaintId, StudentId, Rating, Comment) VALUES (?, ?, ?, ?)",
                  [complaint_id, student_id, rating, comment or None])

    def count_attachments(self, complaint_id: int) -> int:
        return self._one("SELECT COUNT(*) FROM dbo.Attachments WHERE ComplaintId = ?", [complaint_id])[0]

    def add_attachment(self, *, complaint_id, blob_name, original_name, content_type, size, uploaded_by) -> int:
        sql = ("INSERT INTO dbo.Attachments (ComplaintId, BlobName, OriginalName, ContentType, SizeBytes, UploadedBy) "
               "OUTPUT INSERTED.AttachmentId VALUES (?, ?, ?, ?, ?, ?)")
        return self._one(sql, [complaint_id, blob_name, original_name, content_type, size, uploaded_by])[0]

    # ----------------------------------------------------- duplicate detection
    def recent_open(self, days: int) -> list[dict]:
        """Open complaints from the last `days` days (at most 500), used to look for look-alikes."""
        sql = ("SELECT TOP 500 Reference, Title, Description, Location, Status FROM dbo.Complaints "
               "WHERE Status <> 'Resolved' AND CreatedAt >= DATEADD(day, ?, SYSUTCDATETIME()) ORDER BY CreatedAt DESC")
        return [{"id": r.Reference, "title": r.Title, "description": r.Description, "location": r.Location, "status": r.Status}
                for r in self._all(sql, [-days])]

    # ----------------------------------------------------------- analytics
    def analytics_rows(self) -> list[dict]:
        sql = ("SELECT c.ComplaintId, cat.Name AS CategoryName, COALESCE(a.DepartmentId, cat.DepartmentId) AS DepartmentId, "
               "c.Priority, c.Status, c.CreatedAt, c.ResolvedAt, c.DueAt, c.IsEscalated "
               "FROM dbo.Complaints c JOIN dbo.Categories cat ON cat.CategoryId = c.CategoryId "
               "LEFT JOIN dbo.Assignments a ON a.ComplaintId = c.ComplaintId AND a.IsCurrent = 1")
        return [{"id": r.ComplaintId, "categoryName": r.CategoryName, "departmentId": r.DepartmentId, "priority": r.Priority,
                 "status": r.Status, "createdAt": r.CreatedAt, "resolvedAt": r.ResolvedAt, "dueAt": r.DueAt,
                 "isEscalated": bool(r.IsEscalated)} for r in self._all(sql)]

    def feedback_rows(self) -> list[dict]:
        sql = ("SELECT f.Rating, COALESCE(a.DepartmentId, cat.DepartmentId) AS DepartmentId FROM dbo.Feedback f "
               "JOIN dbo.Complaints c ON c.ComplaintId = f.ComplaintId JOIN dbo.Categories cat ON cat.CategoryId = c.CategoryId "
               "LEFT JOIN dbo.Assignments a ON a.ComplaintId = c.ComplaintId AND a.IsCurrent = 1")
        return [{"rating": r.Rating, "departmentId": r.DepartmentId} for r in self._all(sql)]

    # ---------------------------------------------------------- escalation
    def open_for_escalation(self) -> list[dict]:
        sql = "SELECT ComplaintId, Reference, Priority, Status, CreatedAt, DueAt FROM dbo.Complaints WHERE Status <> 'Resolved'"
        return [{"id": r.ComplaintId, "reference": r.Reference, "priority": r.Priority, "status": r.Status,
                 "createdAt": r.CreatedAt, "dueAt": r.DueAt} for r in self._all(sql)]

    def record_escalation(self, complaint_id: int, reason: str, details: str) -> bool:
        """True if this (complaint, reason) was new. False if it was escalated before: that is what prevents duplicates."""
        sql = ("INSERT INTO dbo.Escalations (ComplaintId, Reason, Details) SELECT ?, ?, ? "
               "WHERE NOT EXISTS (SELECT 1 FROM dbo.Escalations WHERE ComplaintId = ? AND Reason = ?)")
        try:
            return self._run(sql, [complaint_id, reason, details, complaint_id, reason]) == 1
        except Exception as err:  # noqa: BLE001
            if type(err).__name__ == "IntegrityError":  # two runs raced; the database's UNIQUE rule stopped the second
                return False
            raise

    def mark_escalated(self, complaint_id: int) -> None:
        self._run("UPDATE dbo.Complaints SET IsEscalated = 1, EscalatedAt = COALESCE(EscalatedAt, SYSUTCDATETIME()) WHERE ComplaintId = ?",
                  [complaint_id])
