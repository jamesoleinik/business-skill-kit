"""audit: report who changed what, and flag sensitive-field access.

Read-only. Summarizes the change log captured by write skills, and scans the store for
sensitive fields (email, credit limit, revenue, budget) so governance can see where they
live.
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
import bskit.skill as sk  # noqa: E402
from bskit import report  # noqa: E402

SENSITIVE = {"email", "creditlimit", "revenue", "budget"}


def run(store, args):
    changes = store.audit
    by_entity = {}
    for c in changes:
        by_entity[c.get("entity")] = by_entity.get(c.get("entity"), 0) + 1
    change_rows = [{"entity": e, "changes": n} for e, n in sorted(by_entity.items())]
    sens = []
    for t, rows in store.tables.items():
        if not rows:
            continue
        found = sorted(set(rows[0].keys()) & SENSITIVE)
        if found:
            sens.append({"table": t, "sensitive_fields": ", ".join(found), "rows": len(rows)})
    lines = ["Change log: %d entr(ies)." % len(changes)]
    if change_rows:
        lines.append(report.table(change_rows, ["entity", "changes"]))
    lines.append("\nSensitive-field scan:")
    lines.append(report.table(sens, ["table", "sensitive_fields", "rows"]))
    return {"text": "\n".join(lines), "data": {"changes": changes, "sensitive": sens}}


if __name__ == "__main__":
    sk.run_cli(run, "Report the change log and scan for sensitive fields.")
