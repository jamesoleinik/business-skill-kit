"""bc-record: list, create, or update a Business Central item, dry-run-first.

Reads bc_item by default. With --set it plans an upsert (create or update) and applies only
with --commit. Idempotent.
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
import bskit.skill as sk  # noqa: E402
from bskit import dryrun, report  # noqa: E402


def run(store, args):
    if not args.set:
        rows = store.table("bc_item")
        text = "bc_item: %d row(s)\n%s" % (len(rows), report.table(rows, ["id", "number", "description", "price", "inventory"]))
        return {"text": text, "data": {"rows": rows}}
    fields = sk.parse_pairs(args.set)
    if args.id:
        fields["id"] = args.id
    if "id" not in fields:
        return {"text": "Provide --id or --set id=... to create or update an item.", "data": {"error": "no-key"}}
    plan = store.plan_upsert("bc_item", [fields], "id")
    text = dryrun.render_plan(plan)
    if args.commit and not dryrun.is_noop(plan):
        res = store.apply(plan)
        text += "\nAPPLIED: %d change(s)." % res["applied"]
    elif not dryrun.is_noop(plan):
        text += "\n(dry run; pass --commit to apply)"
    return {"text": text, "data": plan}


def add_args(p):
    p.add_argument("--id", help="item id for create/update")
    p.add_argument("--set", nargs="*", help="field=value changes")


if __name__ == "__main__":
    sk.run_cli(run, "List, create, or update a Business Central item.", add_args)
