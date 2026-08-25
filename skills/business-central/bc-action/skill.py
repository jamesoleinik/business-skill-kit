"""bc-action: discover and dry-run a Business Central item action.

Read-first. Lists the bounded actions this kit understands (adjust-inventory, set-price),
shows exactly what an invocation would change, and applies only with --commit. Idempotent.
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
import bskit.skill as sk  # noqa: E402
from bskit import dryrun  # noqa: E402

ACTIONS = {
    "adjust-inventory": "change inventory by --by (delta)",
    "set-price": "set price to --value",
}


def run(store, args):
    if not args.action:
        lines = ["Available bc-item actions:"] + ["  %s: %s" % (k, v) for k, v in ACTIONS.items()]
        return {"text": "\n".join(lines), "data": {"actions": ACTIONS}}
    if args.action not in ACTIONS:
        return {"text": "Unknown action '%s'. Known: %s" % (args.action, ", ".join(ACTIONS)), "data": {"error": "unknown-action"}}
    item = store.get("bc_item", "id", args.id)
    if not item:
        return {"text": "No bc_item '%s'." % args.id, "data": {"error": "not-found"}}
    if args.action == "adjust-inventory":
        if args.by is None:
            return {"text": "adjust-inventory needs --by <delta>.", "data": {"error": "no-arg"}}
        new = (item.get("inventory") or 0) + int(args.by)
        rec = {"id": item["id"], "inventory": new}
    else:
        if args.value is None:
            return {"text": "set-price needs --value <price>.", "data": {"error": "no-arg"}}
        rec = {"id": item["id"], "price": int(args.value)}
    plan = store.plan_upsert("bc_item", [rec], "id")
    text = "bc-action %s on %s (%s):\n%s" % (args.action, item["id"], item.get("description"), dryrun.render_plan(plan))
    if args.commit and not dryrun.is_noop(plan):
        store.apply(plan)
        text += "\nAPPLIED."
    elif not dryrun.is_noop(plan):
        text += "\n(dry run; pass --commit to apply)"
    return {"text": text, "data": plan}


def add_args(p):
    p.add_argument("--action", help="action name; omit to list")
    p.add_argument("--id", help="bc_item id")
    p.add_argument("--by", help="delta for adjust-inventory")
    p.add_argument("--value", help="price for set-price")


if __name__ == "__main__":
    sk.run_cli(run, "Discover and dry-run a Business Central item action.", add_args)
