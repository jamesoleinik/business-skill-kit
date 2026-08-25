"""entity-edit: create or update a single record in any entity, dry-run-first.

The finance-layer write skill. Give it an entity, a key, and field=value pairs; it plans an
upsert against the store and applies only with --commit. Idempotent: re-running the same
edit is a no-op.
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
import bskit.skill as sk  # noqa: E402
from bskit import dryrun  # noqa: E402


def run(store, args):
    if args.entity not in store.tables:
        return {"text": "No entity '%s'. Known: %s" % (args.entity, ", ".join(sorted(store.tables))), "data": {"error": "unknown-entity"}}
    fields = sk.parse_pairs(args.set)
    if args.key not in fields:
        if not args.id:
            return {"text": "Provide the key value via --id or in --set %s=..." % args.key, "data": {"error": "no-key"}}
        fields[args.key] = sk.coerce(args.id)
    if len(fields) <= 1:
        return {"text": "Nothing to set beyond the key. Pass --set field=value.", "data": {"error": "no-fields"}}
    plan = store.plan_upsert(args.entity, [fields], args.key)
    text = dryrun.render_plan(plan)
    if args.commit and not dryrun.is_noop(plan):
        res = store.apply(plan)
        text += "\nAPPLIED: %d change(s)." % res["applied"]
    elif not dryrun.is_noop(plan):
        text += "\n(dry run; pass --commit to apply)"
    return {"text": text, "data": plan}


def add_args(p):
    p.add_argument("--entity", required=True, help="data entity / table name")
    p.add_argument("--key", default="id", help="key field for the upsert")
    p.add_argument("--id", help="key value if not included in --set")
    p.add_argument("--set", nargs="*", help="field=value changes")


if __name__ == "__main__":
    sk.run_cli(run, "Create or update a record, dry-run-first.", add_args)
