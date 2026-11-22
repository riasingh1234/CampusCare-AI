"""Creates the CampusCare tables and loads reference data in YOUR Azure SQL database.

    python scripts/init_db.py                 # tables + departments + categories
    python scripts/init_db.py --demo-users    # also creates demo admin, staff and student accounts

Requirements: az login done, your database user has db_ddladmin (see docs/azure-setup.md),
and `python scripts/check_config.py` passes. Safe to run more than once.
It prints the server and database name before changing anything and asks you to confirm.
"""
import argparse
import os
import re
import secrets
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
ROOT = BACKEND.parent
sys.path.insert(0, str(BACKEND))

from core.config import ConfigError, get_sql_settings, load_local_settings_file  # noqa: E402
from core.errors import ValidationError  # noqa: E402
from core.security import hash_password  # noqa: E402
from core.validation import check_password  # noqa: E402

# (name, email, role, department name or None, enrollment id or None)
DEMO_USERS = [
    ("Dr. Meera Kapoor", "meera.kapoor@campuscare.demo", "admin", None, None),
    ("Ravi Sharma", "ravi.sharma@campuscare.demo", "staff", "Electrical", None),
    ("Anil Verma", "anil.verma@campuscare.demo", "staff", "Plumbing & Water", None),
    ("Imran Khan", "imran.khan@campuscare.demo", "staff", "IT & Network", None),
    ("Sunita Devi", "sunita.devi@campuscare.demo", "staff", "Housekeeping", None),
    ("Deepak Joshi", "deepak.joshi@campuscare.demo", "staff", "Civil & Carpentry", None),
    ("Karan Malhotra", "karan.malhotra@campuscare.demo", "staff", "Security & Safety", None),
    ("Aarav Mehta", "aarav.mehta@campuscare.demo", "student", None, "ST-2201"),
    ("Ishita Rao", "ishita.rao@campuscare.demo", "student", None, "ST-2214"),
    ("Kabir Singh", "kabir.singh@campuscare.demo", "student", None, "ST-2230"),
    ("Neha Gupta", "neha.gupta@campuscare.demo", "student", None, "ST-2247"),
]


def split_batches(sql: str) -> list[str]:
    """Splits a script on lines that contain only GO (the SQL Server tools' batch separator)."""
    parts = re.split(r"^\s*GO\s*$", sql, flags=re.IGNORECASE | re.MULTILINE)
    return [p.strip() for p in parts if p.strip()]


def run_script(conn, path: Path) -> int:
    batches = split_batches(path.read_text(encoding="utf-8"))
    cur = conn.cursor()
    for batch in batches:
        cur.execute(batch)
    return len(batches)


def demo_password() -> tuple[str, bool]:
    """Returns (password, was_generated). Uses SEED_DEMO_PASSWORD if you set it, otherwise a random one."""
    chosen = os.environ.get("SEED_DEMO_PASSWORD", "").strip()
    if chosen:
        errors: dict = {}
        check_password(chosen, errors)
        if errors:
            raise ValidationError(f"SEED_DEMO_PASSWORD is not acceptable: {errors['password']}")
        return chosen, False
    return secrets.token_urlsafe(9) + "a1", True


def create_demo_users(conn) -> tuple[int, str, bool]:
    from repositories.users import UsersRepository

    password, generated = demo_password()
    password_hash = hash_password(password)  # one hash is reused for all demo accounts
    repo = UsersRepository(conn)
    cur = conn.cursor()
    created = 0
    for name, email, role, dept_name, enrollment in DEMO_USERS:
        if repo.get_by_email(email):
            continue
        dept_id = None
        if dept_name:
            cur.execute("SELECT DepartmentId FROM dbo.Departments WHERE Name = ?", dept_name)
            row = cur.fetchone()
            if row is None:
                raise RuntimeError(f"Department '{dept_name}' not found. Run without --demo-users first to load seed.sql.")
            dept_id = row[0]
        repo.create_user(full_name=name, email=email, password_hash=password_hash, role=role,
                         department_id=dept_id, enrollment_id=enrollment)
        created += 1
    return created, password, generated


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--demo-users", action="store_true", help="create demo admin, staff and student accounts")
    parser.add_argument("--yes", action="store_true", help="skip the confirmation question")
    args = parser.parse_args()

    load_local_settings_file()
    try:
        sql = get_sql_settings()
        demo = demo_password() if args.demo_users else None  # fail early on a bad SEED_DEMO_PASSWORD
    except (ConfigError, ValidationError) as err:
        print(err)
        return 1

    print(f"This will create or update tables in database '{sql.database}' on server '{sql.server}'.")
    if not args.yes and input("Type yes to continue: ").strip().lower() != "yes":
        print("Cancelled. Nothing was changed.")
        return 1

    from core.azure_clients import sql_connection

    with sql_connection(autocommit=True) as conn:
        for name in ("schema.sql", "seed.sql"):
            count = run_script(conn, ROOT / "database" / name)
            print(f"Ran {name} ({count} batches).")
        if args.demo_users:
            created, password, generated = create_demo_users(conn)
            print(f"Demo users created: {created} (existing ones were left alone).")
            if created and generated:
                print(f"Demo password (shown once, not saved anywhere): {password}")
            elif created:
                print("Demo accounts use the password from SEED_DEMO_PASSWORD.")
        cur = conn.cursor()
        for table in ("Departments", "Categories", "Users"):
            cur.execute(f"SELECT COUNT(*) FROM dbo.{table}")  # table names above are fixed literals
            print(f"  {table}: {cur.fetchone()[0]} rows")
    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
