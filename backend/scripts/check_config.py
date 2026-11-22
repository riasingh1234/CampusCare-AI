"""Checks your backend configuration. Run it before starting the app:

    python scripts/check_config.py

It is OFFLINE: it reads settings and validates their format. It does not contact Azure,
and it never prints values. Exit code 0 = all good, 1 = something to fix.
"""
import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from core.config import load_local_settings_file, validate_all  # noqa: E402


def git_status_of_local_settings() -> str | None:
    """Warns if local.settings.json could end up in git. Returns a message or None."""
    target = BACKEND / "local.settings.json"
    if not target.exists():
        return None
    try:
        tracked = subprocess.run(["git", "ls-files", "--error-unmatch", str(target)], cwd=BACKEND, capture_output=True)
        if tracked.returncode == 0:
            return "local.settings.json is TRACKED by git. Run: git rm --cached backend/local.settings.json  (then rotate anything that was in it)."
        ignored = subprocess.run(["git", "check-ignore", "-q", str(target)], cwd=BACKEND, capture_output=True)
        if ignored.returncode == 1:
            return "local.settings.json is NOT git-ignored. Add it to .gitignore before committing."
    except FileNotFoundError:
        return None  # git not installed; skip
    return None


def main() -> int:
    try:
        found = load_local_settings_file()
    except ValueError:
        print("local.settings.json is not valid JSON. Check for a missing comma or quote.")
        return 1
    print("Reading settings from local.settings.json" if found else
          "No local.settings.json found; using environment variables only (copy local.settings.example.json to create one).")

    failed = False
    for group, problems in validate_all().items():
        if problems:
            failed = True
            print(f"\n[FIX] {group}")
            for p in problems:
                print(f"      - {p}")
        else:
            print(f"[ OK] {group}")

    warning = git_status_of_local_settings()
    if warning:
        failed = True
        print(f"\n[FIX] git\n      - {warning}")

    print("\nThis check is offline. It does not prove your Azure permissions work." if not failed else
          "\nFix the items above and run the check again.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
