"""consent-guard: check contact consent before any send, and list who is safe to mail.

Read-only compliance gate. Given a segment or a table, it splits contacts into mailable
(consent true) and blocked (consent false or missing), so a send never goes to a contact
who has not opted in.
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
import bskit.skill as sk  # noqa: E402
from bskit import report  # noqa: E402


def run(store, args):
    contacts = store.table("contact")
    if args.account:
        contacts = [c for c in contacts if c.get("accountid") == args.account]
    mailable = [c for c in contacts if c.get("consent") is True]
    blocked = [c for c in contacts if not c.get("consent")]
    text = "Consent guard over %d contact(s): %d mailable, %d blocked.\n\nMailable:\n%s\n\nBlocked (do not send):\n%s" % (
        len(contacts), len(mailable), len(blocked),
        report.table([{"id": c["id"], "name": c["name"], "email": c.get("email")} for c in mailable], ["id", "name", "email"]),
        report.table([{"id": c["id"], "name": c["name"], "email": c.get("email")} for c in blocked], ["id", "name", "email"]),
    )
    return {"text": text, "data": {"mailable": mailable, "blocked": blocked}}


def add_args(p):
    p.add_argument("--account", help="limit to contacts of one account id")


if __name__ == "__main__":
    sk.run_cli(run, "Check consent before a send.", add_args)
