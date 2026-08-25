"""master-data-sync: keep CRM accounts and ERP customers in agreement.

Cross-process data-quality skill. It detects four conditions across account and
erp_customer: name drift, a missing back-link, an account with no ERP customer, and an
orphan ERP customer. It plans fixes for the first three (align name, set crm_account_id,
create and link an ERP customer stub) and flags orphans for a human. Dry-run-first;
--commit applies. Idempotent.
"""
import os
import re
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
import bskit.skill as sk  # noqa: E402
from bskit import dryrun  # noqa: E402


def run(store, args):
    accounts = store.table("account")
    erp = {c["id"]: c for c in store.table("erp_customer")}
    account_recs, erp_recs, flags = [], [], []

    for a in accounts:
        cid = a.get("erp_customer_id")
        if not cid:
            new_cid = "C-%s" % re.sub(r"\D", "", a["id"]).zfill(4)
            account_recs.append({"id": a["id"], "erp_customer_id": new_cid})
            erp_recs.append({"id": new_cid, "name": a["name"], "crm_account_id": a["id"], "creditlimit": 0})
            flags.append("account %s had no ERP customer -> create %s" % (a["id"], new_cid))
            continue
        c = erp.get(cid)
        if not c:
            erp_recs.append({"id": cid, "name": a["name"], "crm_account_id": a["id"], "creditlimit": 0})
            flags.append("account %s points to missing %s -> create it" % (a["id"], cid))
            continue
        if c.get("name") != a.get("name"):
            erp_recs.append({"id": cid, "name": a["name"]})
            flags.append("name drift %s: ERP '%s' -> '%s'" % (cid, c.get("name"), a.get("name")))
        if c.get("crm_account_id") != a["id"]:
            erp_recs.append({"id": cid, "crm_account_id": a["id"]})
            flags.append("back-link %s -> account %s" % (cid, a["id"]))

    linked_targets = {a.get("erp_customer_id") for a in accounts}
    for c in erp.values():
        if not c.get("crm_account_id") and c["id"] not in linked_targets:
            flags.append("orphan ERP customer %s ('%s') has no account (manual review)" % (c["id"], c.get("name")))

    # collapse multiple erp edits per id into one record
    merged = {}
    for r in erp_recs:
        merged.setdefault(r["id"], {"id": r["id"]}).update(r)
    erp_plan = store.plan_upsert("erp_customer", list(merged.values()), "id") if merged else None
    acct_plan = store.plan_upsert("account", account_recs, "id") if account_recs else None

    lines = ["master-data-sync: %d finding(s)." % len(flags)] + ["  - " + f for f in flags]
    for pl in (acct_plan, erp_plan):
        if pl:
            lines.append(dryrun.render_plan(pl))
    live = [pl for pl in (acct_plan, erp_plan) if pl and not dryrun.is_noop(pl)]
    if not live:
        lines.append("\nCRM and ERP master data already aligned.")
    elif args.commit:
        applied = sum(store.apply(pl)["applied"] for pl in live)
        lines.append("\nAPPLIED: %d change(s)." % applied)
    else:
        lines.append("\n(dry run; pass --commit to apply)")
    return {"text": "\n".join(lines), "data": {"flags": flags, "account_plan": acct_plan, "erp_plan": erp_plan}}


def add_args(p):
    return p


if __name__ == "__main__":
    sk.run_cli(run, "Align CRM accounts with ERP customers.", add_args)
