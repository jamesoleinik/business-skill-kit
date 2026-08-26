"""Run skill ablation over the JSON case files and write a report card.

Usage (from the repo root):
    python ablation/run_ablation.py                 # all cases, fixture mode, N=3
    python ablation/run_ablation.py --only lead-qualify --n 5
    python ablation/run_ablation.py --json           # print machine-readable result

Fixture mode is deterministic, so the N runs of a condition are identical; N still exercises
the pass@k / pass^k estimators and is the knob that matters once live mode introduces real
variance. Live mode (a real model through the Dataverse MCP server) is a planned extension
and is gated on interactive sign-in.

Reports are written to ablation/reports/ (gitignored). Nothing here reaches a real
environment; there are no org URLs, tenant or org IDs, or tokens anywhere in this module.
"""
import argparse
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from ablation import harness, judge, report as report_mod, stats  # noqa: E402


def _load_cases(only):
    paths = sorted(glob.glob(os.path.join(HERE, "cases", "*.json")))
    out = []
    for p in paths:
        slug = os.path.splitext(os.path.basename(p))[0]
        if only and slug != only:
            continue
        with open(p, encoding="utf-8") as f:
            out.append((slug, json.load(f)))
    return out


def _run_condition(runner, case_def, assertions, n):
    """Run one condition N times, judge each run, return (passes[], scores[], last_assertions)."""
    passes, scores, last = [], [], []
    for _ in range(n):
        artifact = runner(case_def)
        verdict = judge.evaluate(artifact, assertions)
        passes.append(verdict["passed"])
        scores.append(verdict["avg_score"])
        last = verdict["assertions"]
    return passes, scores, last


def run(only=None, n=3, mode="fixture"):
    if mode != "fixture":
        raise SystemExit("live mode is not wired yet; it is gated on interactive sign-in")
    skills = []
    for slug, spec in _load_cases(only):
        with_pass_all, with_score_all = [], []
        without_pass_all, without_score_all = [], []
        cases_out = []
        for case in spec["cases"]:
            case_def = {"with": spec["with"], "without": spec["without"]}
            case_def["with"] = dict(spec["with"], args=case.get("args", spec["with"].get("args")))
            case_def["without"] = spec["without"]
            assertions = case["assertions"]

            wp, ws, wa = _run_condition(harness.run_with, case_def, assertions, n)
            op, os_, oa = _run_condition(harness.run_without, case_def, assertions, n)
            with_pass_all += wp
            with_score_all += ws
            without_pass_all += op
            without_score_all += os_
            cases_out.append({
                "id": case["id"],
                "with_pass": all(wp),
                "without_pass": all(op),
                "with_assertions": wa,
                "without_assertions": oa,
            })

        w = stats.summarize_runs(with_pass_all, with_score_all, k=n)
        o = stats.summarize_runs(without_pass_all, without_score_all, k=n)
        delta = stats.two_proportion_delta(w["passes"], w["n"], o["passes"], o["n"])
        skills.append({"skill": spec["skill"], "with": w, "without": o, "delta": delta, "cases": cases_out})

    return {"mode": mode, "n": n, "skills": skills}


def main():
    p = argparse.ArgumentParser(description="Run skill ablation (with vs without).")
    p.add_argument("--only", help="run one case file by slug, e.g. lead-qualify")
    p.add_argument("--n", type=int, default=3, help="runs per condition (default 3)")
    p.add_argument("--mode", default="fixture", choices=["fixture", "live"])
    p.add_argument("--json", action="store_true", help="print JSON result instead of Markdown")
    p.add_argument("--out", help="write the Markdown report to this path")
    args = p.parse_args()

    result = run(only=args.only, n=args.n, mode=args.mode)
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
