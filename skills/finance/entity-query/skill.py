"""entity-query: read any table with an explainable filter, the ERP/FnO way.

Read-only. The finance-layer read skill: it queries a data entity (any table in the store)
with field=value filters, optional sort and column projection, and always states the filter
it ran so the result is auditable.
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
import bskit.skill as sk  # noqa: E402
from bskit import report  # noqa: E402


def run(store, args):
    if args.entity not in store.tables:
        return {"text": "No entity '%s'. Known: %s" % (args.entity, ", ".join(sorted(store.tables))), "data": {"error": "unknown-entity"}}
    crit = sk.parse_pairs(args.where)
    where = (lambda r: all(r.get(k) == v for k, v in crit.items())) if crit else None
    order_by = (args.order_by, args.desc) if args.order_by else None
    rows = store.query(args.entity, where=where, top=args.top, order_by=order_by)
    cols = args.select.split(",") if args.select else (list(rows[0].keys()) if rows else ["id"])
    filt = ", ".join("%s=%s" % (k, v) for k, v in crit.items()) or "(none)"
    text = "entity %s | filter %s | %d row(s)\n%s" % (args.entity, filt, len(rows), report.table([{c: r.get(c) for c in cols} for r in rows], cols))
    return {"text": text, "data": {"entity": args.entity, "filter": crit, "count": len(rows), "rows": rows}}


def add_args(p):
    p.add_argument("--entity", required=True, help="data entity / table name")
    p.add_argument("--where", nargs="*", help="field=value filters")
    p.add_argument("--select", help="comma-separated columns")
    p.add_argument("--order-by", dest="order_by")
    p.add_argument("--desc", action="store_true")
    p.add_argument("--top", type=int, default=50)


if __name__ == "__main__":
    sk.run_cli(run, "Read a data entity with an explainable filter.", add_args)
