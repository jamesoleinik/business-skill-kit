"""quote-flow: advance a won opportunity to a quote and a CRM sales order.

Writes are dry-run-first. For a won opportunity it ensures a won quote exists and a CRM
sales order is staged (pending, no ERP id yet). Handing the order to the ERP is the job of
the cross-process quote-to-cash skill. Idempotent.
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
import bskit.skill as sk  # noqa: E402
from bskit import dryrun  # noqa: E402


def run(store, args):
    opp = store.get("opportunity", "id", args.opp)
    if not opp:
        return {"text": "No opportunity '%s'." % args.opp, "data": {"error": "not-found"}}
    if opp.get("status") != "won":
        return {"text": "Opportunity %s is %s, not won; nothing to advance." % (opp["id"], opp.get("status")), "data": {"skipped": "not-won"}}
    quotes = store.query("quote", where=lambda r: r.get("opportunityid") == opp["id"])
    quote_plan = None
    if quotes:
        q = quotes[0]
        quote_plan = store.plan_upsert("quote", [{"id": q["id"], "status": "won", "amount": opp.get("amount")}], "id")
    orders = store.query("salesorder", where=lambda r: r.get("accountid") == opp.get("accountid") and (quotes and r.get("quoteid") == quotes[0]["id"]))
    if orders:
        so = orders[0]
        order_rec = {"id": so["id"], "amount": opp.get("amount"), "status": "pending"}
    else:
        order_rec = {"id": "S-%s" % opp["id"], "accountid": opp.get("accountid"), "quoteid": quotes[0]["id"] if quotes else None, "amount": opp.get("amount"), "status": "pending", "erp_order_id": None}
    order_plan = store.plan_upsert("salesorder", [order_rec], "id")
    lines = ["quote-flow for %s (%s):" % (opp["id"], opp.get("name"))]
    if quote_plan:
        lines.append(dryrun.render_plan(quote_plan))
    else:
        lines.append("No quote on file for this opportunity.")
    lines.append(dryrun.render_plan(order_plan))
    applied = 0
    if args.commit:
        for pl in [p for p in (quote_plan, order_plan) if p and not dryrun.is_noop(p)]:
            applied += store.apply(pl)["applied"]
        lines.append("APPLIED: %d change(s)." % applied)
    elif any(p and not dryrun.is_noop(p) for p in (quote_plan, order_plan)):
        lines.append("(dry run; pass --commit to apply)")
    return {"text": "\n".join(lines), "data": {"quote_plan": quote_plan, "order_plan": order_plan}}


def add_args(p):
    p.add_argument("--opp", required=True, help="won opportunity id")


if __name__ == "__main__":
    sk.run_cli(run, "Advance a won opportunity to quote and CRM sales order.", add_args)
