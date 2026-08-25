"""deal-risk: rank open opportunities by risk so reps know where to spend time.

Read-only. Scores each open opp on inactivity, a named competitor, low probability, and a
close date in the past, and explains every point.
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
import bskit.skill as sk  # noqa: E402
from bskit import report  # noqa: E402


def risk_score(o, today):
    reasons, score = [], 0
    dsa = o.get("days_since_activity") or 0
    if dsa >= 60:
        score += 40
        reasons.append("silent %dd (+40)" % dsa)
    elif dsa >= 30:
        score += 25
        reasons.append("silent %dd (+25)" % dsa)
    if o.get("competitor"):
        score += 20
        reasons.append("competitor %s (+20)" % o["competitor"])
    prob = o.get("probability") or 0
    if prob < 30:
        score += 20
        reasons.append("low probability %d%% (+20)" % prob)
    if today and (o.get("closedate") or "") < today:
        score += 20
        reasons.append("close date %s is past (+20)" % o.get("closedate"))
    return min(score, 100), reasons


def run(store, args):
    opps = store.query("opportunity", where=lambda r: r.get("status") == "open")
    ranked = []
    for o in opps:
        sc, reasons = risk_score(o, args.today)
        ranked.append({"id": o["id"], "name": o["name"], "amount": o.get("amount"), "risk": sc, "why": "; ".join(reasons) or "no flags"})
    ranked.sort(key=lambda r: r["risk"], reverse=True)
    at_risk = [r for r in ranked if r["risk"] >= args.threshold]
    text = "Deal risk for %d open opp(s); %d at or above threshold %d:\n%s" % (
        len(ranked), len(at_risk), args.threshold, report.table(ranked, ["id", "name", "amount", "risk", "why"]),
    )
    return {"text": text, "data": {"ranked": ranked, "at_risk": at_risk}}


def add_args(p):
    p.add_argument("--threshold", type=int, default=40)
    p.add_argument("--today", help="ISO date used to test overdue close dates, e.g. 2026-08-25")


if __name__ == "__main__":
    sk.run_cli(run, "Rank open opportunities by risk.", add_args)
