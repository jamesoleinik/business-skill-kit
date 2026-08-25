"""account-brief: assemble a one-page brief for an account before a call.

Read-only. Pulls the account, its contacts, open opportunities, open cases, and any linked
ERP customer into a single grounded summary.
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
import bskit.skill as sk  # noqa: E402
from bskit import report  # noqa: E402


def run(store, args):
    acct = store.get("account", "id", args.account) or store.get("account", "name", args.account)
    if not acct:
        return {"text": "No account matched '%s'." % args.account, "data": {"error": "not-found"}}
    aid = acct["id"]
    contacts = store.query("contact", where=lambda r: r.get("accountid") == aid)
    opps = store.query("opportunity", where=lambda r: r.get("accountid") == aid and r.get("status") == "open")
    cases = store.query("case", where=lambda r: r.get("accountid") == aid and r.get("status") == "active")
    erp = store.get("erp_customer", "id", acct.get("erp_customer_id")) if acct.get("erp_customer_id") else None
    open_pipeline = sum(o.get("amount") or 0 for o in opps)
    lines = [
        "Account brief: %s (%s)" % (acct["name"], aid),
        "Industry %s | Revenue $%s | City %s | Owner %s" % (acct.get("industry"), acct.get("revenue"), acct.get("city"), acct.get("owner")),
        "ERP customer: %s" % (("%s credit $%s" % (erp["id"], erp.get("creditlimit"))) if erp else "not linked"),
        "",
        "Open pipeline: $%d across %d opp(s)" % (open_pipeline, len(opps)),
        report.table([{"id": o["id"], "name": o["name"], "stage": o.get("stage"), "amount": o.get("amount")} for o in opps], ["id", "name", "stage", "amount"]),
        "",
        "Contacts (%d):" % len(contacts),
        report.table([{"id": c["id"], "name": c["name"], "email": c.get("email"), "consent": c.get("consent")} for c in contacts], ["id", "name", "email", "consent"]),
        "",
        "Open cases (%d):" % len(cases),
        report.table([{"id": k["id"], "title": k["title"], "priority": k.get("priority"), "sla": k.get("sla_status")} for k in cases], ["id", "title", "priority", "sla"]),
    ]
    return {"text": "\n".join(lines), "data": {"account": acct, "erp_customer": erp, "contacts": contacts, "open_opportunities": opps, "open_cases": cases, "open_pipeline": open_pipeline}}


def add_args(p):
    p.add_argument("--account", required=True, help="account id or name")


if __name__ == "__main__":
    sk.run_cli(run, "Assemble a one-page account brief.", add_args)
