"""records: read, query, and search business records with grounded, cited results.

The platform-layer read skill. Everything else builds on it. Read-only.
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
import bskit.skill as sk  # noqa: E402
from bskit import report  # noqa: E402


def run(store, args):
    if args.search:
        hits = store.search(args.search, tables=[args.table] if args.table else None)
        rows = [{"table": h["table"], "id": h["record"].get("id"), "name": h["record"].get("name") or h["record"].get("title") or ""} for h in hits[: args.top]]
        text = "Search '%s' matched %d record(s):\n%s" % (args.search, len(hits), report.table(rows, ["table", "id", "name"]))
        return {"text": text, "data": {"query": args.search, "count": len(hits), "hits": rows}}
    if not args.table:
        counts = [{"table": t, "rows": len(v)} for t, v in sorted(store.tables.items())]
        text = "Store tables:\n" + report.table(counts, ["table", "rows"])
        return {"text": text, "data": {"tables": counts}}
    where = None
    if args.where:
        crit = sk.parse_pairs(args.where)
        where = lambda r: all(r.get(k) == v for k, v in crit.items())  # noqa: E731
    rows = store.query(args.table, where=where, top=args.top, order_by=(args.order_by, args.desc) if args.order_by else None)
    cols = args.select.split(",") if args.select else (list(rows[0].keys()) if rows else ["id"])
    text = "%s: %d row(s)\n%s" % (args.table, len(rows), report.table([{c: r.get(c) for c in cols} for r in rows], cols))
    return {"text": text, "data": {"table": args.table, "count": len(rows), "rows": rows}}


def add_args(p):
    p.add_argument("--table")
    p.add_argument("--search")
    p.add_argument("--where", nargs="*", help="field=value filters")
    p.add_argument("--select", help="comma-separated columns")
    p.add_argument("--order-by", dest="order_by")
    p.add_argument("--desc", action="store_true")
    p.add_argument("--top", type=int, default=50)


if __name__ == "__main__":
    sk.run_cli(run, "Read, query, and search business records.", add_args)
