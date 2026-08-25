"""reconcile: find and resolve duplicate or drifted records before a close.

Read-only report. Detects duplicate names within a table and name drift between a CRM
account and its linked ERP customer, then proposes the fix (it does not write).
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
import bskit.skill as sk  # noqa: E402


def run(store, args):
    findings = []
    seen = {}
    for r in store.table(args.table):
        name = (r.get("name") or r.get("title") or "").strip().lower()
        if not name:
            continue
        seen.setdefault(name, []).append(r.get("id"))
    for n, ids in seen.items():
        if len(ids) > 1:
            findings.append({"type": "duplicate", "table": args.table, "value": n, "ids": ids, "fix": "merge into %s" % ids[0]})
    erp = {c.get("id"): c for c in store.table("erp_customer")}
    for a in store.table("account"):
        cid = a.get("erp_customer_id")
        if cid and cid in erp and erp[cid].get("name") != a.get("name"):
            findings.append({"type": "name-drift", "account": a["id"], "crm_name": a["name"], "erp_customer": cid, "erp_name": erp[cid]["name"], "fix": "align erp_customer.name to '%s'" % a["name"]})
    lines = ["Reconcile: %d finding(s)." % len(findings)]
    for f in findings:
        if f["type"] == "duplicate":
            lines.append("  duplicate in %s: '%s' -> %s (%s)" % (f["table"], f["value"], f["ids"], f["fix"]))
        else:
            lines.append("  name-drift %s: CRM '%s' vs ERP '%s' [%s] -> %s" % (f["account"], f["crm_name"], f["erp_name"], f["erp_customer"], f["fix"]))
    return {"text": "\n".join(lines), "data": {"findings": findings}}


def add_args(p):
    p.add_argument("--table", default="account", help="table to scan for duplicates")


if __name__ == "__main__":
    sk.run_cli(run, "Find duplicate or drifted records and propose fixes.", add_args)
