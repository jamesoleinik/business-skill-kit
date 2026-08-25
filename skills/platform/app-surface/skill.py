"""app-surface: outline a Power Apps screen over a table's columns.

Read-only. Infers columns from the table and emits a simple screen spec (a gallery plus
an edit form) as a draft under out/. It never creates an app.
"""
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
import bskit.skill as sk  # noqa: E402
from bskit import config, report  # noqa: E402


def run(store, args):
    rows = store.table(args.table)
    cols = list(rows[0].keys()) if rows else ["id"]
    display = [c for c in cols if c != "id"][:6]
    spec = {
        "screen": "%s browse and edit" % args.table,
        "datasource": args.table,
        "gallery": {"fields": display[:3], "sort": display[0] if display else "id"},
        "form": {"fields": display, "key": "id", "mode": "review-then-save"},
        "note": "Draft only. Review and build in Power Apps.",
    }
    out = os.path.join(config.out_dir(), "app_%s.json" % args.table)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(spec, f, indent=2)
    text = "Screen for '%s' (%d columns):\ngallery: %s\nform: %s\nWrote %s" % (
        args.table, len(cols), report.bullets(spec["gallery"]["fields"]), report.bullets(spec["form"]["fields"]), out,
    )
    return {"text": text, "data": spec}


def add_args(p):
    p.add_argument("--table", default="account")


if __name__ == "__main__":
    sk.run_cli(run, "Outline a Power Apps screen over a table.", add_args)
