"""Adds sample complaints so the demo has something to show (charts, overdue items, escalation).

    python scripts/seed_demo_complaints.py

Run it AFTER init_db.py --demo-users. It does nothing if complaints already exist, so it is safe to run twice.
Some sample complaints are deliberately old and still open: pressing "Run escalation check" on the admin overview
will then escalate them. Everything is written with the same repository code the app uses.
"""
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from core.config import ConfigError, get_sql_settings, load_local_settings_file  # noqa: E402
from core.constants import SLA_HOURS  # noqa: E402

# title, description, category, location, priority, student, age in hours, status, staff, hours to resolve, rating, comment
SAMPLES = [
    ("Ceiling fan sparking in Room 204", "The ceiling fan in Room 204 threw sparks and gave off a burning smell when switched on. Please inspect before the room is used again.",
     "Electrical fault", "Academic Block A", "Critical", "aarav", 30, "In Progress", "ravi", None, None, None),
    ("Wi-Fi keeps dropping in lecture hall", "The Wi-Fi in the Block B lecture hall disconnects every few minutes during classes, so online material will not load.",
     "Wi-Fi & computers", "Academic Block B", "Medium", "ishita", 70, "Assigned", "imran", None, None, None),
    ("Tap leaking in ground floor washroom", "The tap in the ground floor washroom of Block A has been leaking all week and the floor is always wet.",
     "Water & plumbing", "Academic Block A", "Medium", "kabir", 130, "Assigned", "anil", None, None, None),
    ("Garbage not collected near cafeteria", "Garbage bags have been piling up behind the central cafeteria for two days and there is a bad smell.",
     "Cleanliness & waste", "Central Cafeteria", "Low", "neha", 20, "Submitted", None, None, None, None),
    ("Stagnant water at Block B entrance", "Rainwater has collected near the Block B entrance and mosquitoes are breeding in it.",
     "Water & plumbing", "Academic Block B", "Medium", "aarav", 110, "Submitted", None, None, None, None),
    ("Streetlight not working near Main Gate", "The streetlight near the Main Gate has been off for three nights, so the road is dark after evening classes.",
     "Electrical fault", "Main Gate", "High", "ishita", 60, "Submitted", None, None, None, None),
    ("Broken bench in library garden", "Two benches in the library garden are broken and one has a sharp edge sticking out.",
     "Furniture & civil work", "Library", "Low", "kabir", 50, "Assigned", "deepak", None, None, None),
    ("CCTV camera offline at parking area", "The CCTV camera covering the parking area shows no picture since yesterday evening.",
     "Safety & security", "Parking Area", "High", "neha", 40, "In Progress", "karan", None, None, None),
    ("Classroom door will not lock", "The back door of Room 118 will not lock and the handle is loose. Equipment is left inside overnight.",
     "Furniture & civil work", "Academic Block A", "Medium", "aarav", 400, "Resolved", "deepak", 60, 4, "Fixed, thank you."),
    ("Loose power socket in Room 305", "The power socket near the projector in Room 305 is loose and cuts out when a plug is moved.",
     "Electrical fault", "Academic Block A", "Medium", "ishita", 340, "Resolved", "ravi", 20, 5, "Fixed the same day."),
    ("Missing dustbins in corridor", "The second floor corridor of Block B has no dustbins, so litter collects on the stairs.",
     "Cleanliness & waste", "Academic Block B", "Low", "kabir", 600, "Resolved", "sunita", 100, 4, "Bins are back, thanks."),
    ("Computers not booting in lab 2", "Six computers in lab 2 are not booting and the practical session had to be cancelled.",
     "Wi-Fi & computers", "Computer Lab Block", "High", "neha", 250, "Resolved", "imran", 30, 5, "Quick fix."),
    ("Drain overflowing behind hostel", "The drain behind Boys Hostel 1 is overflowing and water is entering the corridor.",
     "Water & plumbing", "Boys Hostel 1", "High", "aarav", 200, "Resolved", "anil", 80, None, None),
]


def main() -> int:
    load_local_settings_file()
    try:
        sql = get_sql_settings()
    except ConfigError as err:
        print(err)
        return 1
    print(f"This adds sample complaints to database '{sql.database}' on server '{sql.server}'.")
    if input("Type yes to continue: ").strip().lower() != "yes":
        print("Cancelled. Nothing was changed.")
        return 1

    from core.azure_clients import sql_connection
    from repositories.complaints import ComplaintsRepository

    with sql_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM dbo.Complaints")
        if cur.fetchone()[0] > 0:
            print("Complaints already exist, so nothing was added.")
            return 0

        def user_id(first_name):
            cur.execute("SELECT UserId, DepartmentId FROM dbo.Users WHERE Email LIKE ?", f"{first_name}.%@campuscare.demo")
            row = cur.fetchone()
            if row is None:
                raise RuntimeError(f"Demo user '{first_name}' not found. Run init_db.py --demo-users first.")
            return row.UserId, row.DepartmentId

        cur.execute("SELECT UserId FROM dbo.Users WHERE Role = 'admin' AND Email LIKE 'meera.%'")
        admin_id = cur.fetchone().UserId
        repo = ComplaintsRepository(conn)
        now = datetime.now(timezone.utc).replace(tzinfo=None)

        for title, desc, cat_name, location, priority, student, age_h, status, staff, solve_h, rating, comment in SAMPLES:
            cur.execute("SELECT CategoryId, DepartmentId FROM dbo.Categories WHERE Name = ?", cat_name)
            category = cur.fetchone()
            student_id, _ = user_id(student)
            created = now - timedelta(hours=age_h)
            ref = repo.next_reference(now.year)
            cid = repo.create(reference=ref, title=title, description=desc, category_id=category.CategoryId, location=location,
                              priority=priority, student_id=student_id, due_at=created + timedelta(hours=SLA_HOURS[priority]), ai=None)

            def history(state, note, who, at):
                cur.execute("INSERT INTO dbo.StatusHistory (ComplaintId, Status, Note, ChangedBy, ChangedAt) VALUES (?, ?, ?, ?, ?)",
                            cid, state, note, who, at)

            history("Submitted", "Complaint submitted.", student_id, created)
            resolved_at = None
            if status != "Submitted":
                staff_id, staff_dept = user_id(staff)
                cur.execute("INSERT INTO dbo.Assignments (ComplaintId, DepartmentId, StaffId, AssignedBy, AssignedAt) VALUES (?, ?, ?, ?, ?)",
                            cid, staff_dept, staff_id, admin_id, created + timedelta(hours=2))
                history("Assigned", f"Assigned. Priority: {priority}.", admin_id, created + timedelta(hours=2))
            if status in ("In Progress", "Resolved"):
                history("In Progress", "Work started.", staff_id, created + timedelta(hours=4))
            if status == "Resolved":
                resolved_at = created + timedelta(hours=solve_h)
                history("Resolved", "Problem fixed and checked.", staff_id, resolved_at)
            cur.execute("UPDATE dbo.Complaints SET Status = ?, CreatedAt = ?, UpdatedAt = ?, ResolvedAt = ?, ResolutionNote = ? WHERE ComplaintId = ?",
                        status, created, resolved_at or created, resolved_at,
                        "Problem fixed and checked." if resolved_at else None, cid)
            if rating:
                cur.execute("INSERT INTO dbo.Feedback (ComplaintId, StudentId, Rating, Comment, CreatedAt) VALUES (?, ?, ?, ?, ?)",
                            cid, student_id, rating, comment, resolved_at + timedelta(hours=3))
        print(f"Added {len(SAMPLES)} sample complaints.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
