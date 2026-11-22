"""SQL for departments, categories and the people lists. Every query is parameterized."""
from core.errors import ConflictError


class ReferenceRepository:
    def __init__(self, conn):
        self.conn = conn

    def _all(self, sql, *params):
        cur = self.conn.cursor()
        cur.execute(sql, *params)
        return cur.fetchall()

    def _one(self, sql, *params):
        cur = self.conn.cursor()
        cur.execute(sql, *params)
        return cur.fetchone()

    # ---------------------------------------------------------------- lists
    def departments(self) -> list[dict]:
        return [{"id": r.DepartmentId, "name": r.Name} for r in self._all("SELECT DepartmentId, Name FROM dbo.Departments ORDER BY Name")]

    def categories(self) -> list[dict]:
        rows = self._all("SELECT CategoryId, Name, DepartmentId, DefaultPriority, Keywords FROM dbo.Categories ORDER BY CategoryId")
        return [{"id": r.CategoryId, "name": r.Name, "departmentId": r.DepartmentId, "defaultPriority": r.DefaultPriority,
                 "keywords": [k for k in (r.Keywords or "").split(",") if k]} for r in rows]

    def users_visible_to(self, user) -> list[dict]:
        """Names only (no emails). Admins see everyone. Others see staff and admins, plus the students they deal with."""
        base = "SELECT UserId, FullName, Role, DepartmentId FROM dbo.Users WHERE IsActive = 1 "
        if user.role == "admin":
            rows = self._all(base + "ORDER BY FullName")
        elif user.role == "staff":
            rows = self._all(base + "AND (Role IN ('staff', 'admin') OR UserId IN ("
                             "SELECT c.StudentId FROM dbo.Complaints c JOIN dbo.Assignments a ON a.ComplaintId = c.ComplaintId "
                             "WHERE a.IsCurrent = 1 AND a.StaffId = ?)) ORDER BY FullName", user.id)
        else:
            rows = self._all(base + "AND (Role IN ('staff', 'admin') OR UserId = ?) ORDER BY FullName", user.id)
        return [{"id": r.UserId, "name": r.FullName, "role": r.Role, "departmentId": r.DepartmentId} for r in rows]

    def get_user(self, user_id: int) -> dict | None:
        r = self._one("SELECT UserId, FullName, Role, DepartmentId, IsActive FROM dbo.Users WHERE UserId = ?", user_id)
        return None if r is None else {"id": r.UserId, "name": r.FullName, "role": r.Role, "departmentId": r.DepartmentId, "isActive": bool(r.IsActive)}

    def get_department(self, department_id: int) -> dict | None:
        r = self._one("SELECT DepartmentId, Name FROM dbo.Departments WHERE DepartmentId = ?", department_id)
        return None if r is None else {"id": r.DepartmentId, "name": r.Name}

    # ---------------------------------------------------------- departments
    def create_department(self, name: str) -> int:
        if self._one("SELECT 1 AS x FROM dbo.Departments WHERE LOWER(Name) = LOWER(?)", name):
            raise ConflictError("A department with this name already exists.")
        return self._one("INSERT INTO dbo.Departments (Name) OUTPUT INSERTED.DepartmentId VALUES (?)", name)[0]

    def rename_department(self, department_id: int, name: str) -> bool:
        if self._one("SELECT 1 AS x FROM dbo.Departments WHERE LOWER(Name) = LOWER(?) AND DepartmentId <> ?", name, department_id):
            raise ConflictError("A department with this name already exists.")
        cur = self.conn.cursor()
        cur.execute("UPDATE dbo.Departments SET Name = ? WHERE DepartmentId = ?", name, department_id)
        return cur.rowcount == 1

    def department_in_use(self, department_id: int) -> bool:
        sql = ("SELECT (SELECT COUNT(*) FROM dbo.Categories WHERE DepartmentId = ?) + (SELECT COUNT(*) FROM dbo.Users WHERE DepartmentId = ?) "
               "+ (SELECT COUNT(*) FROM dbo.Assignments WHERE DepartmentId = ?) + (SELECT COUNT(*) FROM dbo.Complaints WHERE AiDepartmentId = ?)")
        return self._one(sql, department_id, department_id, department_id, department_id)[0] > 0

    def delete_department(self, department_id: int) -> bool:
        cur = self.conn.cursor()
        cur.execute("DELETE FROM dbo.Departments WHERE DepartmentId = ?", department_id)
        return cur.rowcount == 1

    # ----------------------------------------------------------- categories
    def create_category(self, name, department_id, default_priority, keywords) -> int:
        if self._one("SELECT 1 AS x FROM dbo.Categories WHERE LOWER(Name) = LOWER(?)", name):
            raise ConflictError("A category with this name already exists.")
        sql = ("INSERT INTO dbo.Categories (Name, DepartmentId, DefaultPriority, Keywords) OUTPUT INSERTED.CategoryId VALUES (?, ?, ?, ?)")
        return self._one(sql, name, department_id, default_priority, ",".join(keywords))[0]

    def update_category(self, category_id, name, department_id, default_priority, keywords) -> bool:
        if self._one("SELECT 1 AS x FROM dbo.Categories WHERE LOWER(Name) = LOWER(?) AND CategoryId <> ?", name, category_id):
            raise ConflictError("A category with this name already exists.")
        cur = self.conn.cursor()
        cur.execute("UPDATE dbo.Categories SET Name = ?, DepartmentId = ?, DefaultPriority = ?, Keywords = ? WHERE CategoryId = ?",
                    name, department_id, default_priority, ",".join(keywords), category_id)
        return cur.rowcount == 1

    def category_in_use(self, category_id: int) -> bool:
        sql = "SELECT (SELECT COUNT(*) FROM dbo.Complaints WHERE CategoryId = ?) + (SELECT COUNT(*) FROM dbo.Complaints WHERE AiCategoryId = ?)"
        return self._one(sql, category_id, category_id)[0] > 0

    def delete_category(self, category_id: int) -> bool:
        cur = self.conn.cursor()
        cur.execute("DELETE FROM dbo.Categories WHERE CategoryId = ?", category_id)
        return cur.rowcount == 1
