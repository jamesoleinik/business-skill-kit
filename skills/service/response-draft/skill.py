"""response-draft: draft a customer reply for a case, grounded in the case record.

Writes a plain-text draft to out/ for a human to review and send. It never sends and never
edits the case. Deterministic: re-running overwrites the same draft file.
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
import bskit.skill as sk  # noqa: E402
from bskit import config  # noqa: E402


def build_reply(c, contact):
    name = (contact or {}).get("name", "there")
    first = name.split(" ")[0] if name else "there"
    opener = {
        "billing": "Thanks for flagging the billing question.",
        "technical": "Thanks for the details on the issue you hit.",
        "how-to": "Happy to help with that.",
        "return": "Sorry the item arrived that way. We can help with a return.",
        "feature": "Thanks for the suggestion.",
    }.get(c.get("category"), "Thanks for reaching out.")
    return "\n".join([
        "Hi %s," % first,
        "",
        "%s Regarding case %s (%s):" % (opener, c["id"], c["title"]),
        "",
        "(Add the specific answer or next step here. Reference the resolution once confirmed.)",
        "",
        "We will keep this case updated until it is resolved.",
        "",
        "Best regards,",
        "Customer Service",
    ])


def run(store, args):
    c = store.get("case", "id", args.case)
    if not c:
        return {"text": "No case '%s'." % args.case, "data": {"error": "not-found"}}
    contact = store.get("contact", "id", c.get("contactid"))
    body = build_reply(c, contact)
    path = os.path.join(config.out_dir(), "reply-%s.txt" % c["id"])
    if args.commit:
        with open(path, "w", encoding="utf-8") as f:
            f.write(body)
        text = "Wrote reply draft to %s" % path
    else:
        text = "Reply preview (pass --commit to write %s):\n\n%s" % (path, body)
    return {"text": text, "data": {"case": c["id"], "path": path, "draft": body}}


def add_args(p):
    p.add_argument("--case", required=True, help="case id")


if __name__ == "__main__":
    sk.run_cli(run, "Draft a customer reply for a case.", add_args)
