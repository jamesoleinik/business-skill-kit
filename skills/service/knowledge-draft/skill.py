"""knowledge-draft: turn a resolved case into a draft knowledge article.

Writes a markdown draft to out/ for human review. It never publishes and never edits the
case. A draft is a file artifact, so re-running overwrites the same file deterministically.
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
import bskit.skill as sk  # noqa: E402
from bskit import config  # noqa: E402


def build_markdown(c):
    return "\n".join([
        "# %s" % c["title"],
        "",
        "Status: draft (from case %s, category %s)" % (c["id"], c.get("category")),
        "",
        "## Symptom",
        c.get("description") or "(describe the customer-reported symptom)",
        "",
        "## Resolution",
        "(summarize the steps that resolved case %s)" % c["id"],
        "",
        "## Applies to",
        "- Category: %s" % c.get("category"),
        "",
    ])


def run(store, args):
    c = store.get("case", "id", args.case)
    if not c:
        return {"text": "No case '%s'." % args.case, "data": {"error": "not-found"}}
    if c.get("status") != "resolved":
        return {"text": "Case %s is %s; draft knowledge only from resolved cases." % (c["id"], c.get("status")), "data": {"skipped": "not-resolved"}}
    md = build_markdown(c)
    path = os.path.join(config.out_dir(), "kb-draft-%s.md" % c["id"])
    if args.commit:
        with open(path, "w", encoding="utf-8") as f:
            f.write(md)
        text = "Wrote knowledge draft to %s" % path
    else:
        text = "Draft preview (pass --commit to write %s):\n\n%s" % (path, md)
    return {"text": text, "data": {"case": c["id"], "path": path, "markdown": md}}


def add_args(p):
    p.add_argument("--case", required=True, help="resolved case id")


if __name__ == "__main__":
    sk.run_cli(run, "Draft a knowledge article from a resolved case.", add_args)
