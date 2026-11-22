"""Automatic escalation. Used by the timer (every 6 hours) and by the admin's "Run check now" button.

Two reasons a complaint is escalated, using the same rules as the frontend:
  overdue  - it is still open after its target time (SLA by priority, see core/constants.py)
  critical - it is Critical priority and still open after CRITICAL_FLAG_HOURS (6 hours)

No duplicates: the Escalations table has a UNIQUE (ComplaintId, Reason) rule and record_escalation() only inserts
when that pair is new. So running the check twice, or the timer and the button at the same moment, is safe.
"""
from datetime import datetime, timezone

from core.constants import CRITICAL_FLAG_HOURS


def utc_now() -> datetime:
    """Naive UTC time, the same kind Azure SQL gives back for DATETIME2 columns."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def find_escalations(open_complaints: list[dict], now: datetime) -> list[dict]:
    """Pure function (no database): which open complaints need escalating right now?"""
    found = []
    for c in open_complaints:
        if c["status"] == "Resolved":
            continue
        if now > c["dueAt"]:
            late_hours = round((now - c["dueAt"]).total_seconds() / 3600, 1)
            found.append({"complaintId": c["id"], "reference": c["reference"], "status": c["status"], "reason": "overdue",
                          "details": f"Past its target time by about {late_hours} hours."})
        age_hours = (now - c["createdAt"]).total_seconds() / 3600
        if c["priority"] == "Critical" and age_hours > CRITICAL_FLAG_HOURS:
            found.append({"complaintId": c["id"], "reference": c["reference"], "status": c["status"], "reason": "critical",
                          "details": f"Critical complaint still open after {round(age_hours, 1)} hours."})
    return found


def run_escalation(repo, now: datetime | None = None) -> dict:
    """Finds complaints to escalate and records each one only once. Returns a small summary."""
    now = now or utc_now()
    open_complaints = repo.open_for_escalation()
    created, already = [], 0
    for item in find_escalations(open_complaints, now):
        if repo.record_escalation(item["complaintId"], item["reason"], item["details"]):
            repo.mark_escalated(item["complaintId"])
            repo.add_history(item["complaintId"], item["status"], f"Escalated ({item['reason']}): {item['details']}", None)
            created.append({"reference": item["reference"], "reason": item["reason"]})
        else:
            already += 1
    return {"checked": len(open_complaints), "newEscalations": len(created), "alreadyEscalated": already,
            "items": created, "ranAt": now.isoformat() + "Z"}
