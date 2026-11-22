"""Feature 10: duplicate detection."""
import sys
import unittest
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.duplicates import find_duplicates  # noqa: E402
from tests.fakes import NOW, FakeComplaints  # noqa: E402

OPEN = [
    {"id": "CC-2026-0001", "title": "Tap leaking in washroom", "description": "The tap in the ground floor washroom of Block A leaks all day.",
     "location": "Academic Block A", "status": "Assigned"},
    {"id": "CC-2026-0002", "title": "Projector flickers", "description": "The projector in Room 305 keeps flickering during lectures.",
     "location": "Academic Block A", "status": "Submitted"},
    {"id": "CC-2026-0003", "title": "Tap leaking in washroom", "description": "The tap in the ground floor washroom of Block A leaks all day.",
     "location": "Academic Block A", "status": "Resolved"},
]


class DuplicateTests(unittest.TestCase):
    def test_similar_open_complaint_is_found(self):
        found = find_duplicates(OPEN, "Leaking tap in washroom", "The washroom tap on the ground floor of Block A is leaking.", "Academic Block A")
        self.assertEqual([f["id"] for f in found], ["CC-2026-0001"])
        self.assertTrue(found[0]["sameLocation"])
        self.assertGreater(found[0]["similarity"], 30)

    def test_resolved_complaints_are_ignored(self):
        found = find_duplicates(OPEN, "Tap leaking in washroom", "The tap in the ground floor washroom of Block A leaks all day.", "Academic Block A")
        self.assertNotIn("CC-2026-0003", [f["id"] for f in found])

    def test_unrelated_text_finds_nothing(self):
        self.assertEqual(find_duplicates(OPEN, "Library books missing", "Several reference books are missing from the shelves upstairs.", "Library"), [])

    def test_too_little_text_finds_nothing(self):
        self.assertEqual(find_duplicates(OPEN, "tap", "", ""), [])

    def test_result_has_no_personal_data(self):
        found = find_duplicates(OPEN, "Tap leaking in washroom", "The tap in the ground floor washroom leaks all day long.", "")
        self.assertEqual(set(found[0]), {"id", "title", "location", "status", "sameLocation", "similarity"})

    def test_only_recent_open_complaints_are_compared(self):
        repo = FakeComplaints()
        old = repo.create(reference="CC-2026-0001", title="Old", description="x" * 30, category_id=1, location="Library", priority="Low",
                          student_id=4, due_at=NOW, ai=None)
        repo.rows[0]["createdAt"] = NOW - timedelta(days=45)
        repo.create(reference="CC-2026-0002", title="New", description="y" * 30, category_id=1, location="Library", priority="Low",
                    student_id=4, due_at=NOW, ai=None)
        self.assertEqual([r["id"] for r in repo.recent_open(30)], ["CC-2026-0002"])
        self.assertTrue(old)


if __name__ == "__main__":
    unittest.main()
