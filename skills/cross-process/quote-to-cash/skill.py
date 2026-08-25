"""quote-to-cash: drive a CRM sales order all the way to an ERP invoice.

The flagship cross-process skill. For a CRM sales order it ensures the linked quote is won,
pushes the order to the ERP (creates an ERP sales order and stamps erp_order_id back on the
CRM order), and raises the ERP invoice. Every step is a dry-run plan; --commit applies them
together. Fully idempotent: an order already pushed and invoiced yields no changes.
"""
import os
import re
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
import bskit.skill as sk  # noqa: E402
from bskit import dryrun  # noqa: E402


def _digits(s):
    m = re.search(r"(\d+)", str(s))
    return m.group(1) if m else str(s)


def run(store, args):
    so = store.get("salesorder", "id", args.order)
    if not so:
        return {"text": "No CRM sales order '%s'." % args.order, "data": {"error": "not-found"}}
    n = _digits(so["id"])
    erp_order_id = so.get("erp_order_id") or ("E-9%s" % n)
    invoice_id = "N-7%s" % n
    acct = store.get("account", "id", so.get("accountid"))
    existing_eso = store.get("erp_salesorder", "id", erp_order_id)
    existing_inv = store.get("erp_invoice", "id", invoice_id)
    customer_id = (existing_eso or {}).get("customer_id") or (acct or {}).get("erp_customer_id") or ("C-%s" % n)
    duedate = (existing_inv or {}).get("duedate") or args.duedate
    eso_status = (existing_eso or {}).get("status") or "invoiced"
    inv_status = (existing_inv or {}).get("status") or "open"

    plans = []
    if so.get("quoteid"):
        q = store.get("quote", "id", so["quoteid"])
        if q and q.get("status") != "won":
            plans.append(("quote", store.plan_upsert("quote", [{"id": q["id"], "status": "won"}], "id")))
    plans.append(("salesorder", store.plan_upsert("salesorder", [{"id": so["id"], "status": "submitted", "erp_order_id": erp_order_id}], "id")))
    plans.append(("erp_salesorder", store.plan_upsert("erp_salesorder", [{
        "id": erp_order_id, "crm_order_id": so["id"], "customer_id": customer_id,
        "amount": so.get("amount"), "status": eso_status, "invoice_id": invoice_id,
    }], "id")))
    plans.append(("erp_invoice", store.plan_upsert("erp_invoice", [{
        "id": invoice_id, "erp_order_id": erp_order_id, "amount": so.get("amount"),
        "status": inv_status, "duedate": duedate,
    }], "id")))

    lines = ["quote-to-cash for CRM order %s (account %s, $%s):" % (so["id"], so.get("accountid"), so.get("amount"))]
    for _, pl in plans:
        lines.append(dryrun.render_plan(pl))
    live = [pl for _, pl in plans if not dryrun.is_noop(pl)]
    if not live:
        lines.append("\nAlready fully invoiced; nothing to do.")
    elif args.commit:
        applied = sum(store.apply(pl)["applied"] for pl in live)
        lines.append("\nAPPLIED: %d change(s) across %d step(s)." % (applied, len(live)))
    else:
        lines.append("\n(dry run; pass --commit to apply the whole chain)")
    return {"text": "\n".join(lines), "data": {"order": so["id"], "erp_order_id": erp_order_id, "invoice_id": invoice_id, "plans": {name: pl for name, pl in plans}}}


def add_args(p):
    p.add_argument("--order", required=True, help="CRM sales order id, e.g. S005")
    p.add_argument("--duedate", default="2026-09-30", help="ERP invoice due date")


if __name__ == "__main__":
    sk.run_cli(run, "Drive a CRM sales order to an ERP invoice.", add_args)
