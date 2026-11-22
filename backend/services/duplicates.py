"""Duplicate complaint detection with plain Python.

We compare the new text with open complaints from the last 30 days (the SQL query is in the repository).
Score = word overlap (Jaccard) + a bonus if the location is the same. Nothing is ever rejected: the app only warns.
"""
import re

STOP_WORDS = set("the and for with near from this that has have been since not please there their are was were its into out off all any".split(" "))


def _words(text: str) -> set[str]:
    text = re.sub(r"[^a-z0-9\s]", " ", (text or "").lower())
    return {w for w in text.split() if len(w) > 2 and w not in STOP_WORDS}


def find_duplicates(candidates: list[dict], title: str, description: str, location: str, limit: int = 3) -> list[dict]:
    """candidates: dicts with id (reference), title, description, location, status. Best matches first."""
    query = _words(f"{title} {description}")
    if len(query) < 3:
        return []
    found = []
    for c in candidates:
        if c["status"] == "Resolved":
            continue
        other = _words(f"{c['title']} {c['description']}")
        overlap = len(query & other)
        jaccard = overlap / (len(query) + len(other) - overlap or 1)
        same_location = bool(location) and c["location"] == location
        score = jaccard + (0.25 if same_location else 0)
        if jaccard >= 0.1 and score >= 0.3:
            found.append({
                "id": c["id"], "title": c["title"], "location": c["location"], "status": c["status"],
                "sameLocation": same_location, "similarity": round(min(0.99, score) * 100), "_score": score,
            })
    found.sort(key=lambda r: r["_score"], reverse=True)
    for item in found:
        del item["_score"]
    return found[:limit]
