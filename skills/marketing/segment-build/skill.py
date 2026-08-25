"""segment-build: compute a segment's membership from its definition and refresh the count.

Evaluates a small, safe definition language (field OP value, joined by 'and') against
accounts or contacts, reports the members, and proposes an updated membercount and status.
Writes are dry-run-first and idempotent.
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
import bskit.skill as sk  # noqa: E402
from bskit import dryrun, report  # noqa: E402

OPS = {
    "==": lambda a, b: str(a) == b,
    "!=": lambda a, b: str(a) != b,
    ">": lambda a, b: _num(a) > _num(b),
    "<": lambda a, b: _num(a) < _num(b),
    ">=": lambda a, b: _num(a) >= _num(b),
    "<=": lambda a, b: _num(a) <= _num(b),
}


def _num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return float("nan")


def match(rec, definition):
    for clause in [c.strip() for c in definition.split(" and ")]:
        if not clause:
            continue
        if clause == "consent":
            if not rec.get("consent"):
                return False
            continue
        for op in (">=", "<=", "!=", "==", ">", "<"):
            if op in clause:
                field, val = [s.strip() for s in clause.split(op, 1)]
                if not OPS[op](rec.get(field), val):
                    return False
                break
        else:
            return False
    return True


def run(store, args):
    seg = store.get("segment", "id", args.segment) or store.get("segment", "name", args.segment)
    if not seg:
        return {"text": "No segment '%s'." % args.segment, "data": {"error": "not-found"}}
    source = store.table(args.source)
    members = [r for r in source if match(r, seg.get("definition", ""))]
    rec = {"id": seg["id"], "membercount": len(members), "status": "published" if members else seg.get("status")}
    plan = store.plan_upsert("segment", [rec], "id")
    text = "Segment %s '%s' over %s: %d member(s) [%s]\n%s\n\n%s" % (
        seg["id"], seg.get("name"), args.source, len(members), seg.get("definition"),
        report.table([{"id": m.get("id"), "name": m.get("name")} for m in members], ["id", "name"]),
        dryrun.render_plan(plan),
    )
    if args.commit and not dryrun.is_noop(plan):
        store.apply(plan)
        text += "\nAPPLIED."
    elif not dryrun.is_noop(plan):
        text += "\n(dry run; pass --commit to apply)"
    return {"text": text, "data": {"segment": seg["id"], "members": members, "plan": plan}}


def add_args(p):
    p.add_argument("--segment", required=True, help="segment id or name")
    p.add_argument("--source", default="account", help="table to evaluate the definition against")


if __name__ == "__main__":
    sk.run_cli(run, "Build and refresh a segment's membership.", add_args)
