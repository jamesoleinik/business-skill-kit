"""model: propose and apply a table or column change as a reviewed migration.

Dry-run-first. `--add-column table:field=default` plans setting the field on every row
that lacks it; `--create-table name` plans an empty table. Applies only with --commit.
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
import bskit.skill as sk  # noqa: E402
from bskit import dryrun  # noqa: E402


def run(store, args):
    if args.create_table:
        exists = args.create_table in store.tables
        text = "Table '%s' already exists." % args.create_table if exists else "Plan: create empty table '%s'." % args.create_table
        if args.commit and not exists:
            store.tables.setdefault(args.create_table, [])
            store._save()
            text += "\nAPPLIED."
        return {"text": text, "data": {"op": "create-table", "table": args.create_table, "existed": exists}}
    if not args.add_column:
        return {"text": "Pass --add-column table:field=default or --create-table name.", "data": {"error": "no-op"}}
    table, rest = args.add_column.split(":", 1)
    field, default = rest.split("=", 1)
    default = sk.coerce(default)
    records = [{"id": r.get("id"), field: default} for r in store.table(table) if field not in r]
    plan = store.plan_upsert(table, records, "id")
    text = "Add column '%s' to %s (default=%r):\n%s" % (field, table, default, dryrun.render_plan(plan))
    if args.commit and not dryrun.is_noop(plan):
        res = store.apply(plan)
        text += "\nAPPLIED: %d row(s)." % res["applied"]
    elif not dryrun.is_noop(plan):
        text += "\n(dry run; pass --commit to apply)"
    return {"text": text, "data": plan}


def add_args(p):
    p.add_argument("--add-column", dest="add_column", help="table:field=default")
    p.add_argument("--create-table", dest="create_table", help="new table name")


if __name__ == "__main__":
    sk.run_cli(run, "Propose and apply a table or column model change.", add_args)
