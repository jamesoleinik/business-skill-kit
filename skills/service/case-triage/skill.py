"""case-triage: rank the active case queue so agents work the right case next.

Read-only. Scores each active case on SLA status, priority, and age, and returns a sorted
work queue with the reason for each rank.
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
import bskit.skill as sk  # noqa: E402
from bskit import report  # noqa: E402

SLA_POINTS = {"breached": 50, "at_risk": 30, "ok": 0}
PRIORITY_POINTS = {"high": 30, "normal": 15, "low": 5}


def triage_score(c):
    reasons, score = [], 0
    sp = SLA_POINTS.get(c.get("sla_status"), 0)
    if sp:
        reasons.append("sla %s (+%d)" % (c.get("sla_status"), sp))
    score += sp
    pp = PRIORITY_POINTS.get(c.get("priority"), 0)
    if pp:
        reasons.append("priority %s (+%d)" % (c.get("priority"), pp))
    score += pp
    age = c.get("days_open") or 0
    if age >= 5:
        score += 15
        reasons.append("open %dd (+15)" % age)
    elif age >= 3:
        score += 8
        reasons.append("open %dd (+8)" % age)
    return score, reasons


def run(store, args):
    cases = store.query("case", where=lambda r: r.get("status") == "active")
    ranked = []
    for c in cases:
        sc, reasons = triage_score(c)
        ranked.append({"id": c["id"], "title": c["title"], "priority": c.get("priority"), "sla": c.get("sla_status"), "days": c.get("days_open"), "score": sc, "why": "; ".join(reasons)})
    ranked.sort(key=lambda r: r["score"], reverse=True)
    ranked = ranked[: args.top]
    text = "Case triage: %d active case(s), top %d:\n%s" % (len(cases), len(ranked), report.table(ranked, ["id", "title", "priority", "sla", "days", "score", "why"]))
    return {"text": text, "data": {"queue": ranked}}


def add_args(p):
    p.add_argument("--top", type=int, default=25)


if __name__ == "__main__":
    sk.run_cli(run, "Rank the active case queue.", add_args)
