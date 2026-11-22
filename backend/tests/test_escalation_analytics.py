"""Feature 7 (escalation logic) and Feature 8 (analytics numbers). No database needed."""
import sys
import unittest
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.analytics import build_analytics  # noqa: E402
from services.escalation import find_escalations, run_escalation  # noqa: E402
from tests.fakes import DEPARTMENTS, NOW, FakeComplaints  # noqa: E402

H = timedelta(hours=1)


def open_row(i, priority, age_hours, due_in_hours, status="Assigned"):
    return {"id": i, "reference": f"CC-2026-{i:04d}", "priority": priority, "status": status,
            "createdAt": NOW - age_hours * H, "dueAt": NOW + due_in_hours * H}


class EscalationRuleTests(unittest.TestCase):
    def reasons(self, rows):
        return sorted((f["complaintId"], f["reason"]) for f in find_escalations(rows, NOW))

    def test_overdue_complaint_is_escalated(self):
        self.assertEqual(self.reasons([open_row(1, "Medium", 100, -2)]), [(1, "overdue")])

    def test_not_yet_due_is_left_alone(self):
        self.assertEqual(self.reasons([open_row(1, "Medium", 10, 80)]), [])

    def test_critical_after_six_hours(self):
        self.assertEqual(self.reasons([open_row(1, "Critical", 7, 17)]), [(1, "critical")])

    def test_critical_under_six_hours_is_left_alone(self):
        self.assertEqual(self.reasons([open_row(1, "Critical", 5, 19)]), [])

    def test_critical_and_overdue_gives_two_reasons(self):
        self.assertEqual(self.reasons([open_row(1, "Critical", 30, -6)]), [(1, "critical"), (1, "overdue")])

    def test_resolved_is_never_escalated(self):
        self.assertEqual(self.reasons([open_row(1, "Critical", 30, -6, status="Resolved")]), [])


class EscalationRunTests(unittest.TestCase):
    def make_repo(self):
        repo = FakeComplaints()
        # One critical complaint that is 8 hours old and one low complaint that is long overdue.
        repo.create(reference="CC-2026-0001", title="Sparks", description="x" * 30, category_id=1, location="Library", priority="Critical",
                    student_id=4, due_at=NOW + 16 * H, ai=None)
        repo.rows[0].update(createdAt=NOW - 8 * H, status="In Progress")
        repo.create(reference="CC-2026-0002", title="Bin", description="y" * 30, category_id=4, location="Library", priority="Low",
                    student_id=4, due_at=NOW - 10 * H, ai=None)
        repo.rows[1]["createdAt"] = NOW - 200 * H
        return repo

    def test_first_run_escalates_and_records_history(self):
        repo = self.make_repo()
        result = run_escalation(repo, NOW)
        self.assertEqual((result["checked"], result["newEscalations"], result["alreadyEscalated"]), (2, 2, 0))
        self.assertTrue(all(r["isEscalated"] for r in repo.rows))
        notes = [h["note"] for h in repo.history]
        self.assertEqual(len(notes), 2)
        self.assertTrue(all(n.startswith("Escalated") for n in notes))
        self.assertTrue(all(h["byId"] is None for h in repo.history))  # recorded as made by the system

    def test_second_run_does_not_duplicate(self):
        repo = self.make_repo()
        run_escalation(repo, NOW)
        again = run_escalation(repo, NOW + 6 * H)
        self.assertEqual((again["newEscalations"], again["alreadyEscalated"]), (0, 2))
        self.assertEqual(len(repo.history), 2)
        self.assertEqual(len(repo.escalations), 2)

    def test_a_new_reason_later_is_still_recorded_once(self):
        repo = FakeComplaints()
        repo.create(reference="CC-2026-0001", title="Sparks", description="x" * 30, category_id=1, location="Library", priority="Critical",
                    student_id=4, due_at=NOW + 10 * H, ai=None)
        repo.rows[0]["createdAt"] = NOW - 8 * H
        self.assertEqual(run_escalation(repo, NOW)["newEscalations"], 1)       # critical
        later = run_escalation(repo, NOW + 12 * H)                             # now also overdue
        self.assertEqual((later["newEscalations"], later["alreadyEscalated"]), (1, 1))

    def test_nothing_to_do(self):
        self.assertEqual(run_escalation(FakeComplaints(), NOW)["newEscalations"], 0)


def row(i, category, dept, priority, status, created_h_ago, resolved_after_h=None, due_after_h=48, escalated=False):
    created = NOW - created_h_ago * H
    return {"id": i, "categoryName": category, "departmentId": dept, "priority": priority, "status": status, "createdAt": created,
            "resolvedAt": created + resolved_after_h * H if resolved_after_h is not None else None,
            "dueAt": created + due_after_h * H, "isEscalated": escalated}


class AnalyticsTests(unittest.TestCase):
    ROWS = [
        row(1, "Electrical fault", 1, "Critical", "Resolved", 100, resolved_after_h=10, due_after_h=24),   # on time
        row(2, "Electrical fault", 1, "High", "Resolved", 90, resolved_after_h=70, due_after_h=48),        # late
        row(3, "Water & plumbing", 2, "Medium", "In Progress", 20),
        row(4, "Water & plumbing", 2, "Medium", "Submitted", 5),
        row(5, "Wi-Fi & computers", 3, "Low", "Assigned", 300, due_after_h=168, escalated=True),          # overdue
    ]
    FEEDBACK = [{"rating": 5, "departmentId": 1}, {"rating": 3, "departmentId": 1}]

    def setUp(self):
        self.a = build_analytics(self.ROWS, self.FEEDBACK, DEPARTMENTS, NOW)

    def test_summary_counts(self):
        s = self.a["summary"]
        self.assertEqual((s["total"], s["open"], s["resolved"], s["awaitingAssignment"]), (5, 3, 2, 1))
        self.assertEqual((s["overdue"], s["criticalOpen"], s["escalated"], s["resolvedPct"]), (1, 0, 1, 40))

    def test_resolution_time_sla_and_rating(self):
        s = self.a["summary"]
        self.assertEqual(s["avgHours"], 40.0)    # (10 + 70) / 2
        self.assertEqual(s["sla"], 50)           # one of two resolved within target
        self.assertEqual(s["rating"], 4.0)

    def test_status_priority_category_counts(self):
        self.assertEqual({d["name"]: d["value"] for d in self.a["byStatus"]}, {"Submitted": 1, "Assigned": 1, "In Progress": 1, "Resolved": 2})
        self.assertEqual({d["name"]: d["value"] for d in self.a["byPriority"]}, {"Low": 1, "Medium": 2, "High": 1, "Critical": 1})
        self.assertEqual(self.a["byCategory"][0], {"name": "Electrical fault", "value": 2})

    def test_department_statistics(self):
        electrical = next(d for d in self.a["departments"] if d["name"] == "Electrical")
        self.assertEqual((electrical["total"], electrical["open"], electrical["resolved"], electrical["avgHours"], electrical["sla"], electrical["rating"]),
                         (2, 0, 2, 40.0, 50, 4.0))
        housekeeping = next(d for d in self.a["departments"] if d["name"] == "Housekeeping")
        self.assertEqual((housekeeping["total"], housekeeping["avgHours"], housekeeping["sla"], housekeeping["rating"]), (0, None, None, None))

    def test_trend_covers_30_days_and_counts_today(self):
        trend = self.a["trend"]
        self.assertEqual(len(trend), 30)
        self.assertEqual(trend[-1]["label"], "22 Nov")
        self.assertEqual(trend[-1]["reported"], 1)       # only row 4 (5 hours ago) was created today; row 3 was 20 hours ago = yesterday
        self.assertEqual(trend[-2]["reported"], 1)
        self.assertEqual(sum(t["reported"] for t in trend), 5)   # all five complaints are inside the 30-day window
        self.assertEqual(sum(t["resolved"] for t in trend), 2)

    def test_empty_data_does_not_crash(self):
        a = build_analytics([], [], DEPARTMENTS, NOW)
        self.assertEqual((a["summary"]["total"], a["summary"]["resolvedPct"], a["summary"]["avgHours"], a["summary"]["sla"]), (0, 0, None, None))


if __name__ == "__main__":
    unittest.main()
