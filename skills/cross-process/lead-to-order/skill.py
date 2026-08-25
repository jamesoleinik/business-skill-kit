"""lead-to-order: promote a qualified lead into an opportunity.

Cross-process bridge from marketing/sales development into the pipeline. For a qualified
lead it plans a new opportunity (and can create the account if the lead's company is not yet
an account). Dry-run-first; --commit applies. Idempotent by deterministic ids.
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
import bskit.skill as sk  # noqa: E402
from bskit import dryrun  # noqa: E402


def run(store, args):
    lead = store.get("lead", "id", args.lead)
    if not lead:
        return {"text": "No lead '%s'." % args.lead, "data": {"error": "not-found"}}
    if lead.get("status") != "qualified" and not args.force:
        return {"text": "Lead %s is %s, not qualified. Qualify it first or pass --force." % (lead["id"], lead.get("status")), "data": {"skipped": "not-qualified"}}

    plans = []
    acct = next((a for a in store.table("account") if (a.get("name") or "").lower() == (lead.get("company") or "").lower()), None)
    account_id = acct["id"] if acct else ("A-%s" % lead["id"])
    if not acct:
        plans.append(("account", store.plan_upsert("account", [{"id": account_id, "name": lead.get("company"), "industry": None, "revenue": None, "city": None, "owner": None, "erp_customer_id": None}], "id")))
    opp_id = "O-%s" % lead["id"]
    plans.append(("opportunity", store.plan_upsert("opportunity", [{
        "id": opp_id, "name": "%s opportunity" % lead.get("company"), "accountid": account_id,
        "stage": "qualify", "amount": lead.get("budget") or 0, "probability": 20,
        "closedate": args.closedate, "status": "open", "owner": lead.get("owner"),
        "days_since_activity": 0, "competitor": None,
    }], "id")))
    plans.append(("lead", store.plan_upsert("lead", [{"id": lead["id"], "status": "converted"}], "id")))

    lines = ["lead-to-order for %s (%s @ %s):" % (lead["id"], lead.get("name"), lead.get("company"))]
    for _, pl in plans:
        lines.append(dryrun.render_plan(pl))
    live = [pl for _, pl in plans if not dryrun.is_noop(pl)]
    if not live:
        lines.append("\nAlready converted; nothing to do.")
    elif args.commit:
        applied = sum(store.apply(pl)["applied"] for pl in live)
        lines.append("\nAPPLIED: %d change(s)." % applied)
    else:
        lines.append("\n(dry run; pass --commit to apply)")
    return {"text": "\n".join(lines), "data": {"lead": lead["id"], "account_id": account_id, "opportunity_id": opp_id, "plans": {n: pl for n, pl in plans}}}


def add_args(p):
    p.add_argument("--lead", required=True, help="qualified lead id")
    p.add_argument("--closedate", default="2026-12-31", help="target close date for the new opportunity")
    p.add_argument("--force", action="store_true", help="convert even if the lead is not qualified")


if __name__ == "__main__":
    sk.run_cli(run, "Promote a qualified lead into an opportunity.", add_args)
