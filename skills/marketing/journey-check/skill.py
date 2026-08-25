"""journey-check: pre-flight customer journeys before they go live.

Read-only. Flags journeys that are live with errors, drafts that are not ready, and any
journey whose segment is empty or missing. Returns a go/no-go list.
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
import bskit.skill as sk  # noqa: E402
from bskit import report  # noqa: E402


def run(store, args):
    segs = {s["id"]: s for s in store.table("segment")}
    rows = []
    for j in store.table("journey"):
        issues = []
        if j.get("errors"):
            issues.append("%d error(s)" % j["errors"])
        seg = segs.get(j.get("segmentid"))
        if not seg:
            issues.append("segment %s missing" % j.get("segmentid"))
        elif not seg.get("membercount"):
            issues.append("segment %s is empty" % seg["id"])
        if j.get("status") == "draft":
            issues.append("still draft")
        rows.append({"id": j["id"], "name": j.get("name"), "status": j.get("status"), "verdict": "no-go" if issues else "go", "issues": "; ".join(issues) or "none"})
    nogo = [r for r in rows if r["verdict"] == "no-go"]
    text = "Journey check: %d journey(s), %d no-go:\n%s" % (len(rows), len(nogo), report.table(rows, ["id", "name", "status", "verdict", "issues"]))
    return {"text": text, "data": {"journeys": rows, "no_go": nogo}}


def add_args(p):
    return p


if __name__ == "__main__":
    sk.run_cli(run, "Pre-flight customer journeys.", add_args)
