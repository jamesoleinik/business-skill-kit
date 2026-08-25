"""flow-scaffold: propose a Power Automate flow for a repeatable business step.

Read-only against business data. Emits a flow skeleton (trigger plus actions) as a draft
JSON under out/ so a maker can review and import it. It never deploys anything.
"""
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
import bskit.skill as sk  # noqa: E402
from bskit import config, report  # noqa: E402


def run(store, args):
    steps = args.steps.split(",") if args.steps else ["get_record", "condition", "update_record", "notify"]
    flow = {
        "name": args.name,
        "trigger": {"type": args.trigger, "table": args.table},
        "actions": [{"order": i + 1, "action": s.strip()} for i, s in enumerate(steps)],
        "note": "Draft only. Review and import in Power Automate.",
    }
    out = os.path.join(config.out_dir(), "flow_%s.json" % args.name.replace(" ", "_"))
    with open(out, "w", encoding="utf-8") as f:
        json.dump(flow, f, indent=2)
    text = "Drafted flow '%s' (%s on %s):\n%s\nWrote %s" % (
        args.name, args.trigger, args.table,
        report.bullets([a["action"] for a in flow["actions"]]), out,
    )
    return {"text": text, "data": flow}


def add_args(p):
    p.add_argument("--name", default="record-followup")
    p.add_argument("--trigger", default="when_a_record_is_updated")
    p.add_argument("--table", default="opportunity")
    p.add_argument("--steps", help="comma-separated action names")


if __name__ == "__main__":
    sk.run_cli(run, "Propose a Power Automate flow for a repeatable step.", add_args)
