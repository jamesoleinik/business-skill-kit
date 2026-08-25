"""bulk-edit: propose and apply a reviewed set of record changes, dry-run-first.

Selects records by a filter, sets one or more fields, shows the plan, and applies it only
with --commit. Idempotent: re-running an applied change is a no-op.
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
import bskit.skill as sk  # noqa: E402
from bskit import dryrun  # noqa: E402


def run(store, args):
    crit = sk.parse_pairs(args.where)
    sets = sk.parse_pairs(args.set)
    if not sets:
        return {"text": "Nothing to set. Pass --set field=value.", "data": {"error": "no-set"}}
    where = lambda r: all(r.get(k) == v for k, v in crit.items())  # noqa: E731
    targets = store.query(args.table, where=where)
    records = []
    for r in targets:
        rec = {args.key: r.get(args.key)}
        rec.update(sets)
        records.append(rec)
    plan = store.plan_upsert(args.table, records, args.key)
    text = dryrun.render_plan(plan)
    if args.commit and not dryrun.is_noop(plan):
        res = store.apply(plan)
        text += "\nAPPLIED: %d change(s) written to the working copy." % res["applied"]
    elif not args.commit and not dryrun.is_noop(plan):
        text += "\n(dry run; pass --commit to apply)"
    return {"text": text, "data": plan}


def add_args(p):
    p.add_argument("--table", required=True)
    p.add_argument("--key", default="id")
    p.add_argument("--where", nargs="*", help="field=value selection filters")
    p.add_argument("--set", nargs="*", help="field=value changes to apply")


if __name__ == "__main__":
    sk.run_cli(run, "Propose and apply a reviewed set of record changes.", add_args)
