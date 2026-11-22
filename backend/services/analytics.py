"""Admin analytics. The repository reads one row per complaint from Azure SQL; this file does the counting.

Keeping the counting in plain Python (instead of long SQL) makes it easy to read and to unit test.
"""
from datetime import datetime, timedelta

from core.constants import PRIORITIES, STATUSES


def _average(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 2) if values else None


def _hours(start: datetime, end: datetime) -> float:
    return (end - start).total_seconds() / 3600


def department_stats(rows: list[dict], feedback: list[dict], departments: list[dict]) -> list[dict]:
    result = []
    for dept in departments:
        mine = [r for r in rows if r["departmentId"] == dept["id"]]
        resolved = [r for r in mine if r["resolvedAt"]]
        met = [r for r in resolved if r["resolvedAt"] <= r["dueAt"]]
        ratings = [f["rating"] for f in feedback if f["departmentId"] == dept["id"]]
        result.append({
            "id": dept["id"], "name": dept["name"], "total": len(mine),
            "open": sum(1 for r in mine if r["status"] != "Resolved"),
            "resolved": len(resolved),
            "avgHours": _average([_hours(r["createdAt"], r["resolvedAt"]) for r in resolved]),
            "sla": round(100 * len(met) / len(resolved)) if resolved else None,
            "rating": _average(ratings),
        })
    return result


def daily_trend(rows: list[dict], now: datetime, days: int, tz_offset_minutes: int) -> list[dict]:
    """Reported and resolved per day for the last `days` days, in the viewer's own time zone."""
    shift = timedelta(minutes=tz_offset_minutes)
    today = (now + shift).date()
    reported: dict = {}
    resolved: dict = {}
    for r in rows:
        day = (r["createdAt"] + shift).date()
        reported[day] = reported.get(day, 0) + 1
        if r["resolvedAt"]:
            day = (r["resolvedAt"] + shift).date()
            resolved[day] = resolved.get(day, 0) + 1
    out = []
    for i in range(days - 1, -1, -1):
        d = today - timedelta(days=i)
        out.append({"label": f"{d.day} {d.strftime('%b')}", "reported": reported.get(d, 0), "resolved": resolved.get(d, 0)})
    return out


def build_analytics(rows: list[dict], feedback: list[dict], departments: list[dict], now: datetime,
                    tz_offset_minutes: int = 0, days: int = 30) -> dict:
    """rows: one dict per complaint (categoryName, departmentId, priority, status, createdAt, resolvedAt, dueAt, isEscalated)."""
    total = len(rows)
    resolved = [r for r in rows if r["resolvedAt"]]
    open_rows = [r for r in rows if r["status"] != "Resolved"]

    by_status = {s: 0 for s in STATUSES}
    by_priority = {p: 0 for p in PRIORITIES}
    by_category: dict = {}
    for r in rows:
        by_status[r["status"]] += 1
        by_priority[r["priority"]] += 1
        by_category[r["categoryName"]] = by_category.get(r["categoryName"], 0) + 1

    met = [r for r in resolved if r["resolvedAt"] <= r["dueAt"]]
    return {
        "summary": {
            "total": total,
            "open": len(open_rows),                       # pending = not resolved yet
            "resolved": by_status["Resolved"],
            "awaitingAssignment": by_status["Submitted"],
            "overdue": sum(1 for r in open_rows if now > r["dueAt"]),
            "criticalOpen": sum(1 for r in open_rows if r["priority"] == "Critical"),
            "escalated": sum(1 for r in rows if r["isEscalated"]),
            "resolvedPct": round(100 * by_status["Resolved"] / total) if total else 0,
            "avgHours": _average([_hours(r["createdAt"], r["resolvedAt"]) for r in resolved]),
            "sla": round(100 * len(met) / len(resolved)) if resolved else None,
            "rating": _average([f["rating"] for f in feedback]),
        },
        "byStatus": [{"name": s, "value": by_status[s]} for s in STATUSES],
        "byPriority": [{"name": p, "value": by_priority[p]} for p in PRIORITIES],
        "byCategory": sorted(({"name": n, "value": v} for n, v in by_category.items()), key=lambda x: (-x["value"], x["name"])),
        "departments": department_stats(rows, feedback, departments),
        "trend": daily_trend(rows, now, days, tz_offset_minutes),
    }
