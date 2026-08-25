"""lead-qualify: score inbound leads on fit and intent, then set score and status.

Reads leads, computes an explainable 0-100 score from budget, source, and company
signal, and proposes a status (qualified at or above the threshold, else nurture). Writes
are dry-run-first; pass --commit to apply.
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
import bskit.skill as sk  # noqa: E402
from bskit import dryrun, report  # noqa: E402

SOURCE_POINTS = {"referral": 30, "partner": 25, "event": 20, "web": 10}


def score_lead(lead):
    reasons = []
    score = 0
    budget = lead.get("budget") or 0
    if budget >= 200000:
        score += 40
        reasons.append("budget>=200k (+40)")
    elif budget >= 50000:
        score += 25
        reasons.append("budget>=50k (+25)")
    elif budget > 0:
        score += 10
        reasons.append("budget>0 (+10)")
    else:
        reasons.append("no budget (+0)")
    sp = SOURCE_POINTS.get(lead.get("source"), 0)
    if sp:
        reasons.append("source=%s (+%d)" % (lead.get("source"), sp))
    score += sp
    if lead.get("company"):
        score += 15
        reasons.append("named company (+15)")
    return min(score, 100), reasons


def run(store, args):
    leads = store.query("lead", where=(lambda r: r.get("status") == "new") if not args.all else None)
    records, detail = [], []
    for ld in leads:
        sc, reasons = score_lead(ld)
        status = "qualified" if sc >= args.threshold else "nurture"
        records.append({"id": ld["id"], "score": sc, "status": status})
        detail.append({"id": ld["id"], "name": ld.get("name"), "score": sc, "status": status, "why": "; ".join(reasons)})
    detail.sort(key=lambda d: d["score"], reverse=True)
    plan = store.plan_upsert("lead", records, "id")
    text = "Scored %d lead(s) at threshold %d:\n%s\n\n%s" % (
        len(detail), args.threshold, report.table(detail, ["id", "name", "score", "status", "why"]), dryrun.render_plan(plan),
    )
    if args.commit and not dryrun.is_noop(plan):
        res = store.apply(plan)
        text += "\nAPPLIED: %d change(s)." % res["applied"]
    elif not dryrun.is_noop(plan):
        text += "\n(dry run; pass --commit to apply)"
    return {"text": text, "data": {"scored": detail, "plan": plan}}


def add_args(p):
    p.add_argument("--threshold", type=int, default=50, help="qualify at or above this score")
    p.add_argument("--all", action="store_true", help="score all leads, not only new ones")


if __name__ == "__main__":
    sk.run_cli(run, "Score and qualify inbound leads.", add_args)
