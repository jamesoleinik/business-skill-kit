"""agent-front: draft a Copilot Studio topic that calls a skill as a tool.

Read-only. Emits a topic spec (trigger phrases, the tool it calls, and the inputs it
collects) as a draft under out/. It never publishes an agent.
"""
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
import bskit.skill as sk  # noqa: E402
from bskit import config, report  # noqa: E402


def run(store, args):
    inputs = args.inputs.split(",") if args.inputs else ["record_id"]
    topic = {
        "topic": "Run %s" % args.skill,
        "trigger_phrases": ["run %s" % args.skill, "%s for" % args.skill.replace("-", " "), "help me %s" % args.skill.replace("-", " ")],
        "tool": {"name": args.skill, "kind": "skill"},
        "inputs": [i.strip() for i in inputs],
        "confirmation": "Show the plan and ask before any write.",
        "note": "Draft only. Review and build in Copilot Studio.",
    }
    out = os.path.join(config.out_dir(), "topic_%s.json" % args.skill.replace("-", "_"))
    with open(out, "w", encoding="utf-8") as f:
        json.dump(topic, f, indent=2)
    text = "Topic for skill '%s':\ntriggers: %s\ninputs: %s\nWrote %s" % (
        args.skill, report.bullets(topic["trigger_phrases"]), report.bullets(topic["inputs"]), out,
    )
    return {"text": text, "data": topic}


def add_args(p):
    p.add_argument("--skill", default="lead-qualify")
    p.add_argument("--inputs", help="comma-separated input names")


if __name__ == "__main__":
    sk.run_cli(run, "Draft a Copilot Studio topic that calls a skill.", add_args)
