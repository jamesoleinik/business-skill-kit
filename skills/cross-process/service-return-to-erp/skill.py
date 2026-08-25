"""service-return-to-erp: turn an approved product return into an ERP credit.

Cross-process bridge from Customer Service to ERP finance. For a resolved case in the
'return' category it plans an ERP return order and a credit invoice (negative amount) so the
customer is credited. Dry-run-first; --commit applies. Idempotent by deterministic ids.
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
import bskit.skill as sk  # noqa: E402
from bskit import dryrun  # noqa: E402


def run(store, args):
    case = store.get("case", "id", args.case)
    if not case:
        return {"text": "No case '%s'." % args.case, "data": {"error": "not-found"}}
    if case.get("category") != "return":
        return {"text": "Case %s is category '%s', not a return." % (case["id"], case.get("category")), "data": {"skipped": "not-return"}}
    if case.get("status") != "resolved":
        return {"text": "Case %s is %s; only resolved returns are credited." % (case["id"], case.get("status")), "data": {"skipped": "not-resolved"}}
    acct = store.get("account", "id", case.get("accountid"))
    customer_id = (acct or {}).get("erp_customer_id")
    if not customer_id:
        return {"text": "Account %s has no linked ERP customer; run master-data-sync first." % case.get("accountid"), "data": {"error": "no-erp-customer"}}
    n = case["id"].replace("K", "")
    ret_id = "E-R%s" % n
    credit_id = "N-R%s" % n
    amount = args.amount

    ret_plan = store.plan_upsert("erp_salesorder", [{
        "id": ret_id, "crm_order_id": None, "customer_id": customer_id,
        "amount": -abs(amount), "status": "return", "invoice_id": credit_id,
    }], "id")
    credit_plan = store.plan_upsert("erp_invoice", [{
        "id": credit_id, "erp_order_id": ret_id, "amount": -abs(amount),
        "status": "credit", "duedate": args.duedate,
    }], "id")

    lines = ["service-return-to-erp for case %s (%s, customer %s):" % (case["id"], case.get("title"), customer_id)]
    lines.append(dryrun.render_plan(ret_plan))
    lines.append(dryrun.render_plan(credit_plan))
    live = [pl for pl in (ret_plan, credit_plan) if not dryrun.is_noop(pl)]
    if not live:
        lines.append("\nCredit already recorded; nothing to do.")
    elif args.commit:
        applied = sum(store.apply(pl)["applied"] for pl in live)
        lines.append("\nAPPLIED: %d change(s)." % applied)
    else:
        lines.append("\n(dry run; pass --commit to apply)")
    return {"text": "\n".join(lines), "data": {"case": case["id"], "return_id": ret_id, "credit_id": credit_id, "return_plan": ret_plan, "credit_plan": credit_plan}}


def add_args(p):
    p.add_argument("--case", required=True, help="resolved return case id, e.g. K004")
    p.add_argument("--amount", type=float, default=100.0, help="credit amount (stored negative)")
    p.add_argument("--duedate", default="2026-09-30", help="credit note date")


if __name__ == "__main__":
    sk.run_cli(run, "Turn an approved return into an ERP credit.", add_args)
