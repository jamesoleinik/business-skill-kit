"""opportunity-catchup: a fast standup summary of the open pipeline.

Read-only. Rolls up open opportunities by stage and owner, weights amount by probability
for a forecast number, and flags the ones that have gone quiet.
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
import bskit.skill as sk  # noqa: E402
from bskit import report  # noqa: E402


def run(store, args):
    opps = store.query("opportunity", where=lambda r: r.get("status") == "open")
    if args.owner:
        opps = [o for o in opps if o.get("owner") == args.owner]
    total = sum(o.get("amount") or 0 for o in opps)
    weighted = sum((o.get("amount") or 0) * (o.get("probability") or 0) / 100.0 for o in opps)
    by_stage = {}
    for o in opps:
        by_stage.setdefault(o.get("stage"), {"stage": o.get("stage"), "count": 0, "amount": 0})
        by_stage[o["stage"]]["count"] += 1
        by_stage[o["stage"]]["amount"] += o.get("amount") or 0
    stale = sorted([o for o in opps if (o.get("days_since_activity") or 0) >= args.stale_days], key=lambda o: -(o.get("days_since_activity") or 0))
    text = "Open pipeline: %d opp(s), $%d total, $%d weighted forecast.\n\nBy stage:\n%s\n\nStale (>= %dd no activity):\n%s" % (
        len(opps), total, int(weighted),
        report.table(sorted(by_stage.values(), key=lambda s: -s["amount"]), ["stage", "count", "amount"]),
        args.stale_days,
        report.table([{"id": o["id"], "name": o["name"], "days": o.get("days_since_activity"), "amount": o.get("amount")} for o in stale], ["id", "name", "days", "amount"]),
    )
    return {"text": text, "data": {"count": len(opps), "total": total, "weighted": round(weighted, 2), "by_stage": list(by_stage.values()), "stale": stale}}


def add_args(p):
    p.add_argument("--owner", help="filter to a single owner")
    p.add_argument("--stale-days", dest="stale_days", type=int, default=30)


if __name__ == "__main__":
    sk.run_cli(run, "Summarize the open opportunity pipeline.", add_args)
