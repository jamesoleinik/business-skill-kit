"""End-to-end LIVE ablation for sales/lead-qualify against a real Dataverse environment.

This is the live counterpart to run_ablation.py. Instead of the committed fixture, it:

  1. reads the seeded leads from a live Dataverse org through the MCP server (read_query),
  2. normalizes them into the same snapshot shape the Store expects,
  3. points the ablation harness at that snapshot (harness.set_store_path),
  4. runs the identical with-skill / without-skill conditions, judge, stats, and report.

Ground truth is derived from the seed roles (Hot/Warm/Cold in the lead subject), not from
the skill's own scoring, so the assertions are an independent acceptance test: the with
condition must rank the hot lead first and set qualified/nurture statuses; the without
condition (raw table rows, no score, no status) cannot, and that gap is the ablation signal.

The skill runs dry-run (no --commit), so this never writes back to the live environment.
Nothing is hardcoded to an org: pass --url and --token-file (see live-agent/signin.py).

Usage (from repo root):
    python ablation/live_ablation.py \
        --url https://<org>.crm.dynamics.com/api/mcp_preview \
        --token-file build-notes/<org>-token.json \
        --tag "zzz-bskit-seed" --n 3 --out ablation/reports/live-lead-qualify.md
"""
import argparse
import importlib.util
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from ablation import harness, judge, report as report_mod, stats  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "mcp_probe", os.path.join(ROOT, "live-agent", "mcp_probe.py"))
mcp_probe = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mcp_probe)


def _text(res):
    try:
        return res["result"]["content"][0]["text"]
    except (KeyError, IndexError, TypeError):
        return json.dumps(res)


def fetch_leads(client, tag):
    q = ("SELECT leadid, subject, companyname, budgetamount FROM lead "
         "WHERE subject LIKE '%s%%'" % tag.replace("'", "''"))
    res = client.tools_call("read_query", {"querytext": q})
    if res.get("result", {}).get("isError"):
        raise SystemExit("read_query failed: %s" % _text(res))
    rows = json.loads(_text(res))
    if not rows:
        raise SystemExit("no seeded leads found for tag %r; run live-agent/seed.py --seed first" % tag)
    return rows


def build_snapshot(rows):
    """Map live Dataverse lead columns onto the skill's expected lead fields."""
    leads = []
    for r in rows:
        leads.append({
            "id": r["leadid"],
            "name": r.get("subject"),
            "budget": int(r.get("budgetamount") or 0),
            "company": r.get("companyname"),
            "source": None,          # not seeded; scores 0 from source, as intended
            "status": "new",         # raw table status; the skill derives qualified/nurture
        })
    return {"tables": {"lead": leads}}


def _role_id(rows, needle):
    for r in rows:
        if needle.lower() in (r.get("subject") or "").lower():
            return r["leadid"]
    raise SystemExit("could not find a seeded lead whose subject contains %r" % needle)


def build_assertions(rows):
    """Independent acceptance test derived from the seed roles, not the skill internals."""
    hot = _role_id(rows, "Hot")
    warm = _role_id(rows, "Warm")
    cold = _role_id(rows, "Cold")
    return [
        {"level": "critical", "kind": "ranked_first", "dataset": "scored",
         "by": "score", "idfield": "id", "id": hot},
        {"level": "critical", "kind": "field_equals", "dataset": "scored",
         "idfield": "id", "id": hot, "field": "status", "value": "qualified"},
        {"level": "critical", "kind": "field_equals", "dataset": "scored",
         "idfield": "id", "id": cold, "field": "status", "value": "nurture"},
        {"level": "expected", "kind": "field_equals", "dataset": "scored",
         "idfield": "id", "id": warm, "field": "status", "value": "nurture"},
    ]


def _run_condition(runner, case_def, assertions, n):
    passes, scores, last = [], [], []
    for _ in range(n):
        artifact = runner(case_def)
        verdict = judge.evaluate(artifact, assertions)
        passes.append(verdict["passed"])
        scores.append(verdict["avg_score"])
        last = verdict["assertions"]
    return passes, scores, last


def run_live(url, token_file, tag, n):
    client = mcp_probe.McpClient(url, mcp_probe._load_token(token_file))
    client.initialize()
    rows = fetch_leads(client, tag)
    snapshot = build_snapshot(rows)
    assertions = build_assertions(rows)

    fd, snap_path = tempfile.mkstemp(prefix="bskit-live-", suffix=".json")
    os.close(fd)
    with open(snap_path, "w", encoding="utf-8") as f:
        json.dump(snapshot, f)

    try:
        harness.set_store_path(snap_path)
        case_def = {
            "with": {"module": "skills/sales/lead-qualify/skill.py",
                     "args": {"threshold": 50, "all": True},
                     "datasets": {"scored": "scored"}},
            "without": {"text": "Here are the new leads from the queue.",
                        "datasets": {"scored": {"source": "table", "table": "lead"}}},
        }
        wp, ws, wa = _run_condition(harness.run_with, case_def, assertions, n)
        op, os_, oa = _run_condition(harness.run_without, case_def, assertions, n)
    finally:
        harness.set_store_path(None)
        os.remove(snap_path)

    w = stats.summarize_runs(wp, ws, k=n)
    o = stats.summarize_runs(op, os_, k=n)
    delta = stats.two_proportion_delta(w["passes"], w["n"], o["passes"], o["n"])
    skill = {
        "skill": "sales/lead-qualify (LIVE)", "with": w, "without": o, "delta": delta,
        "cases": [{
            "id": "live-lead-qualify (%d seeded leads)" % len(rows),
            "with_pass": all(wp), "without_pass": all(op),
            "with_assertions": wa, "without_assertions": oa,
        }],
    }
    return {"mode": "live", "n": n, "skills": [skill]}


def main():
    p = argparse.ArgumentParser(description="Live e2e ablation for lead-qualify.")
    p.add_argument("--url", required=True)
    p.add_argument("--token-file", required=True)
    p.add_argument("--tag", default="zzz-bskit-seed")
    p.add_argument("--n", type=int, default=3)
    p.add_argument("--out", help="write the Markdown report here (else print)")
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    result = run_live(args.url, args.token_file, args.tag, args.n)
    if args.json:
        print(json.dumps(result, indent=2, default=str))
        return
    md = report_mod.render(result)
    if args.out:
        os.makedirs(os.path.dirname(args.out), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(md)
        print("wrote %s" % args.out)
    else:
        print(md)


if __name__ == "__main__":
    main()
