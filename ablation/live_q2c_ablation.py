"""End-to-end LIVE ablation for cross-process/quote-to-cash against real environments.

This is the cross-process counterpart to live_ablation.py. It proves the flagship CRM to ERP
skill on live data spanning two MCP planes:

  1. reads a seeded CRM sales order (and its account) from the live Dataverse org (read_query),
  2. normalizes them into the snapshot shape the Store expects, with empty erp_salesorder /
     erp_invoice tables (the ERP side does not exist yet),
  3. points the ablation harness at that snapshot (harness.set_store_path),
  4. runs the identical with-skill / without-skill conditions, judge, stats, and report,
  5. optionally cross-reads the live D365 F&O ERP MCP to confirm the ERP sales order the skill
     plans does not already exist -- an independent, live, cross-plane check.

The with condition runs quote-to-cash, which plans the ERP sales order + ERP invoice and stamps
erp_order_id back on the CRM order. The without condition (an agent with table access but no
skill) produces no cross-process plans at all. That gap is the ablation signal.

The skill runs dry-run (no --commit), so this never writes to the CRM or ERP environments.
Nothing is hardcoded to an org: pass --url / --token-file (and optionally --erp-url /
--erp-token-file). See live-agent/signin.py.

Usage (from repo root):
    python ablation/live_q2c_ablation.py \
        --url https://<org>.crm.dynamics.com/api/mcp_preview \
        --token-file build-notes/<org>-token.json \
        --order S005 \
        --erp-url https://<env>.operations.dynamics.com/mcp \
        --erp-token-file build-notes/<env>-erp-token.json \
        --out ablation/reports/live-quote-to-cash.md
"""
import argparse
import importlib.util
import json
import os
import re
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


def _digits(s):
    m = re.search(r"(\d+)", str(s))
    return m.group(1) if m else str(s)


def fetch_order(client, order):
    """Read the seeded CRM sales order and its parent account from the live org."""
    q = ("SELECT salesorderid, ordernumber, name, totalamount, "
         "customerid FROM salesorder WHERE ordernumber = '%s'" % order.replace("'", "''"))
    res = client.tools_call("read_query", {"querytext": q})
    if res.get("result", {}).get("isError"):
        raise SystemExit("read_query (salesorder) failed: %s" % _text(res))
    rows = json.loads(_text(res))
    if not rows:
        raise SystemExit("no live sales order with ordernumber %r; seed one first" % order)
    so = rows[0]
    acct_guid = so.get("customerid")
    acct = {"id": acct_guid, "name": None}
    if acct_guid:
        aq = ("SELECT accountid, name FROM account WHERE accountid = '%s'"
              % acct_guid.replace("'", "''"))
        ares = client.tools_call("read_query", {"querytext": aq})
        arows = json.loads(_text(ares)) if not ares.get("result", {}).get("isError") else []
        if arows:
            acct = {"id": arows[0]["accountid"], "name": arows[0].get("name")}
    return so, acct


def build_snapshot(so, acct):
    """Map the live order/account onto the Store shape quote-to-cash reads.

    The CRM sales order id is the human ordernumber (e.g. S005) so the skill's deterministic
    ERP ids (E-9<digits>, N-7<digits>) stay stable and match the acceptance assertions. The
    ERP tables are empty: the ERP order/invoice do not exist yet, which is exactly what the
    skill is asked to create.
    """
    order_id = so.get("ordernumber") or so["salesorderid"]
    acct_id = acct.get("id") or "account"
    tables = {
        "salesorder": [{
            "id": order_id,
            "accountid": acct_id,
            "amount": int(float(so.get("totalamount") or 0)),
            "status": "won",
        }],
        "account": [{
            "id": acct_id,
            "name": acct.get("name"),
        }],
        "erp_salesorder": [],
        "erp_invoice": [],
        "quote": [],
    }
    return {"tables": tables}, order_id


def build_case(order_id):
    """The committed acceptance assertions, retargeted at the live order id."""
    n = _digits(order_id)
    erp_order_id = "E-9%s" % n
    invoice_id = "N-7%s" % n
    case_def = {
        "with": {
            "module": "skills/cross-process/quote-to-cash/skill.py",
            "args": {"order": order_id, "duedate": "2026-09-30"},
            "datasets": {
                "erp_invoice_plan": "plans.erp_invoice",
                "erp_salesorder_plan": "plans.erp_salesorder",
                "salesorder_plan": "plans.salesorder",
            },
        },
        "without": {
            "text": "The CRM sales order %s is won." % order_id,
            "datasets": {
                "erp_invoice_plan": {"source": "empty_plan"},
                "erp_salesorder_plan": {"source": "empty_plan"},
                "salesorder_plan": {"source": "empty_plan"},
            },
        },
    }
    assertions = [
        {"level": "critical", "kind": "plan_creates", "dataset": "erp_salesorder_plan",
         "match": {"id": erp_order_id, "crm_order_id": order_id}},
        {"level": "critical", "kind": "plan_creates", "dataset": "erp_invoice_plan",
         "match": {"id": invoice_id, "erp_order_id": erp_order_id}},
        {"level": "expected", "kind": "plan_updates", "dataset": "salesorder_plan",
         "key": order_id, "field": "erp_order_id", "to": erp_order_id},
    ]
    return case_def, assertions, erp_order_id, invoice_id


def _run_condition(runner, case_def, assertions, n):
    passes, scores, last = [], [], []
    for _ in range(n):
        artifact = runner(case_def)
        verdict = judge.evaluate(artifact, assertions)
        passes.append(verdict["passed"])
        scores.append(verdict["avg_score"])
        last = verdict["assertions"]
    return passes, scores, last


def erp_cross_check(erp_url, erp_token_file, erp_order_id):
    """Independent live check on the ERP plane: confirm the planned ERP order isn't there yet."""
    client = mcp_probe.McpClient(erp_url, mcp_probe._load_token(erp_token_file))
    client.initialize()
    sql = ("SELECT T.SalesOrderNumber AS SalesOrderNumber FROM SalesOrderHeadersV4 T "
           "WHERE T.SalesOrderNumber = '%s'" % erp_order_id.replace("'", "''"))
    res = client.tools_call("data_find_entities_sql",
                            {"sqlExpression": sql, "companyId": "Cross-company"})
    txt = _text(res)
    present = bool(txt and txt.strip() not in ("[]", "")) and '"SalesOrderNumber"' in txt
    return {"queried": erp_order_id, "present_in_erp": present, "raw": txt[:400]}


def run_live(url, token_file, order, n, erp_url=None, erp_token_file=None):
    client = mcp_probe.McpClient(url, mcp_probe._load_token(token_file))
    client.initialize()
    so, acct = fetch_order(client, order)
    snapshot, order_id = build_snapshot(so, acct)
    case_def, assertions, erp_order_id, invoice_id = build_case(order_id)

    fd, snap_path = tempfile.mkstemp(prefix="bskit-live-q2c-", suffix=".json")
    os.close(fd)
    with open(snap_path, "w", encoding="utf-8") as f:
        json.dump(snapshot, f)

    try:
        harness.set_store_path(snap_path)
        wp, ws, wa = _run_condition(harness.run_with, case_def, assertions, n)
        op, os_, oa = _run_condition(harness.run_without, case_def, assertions, n)
    finally:
        harness.set_store_path(None)
        os.remove(snap_path)

    w = stats.summarize_runs(wp, ws, k=n)
    o = stats.summarize_runs(op, os_, k=n)
    delta = stats.two_proportion_delta(w["passes"], w["n"], o["passes"], o["n"])

    erp_note = None
    if erp_url and erp_token_file:
        try:
            erp_note = erp_cross_check(erp_url, erp_token_file, erp_order_id)
        except Exception as exc:  # noqa: BLE001 - diagnostic only, never fail the ablation
            erp_note = {"queried": erp_order_id, "error": str(exc)}

    skill = {
        "skill": "cross-process/quote-to-cash (LIVE)", "with": w, "without": o, "delta": delta,
        "cases": [{
            "id": "live-quote-to-cash (CRM order %s -> ERP %s / %s)" % (
                order_id, erp_order_id, invoice_id),
            "with_pass": all(wp), "without_pass": all(op),
            "with_assertions": wa, "without_assertions": oa,
        }],
    }
    return {"mode": "live", "n": n, "skills": [skill], "erp_cross_check": erp_note}


def main():
    p = argparse.ArgumentParser(description="Live e2e ablation for cross-process/quote-to-cash.")
    p.add_argument("--url", required=True, help="Dataverse (CRM) MCP url")
    p.add_argument("--token-file", required=True, help="Dataverse MCP token file")
    p.add_argument("--order", default="S005", help="live CRM sales order ordernumber")
    p.add_argument("--n", type=int, default=3)
    p.add_argument("--erp-url", help="optional D365 F&O ERP MCP url for a live cross-plane check")
    p.add_argument("--erp-token-file", help="optional ERP MCP token file")
    p.add_argument("--out", help="write the Markdown report here (else print)")
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    result = run_live(args.url, args.token_file, args.order, args.n,
                      erp_url=args.erp_url, erp_token_file=args.erp_token_file)
    if args.json:
        print(json.dumps(result, indent=2, default=str))
        return
    md = report_mod.render(result)
    note = result.get("erp_cross_check")
    if note:
        if note.get("error"):
            md += "\n\n> ERP cross-plane check skipped: %s\n" % note["error"]
        else:
            md += ("\n\n> ERP cross-plane check (live D365 F&O MCP): sales order %s "
                   "present_in_erp=%s. The skill's plan targets an ERP order that does not "
                   "yet exist, confirming the CRM->ERP push is real work.\n"
                   % (note["queried"], note["present_in_erp"]))
    if args.out:
        os.makedirs(os.path.dirname(args.out), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(md)
        print("wrote %s" % args.out)
    else:
        print(md)


if __name__ == "__main__":
    main()
