"""case-summary: a grounded summary of a single case with its account and contact.

Read-only. Pulls the case plus its linked account and contact and suggests a next action
based on category and SLA. No writes.
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
import bskit.skill as sk  # noqa: E402

NEXT_ACTION = {
    "return": "hand to the ERP return/credit process (see service-return-to-erp).",
    "billing": "verify the invoice line items before responding.",
    "technical": "reproduce the issue and check the knowledge base.",
    "how-to": "reply with the relevant knowledge article.",
    "feature": "log the request and set expectations; no immediate fix.",
}


def run(store, args):
    c = store.get("case", "id", args.case)
    if not c:
        return {"text": "No case '%s'." % args.case, "data": {"error": "not-found"}}
    acct = store.get("account", "id", c.get("accountid"))
    contact = store.get("contact", "id", c.get("contactid"))
    nxt = NEXT_ACTION.get(c.get("category"), "review and assign an owner.")
    lines = [
        "Case %s: %s" % (c["id"], c["title"]),
        "Status %s | Priority %s | SLA %s | Open %sd | Category %s" % (c.get("status"), c.get("priority"), c.get("sla_status"), c.get("days_open"), c.get("category")),
        "Account: %s" % (acct["name"] if acct else c.get("accountid")),
        "Contact: %s <%s>" % ((contact or {}).get("name", c.get("contactid")), (contact or {}).get("email", "")),
        "",
        "Description: %s" % c.get("description"),
        "",
        "Suggested next action: %s" % nxt,
    ]
    return {"text": "\n".join(lines), "data": {"case": c, "account": acct, "contact": contact, "next_action": nxt}}


def add_args(p):
    p.add_argument("--case", required=True, help="case id")


if __name__ == "__main__":
    sk.run_cli(run, "Summarize a single case.", add_args)
