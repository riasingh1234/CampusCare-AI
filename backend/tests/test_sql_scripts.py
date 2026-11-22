import re
import sys
import unittest
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(BACKEND / "scripts"))

from init_db import split_batches  # noqa: E402

DB = BACKEND.parent / "database"


class SqlScriptTests(unittest.TestCase):
    def test_split_batches(self):
        self.assertEqual(split_batches("A;\nGO\nB;\n  go  \nC;"), ["A;", "B;", "C;"])

    def test_scripts_have_batches(self):
        for name in ("schema.sql", "seed.sql"):
            self.assertGreaterEqual(len(split_batches((DB / name).read_text())), 3)

    def test_seed_contains_no_users_or_credentials(self):
        code = re.sub(r"--.*", "", (DB / "seed.sql").read_text()).lower()  # ignore comments
        self.assertNotIn("dbo.users", code)
        self.assertNotIn("password", code)

    def test_every_expected_table_is_created(self):
        schema = (DB / "schema.sql").read_text()
        for table in ("Users", "Departments", "Complaints", "Assignments", "StatusHistory", "Feedback",
                      "Categories", "Attachments", "Escalations", "Notifications"):
            self.assertIn(f"CREATE TABLE dbo.{table} ", schema)


if __name__ == "__main__":
    unittest.main()
