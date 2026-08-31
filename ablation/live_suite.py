"""Generalized LIVE ablation suite: run several skills against a real Dataverse org.

This is the multi-skill generalization of live_ablation.py. For each skill spec it:

  1. reads the seeded rows for every table the skill needs, through the MCP server
     (read_query), filtered by the seed tag,
  2. maps the live Dataverse columns onto the field names the skill's Store expects
     (build a snapshot), pointing the harness at that snapshot (harness.set_store_path),
  3. runs the identical with-skill / without-skill conditions, judge, stats, and report.

Ground truth is derived from the seeded roles (e.g. the opted-in vs. non-consented contact,
the breached-high case), not from the skill's own output, so each assertion is an independent
acceptance test. The with condition (skill loaded) must produce the derived result; the
without condition (raw table rows, no procedure) cannot, and that gap is the ablation signal.

Every skill runs dry-run (no --commit); this never writes back to the live environment.
Nothing is hardcoded to an org: pass --url and --token-file (see live-agent/signin.py).

Usage (from repo root):
    python ablation/live_suite.py \
        --url https://<org>.crm.dynamics.com/api/mcp_preview \
        --token-file build-notes/<org>-token.json \
        --tag "zzz-bskit-seed" --n 3 --out ablation/reports/live-suite.md
Optionally restrict to some skills: --only consent-guard,case-triage
"""
import argparse
import datetime
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


def _as_bool(v):
    return v in (True, 1, "1", "true", "True")


def _as_int(v, default=0):
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def _days_since(iso):
    if not iso:
        return 0
    try:
        d = datetime.datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
        if d.tzinfo is None:
            d = d.replace(tzinfo=datetime.timezone.utc)
        now = datetime.datetime.now(datetime.timezone.utc)
        return max(0, (now - d).days)
    except ValueError:
        return 0


_PRIORITY = {1: "high", 2: "normal", 3: "low"}
_STATECODE = {0: "active", 1: "resolved", 2: "cancelled"}


# ---- live-column -> fixture-field maps (generic; no environment specifics) --------------

def _map_contact(r):
    return {
        "id": r["contactid"],
        "name": (" ".join(x for x in (r.get("firstname"), r.get("lastname")) if x)).strip(),
        "email": r.get("emailaddress1"),
        "consent": _as_bool(r.get("contact_bskit_consent")),
        "accountid": None,
    }


def _map_case(r):
    return {
        "id": r["incidentid"],
        "title": r.get("title"),
        "priority": _PRIORITY.get(_as_int(r.get("prioritycode"), 2), "normal"),
        "sla_status": r.get("incident_bskit_sla_status"),
        "category": r.get("incident_bskit_category"),
        "days_open": _days_since(r.get("createdon")),
        "status": _STATECODE.get(_as_int(r.get("statecode"), 0), "active"),
    }


# ---- role finders (ground truth from the seed) -----------------------------------------

def _by_needle(rows, field, needle):
    for r in rows:
        if needle.lower() in (r.get(field) or "").lower():
            return r["id"]
    raise SystemExit("no seeded row whose %s contains %r" % (field, needle))


def _assert_consent(by):
    contacts = by["contact"]
    optin = _by_needle(contacts, "name", "Optin")
    noconsent = _by_needle(contacts, "name", "Noconsent")
    return [
        # The skill must keep the non-consented contact OUT of the mailable list.
        {"level": "critical", "kind": "not_contains", "dataset": "mailable",
         "idfield": "id", "id": noconsent},
        # ...and keep the opted-in contact IN it.
        {"level": "critical", "kind": "field_equals", "dataset": "mailable",
         "idfield": "id", "id": optin, "field": "consent", "value": True},
        {"level": "expected", "kind": "count_min", "dataset": "blocked", "n": 1},
    ]


def _assert_triage(by):
    cases = by["case"]
    breach = _by_needle(cases, "title", "Breached")
    return [
        # Breached + high case must be worked first.
        {"level": "critical", "kind": "ranked_first", "dataset": "queue",
         "by": "score", "idfield": "id", "id": breach},
        # The queue must carry the derived SLA reason field the raw table lacks.
        {"level": "critical", "kind": "field_equals", "dataset": "queue",
         "idfield": "id", "id": breach, "field": "sla", "value": "breached"},
    ]


def _billing_case_id(by):
    for r in by["case"]:
        if r.get("category") == "billing":
            return r["id"]
    raise SystemExit("no seeded case with category 'billing'")


def _args_billing_case(by):
    return {"case": _billing_case_id(by)}


def _assert_summary(_by):
    # Next-action is derived from the case category (billing); the raw text cannot state it.
    return [{"level": "critical", "kind": "text_contains",
             "substr": "verify the invoice line items"}]


def _assert_response(_by):
    # The reply opener is category-specific (billing); a generic agent reply is not.
    return [{"level": "critical", "kind": "text_contains",
             "substr": "Thanks for flagging the billing question"}]


_INCIDENT_FETCH = {
    "table": "incident", "namefield": "title", "target": "case",
    "select": ["incidentid", "title", "prioritycode", "statecode",
               "incident_bskit_category", "incident_bskit_sla_status", "createdon"],
    "map": _map_case,
}


SPECS = {
    "consent-guard": {
        "skill": "skills/marketing/consent-guard/skill.py",
        "args": {"account": None},
        "fetch": [{
            "table": "contact", "namefield": "lastname", "target": "contact",
            "select": ["contactid", "firstname", "lastname", "emailaddress1",
                       "contact_bskit_consent"],
            "map": _map_contact,
        }],
        "with_datasets": {"mailable": "mailable", "blocked": "blocked"},
        "without": {"text": "Here is the contact list for the send.",
                    "datasets": {"mailable": {"source": "table", "table": "contact"},
                                 "blocked": {"source": "empty"}}},
        "assertions": _assert_consent,
    },
    "case-triage": {
        "skill": "skills/service/case-triage/skill.py",
        "args": {"top": 25},
        "fetch": [_INCIDENT_FETCH],
        "with_datasets": {"queue": "queue"},
        "without": {"text": "Here are the open cases.",
                    "datasets": {"queue": {"source": "table", "table": "case"}}},
        "assertions": _assert_triage,
    },
    "case-summary": {
        "skill": "skills/service/case-summary/skill.py",
        "args": {}, "args_builder": _args_billing_case,
        "fetch": [_INCIDENT_FETCH],
        "with_datasets": {},
        "without": {"text": "This case is about a billing question from the customer.",
                    "datasets": {}},
        "assertions": _assert_summary,
    },
    "response-draft": {
        "skill": "skills/service/response-draft/skill.py",
        "args": {}, "args_builder": _args_billing_case,
        "fetch": [_INCIDENT_FETCH],
        "with_datasets": {},
        "without": {"text": "Hi, thanks for reaching out about your issue. We will follow up.",
                    "datasets": {}},
        "assertions": _assert_response,
    },
}


def fetch_table(client, spec, tag):
    cols = ", ".join(spec["select"])
    q = "SELECT %s FROM %s WHERE %s LIKE '%s%%'" % (
        cols, spec["table"], spec["namefield"], tag.replace("'", "''"))
    res = client.tools_call("read_query", {"querytext": q})
    if res.get("result", {}).get("isError"):
        raise SystemExit("read_query failed for %s: %s" % (spec["table"], _text(res)))
    rows = json.loads(_text(res))
    return [spec["map"](r) for r in rows]


def _run_condition(runner, case_def, assertions, n):
    passes, scores, last = [], [], []
    for _ in range(n):
        artifact = runner(case_def)
        verdict = judge.evaluate(artifact, assertions)
        passes.append(verdict["passed"])
        scores.append(verdict["avg_score"])
        last = verdict["assertions"]
    return passes, scores, last


def run_skill(client, skill_id, spec, tag, n):
    by_target, snapshot_tables = {}, {}
    for f in spec["fetch"]:
        rows = fetch_table(client, f, tag)
        if not rows:
            raise SystemExit("no seeded rows for %s (%s); run live-agent/seed.py --seed first"
                             % (skill_id, f["table"]))
        by_target[f["target"]] = rows
        snapshot_tables[f["target"]] = rows
    assertions = spec["assertions"](by_target)
    snapshot = {"tables": snapshot_tables}
    run_args = dict(spec.get("args") or {})
    if spec.get("args_builder"):
        run_args.update(spec["args_builder"](by_target))

    fd, snap_path = tempfile.mkstemp(prefix="bskit-live-", suffix=".json")
    os.close(fd)
    with open(snap_path, "w", encoding="utf-8") as fh:
        json.dump(snapshot, fh)

    try:
        harness.set_store_path(snap_path)
        case_def = {
            "with": {"module": spec["skill"], "args": run_args,
                     "datasets": spec["with_datasets"]},
            "without": spec["without"],
        }
        wp, ws, wa = _run_condition(harness.run_with, case_def, assertions, n)
        op, os_, oa = _run_condition(harness.run_without, case_def, assertions, n)
    finally:
        harness.set_store_path(None)
        os.remove(snap_path)

    w = stats.summarize_runs(wp, ws, k=n)
    o = stats.summarize_runs(op, os_, k=n)
    delta = stats.two_proportion_delta(w["passes"], w["n"], o["passes"], o["n"])
    seeded = sum(len(v) for v in by_target.values())
    return {
        "skill": "%s (LIVE)" % skill_id, "with": w, "without": o, "delta": delta,
        "cases": [{
            "id": "live-%s (%d seeded row(s))" % (skill_id, seeded),
            "with_pass": all(wp), "without_pass": all(op),
            "with_assertions": wa, "without_assertions": oa,
        }],
    }


def run_live(url, token_file, tag, n, only):
    client = mcp_probe.McpClient(url, mcp_probe._load_token(token_file))
    client.initialize()
    ids = only or list(SPECS.keys())
    skills = [run_skill(client, sid, SPECS[sid], tag, n) for sid in ids]
    return {"mode": "live", "n": n, "skills": skills}


def main():
    p = argparse.ArgumentParser(description="Generalized live ablation suite.")
    p.add_argument("--url", required=True)
    p.add_argument("--token-file", required=True)
    p.add_argument("--tag", default="zzz-bskit-seed")
    p.add_argument("--n", type=int, default=3)
    p.add_argument("--only", help="comma-separated skill ids (default: all)")
    p.add_argument("--out", help="write the Markdown report here (else print)")
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    only = [s.strip() for s in args.only.split(",")] if args.only else None
    if only:
        unknown = [s for s in only if s not in SPECS]
        if unknown:
            raise SystemExit("unknown skill id(s): %s; known: %s"
                             % (unknown, list(SPECS.keys())))
    result = run_live(args.url, args.token_file, args.tag, args.n, only)
    if args.json:
        print(json.dumps(result, indent=2, default=str))
        return
    md = report_mod.render(result)
    if args.out:
        os.makedirs(os.path.dirname(args.out), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(md)
        print("wrote %s" % args.out)
    else:
        print(md)


if __name__ == "__main__":
    main()
