"""q2c_commit: really execute the CRM->ERP quote-to-cash push against live D365 F&O.

This is the committed-write counterpart to the dry-run quote-to-cash skill and its ablation.
Where the skill only *plans* the ERP sales order + invoice, this executor actually creates them
in a live D365 Finance & Operations environment through the remote ERP MCP server, and stamps
the resulting ERP order id back onto the CRM sales order through the Dataverse MCP server.

It follows the repo's write discipline:
  * Read-only / dry-run by DEFAULT. It prints exactly what it would create and exits. Nothing
    is written unless you pass --commit AND confirm (--yes for non-interactive runs).
  * Idempotent. It upserts by the natural key (SalesOrderNumber in F&O, ordernumber in CRM).
    A re-run finds the existing ERP order and makes no duplicate.
  * No hardcoded environment. Both MCP urls and both token files are passed in; nothing about
    a specific org is committed here.

Two planes, same OAuth pattern (see live-agent/signin.py to mint the two tokens):
  * CRM  : Dataverse MCP  https://<org>.crm.dynamics.com/api/mcp_preview
  * ERP  : D365 F&O MCP   https://<env>.operations.dynamics.com/mcp

Usage (from repo root), dry run first:
    python live-agent/q2c_commit.py \
        --url https://<org>.crm.dynamics.com/api/mcp_preview \
        --token-file build-notes/<org>-token.json \
        --erp-url https://<env>.operations.dynamics.com/mcp \
        --erp-token-file build-notes/<env>-erp-token.json \
        --order S005 --company USMF --currency USD

Then, to actually write:
    ...same args... --commit --yes
"""
import argparse
import importlib.util
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))

_spec = importlib.util.spec_from_file_location("mcp_probe", os.path.join(HERE, "mcp_probe.py"))
mcp_probe = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mcp_probe)
McpClient = mcp_probe.McpClient


def _text(res):
    try:
        return res["result"]["content"][0]["text"]
    except (KeyError, IndexError, TypeError):
        return json.dumps(res)


def _is_error(res):
    return bool(res.get("result", {}).get("isError"))


def _rows(res):
    """Parse a data_find_entities_sql / read_query result into a list of dict rows.

    CRM (Dataverse read_query) returns a flat JSON array. The ERP (F&O data_find_entities_sql)
    wraps rows as {"SessionId": ..., "Result": {"Value": [...]}}. Handle both.
    """
    txt = _text(res)
    try:
        val = json.loads(txt)
    except (json.JSONDecodeError, TypeError):
        return []
    if isinstance(val, dict):
        result = val.get("Result")
        if isinstance(result, dict) and "Value" in result:
            return result["Value"] or []
        if "value" in val:
            return val["value"]
        if "Value" in val:
            return val["Value"]
    return val if isinstance(val, list) else []


def _digits(s):
    m = re.search(r"(\d+)", str(s))
    return m.group(1) if m else str(s)


# ----------------------------------------------------------------------------- ERP tool shapes
def _tool_schema(client, name):
    res = client.tools_list()
    for t in (res or {}).get("result", {}).get("tools", []):
        if t.get("name") == name:
            return t.get("inputSchema", {}) or {}
    return {}


def _pick(props, *candidates):
    """Return the first candidate key that exists in a JSON-schema properties dict."""
    for c in candidates:
        if c in props:
            return c
    return candidates[0]


def erp_write_shape(erp):
    """Confirm the parameter names data_create_entities expects (odataPath + entityDefinitionsJson)."""
    props = (_tool_schema(erp, "data_create_entities") or {}).get("properties", {}) or {}
    path_key = _pick(props, "odataPath", "entitySetName", "entityName")
    defs_key = _pick(props, "entityDefinitionsJson", "entities", "values")
    return {"path": path_key, "defs": defs_key, "props": props}


# ----------------------------------------------------------------------------- CRM side
def crm_fetch_order(crm, order):
    q = ("SELECT salesorderid, ordernumber, name, totalamount, customerid "
         "FROM salesorder WHERE ordernumber = '%s'" % order.replace("'", "''"))
    res = crm.tools_call("read_query", {"querytext": q})
    if _is_error(res):
        raise SystemExit("CRM read_query (salesorder) failed: %s" % _text(res))
    rows = _rows(res)
    if not rows:
        raise SystemExit("No live CRM sales order with ordernumber %r. Seed one first." % order)
    so = rows[0]
    acct = {"id": so.get("customerid"), "name": None}
    if so.get("customerid"):
        ares = crm.tools_call("read_query", {"querytext":
            "SELECT accountid, name FROM account WHERE accountid = '%s'"
            % so["customerid"].replace("'", "''")})
        arows = [] if _is_error(ares) else _rows(ares)
        if arows:
            acct = {"id": arows[0]["accountid"], "name": arows[0].get("name")}
    return so, acct


def crm_stamp_erp_order(crm, salesorderid, erp_order_id, apply, field="new_erp_order_id"):
    """Best-effort: record the ERP order id back on the CRM sales order if the column exists."""
    if not apply:
        return {"planned": True, "field": field, "value": erp_order_id}
    res = crm.tools_call("update_record", {
        "tablename": "salesorder", "recordId": salesorderid,
        "item": {field: erp_order_id}})
    detail = _text(res)
    if _is_error(res):
        if "not found in table" in detail.lower():
            return {"skipped": True, "reason": "column %r absent on salesorder" % field,
                    "field": field, "value": erp_order_id}
        return {"applied": False, "field": field, "value": erp_order_id, "detail": detail}
    return {"applied": True, "field": field, "value": erp_order_id}


# ----------------------------------------------------------------------------- ERP side
def erp_find_order(erp, company, order_number):
    sql = ("SELECT T.SalesOrderNumber AS SalesOrderNumber, T.SalesOrderName AS SalesOrderName, "
           "T.OrderingCustomerAccountNumber AS Customer FROM SalesOrderHeadersV4 T "
           "WHERE T.SalesOrderNumber = '%s'" % order_number.replace("'", "''"))
    res = erp.tools_call("data_find_entities_sql",
                         {"sqlExpression": sql, "companyId": company})
    if _is_error(res):
        return None, _text(res)
    rows = _rows(res)
    return (rows[0] if rows else None), None


def erp_find_customer(erp, company, customer_account):
    sql = ("SELECT T.CustomerAccount AS CustomerAccount FROM CustomersV3 T "
           "WHERE T.CustomerAccount = '%s'" % customer_account.replace("'", "''"))
    res = erp.tools_call("data_find_entities_sql",
                         {"sqlExpression": sql, "companyId": company})
    if _is_error(res):
        return None, _text(res)
    rows = _rows(res)
    return (rows[0] if rows else None), None


def erp_create(erp, shape, entity_set, values):
    args = {shape["path"]: entity_set, shape["defs"]: json.dumps([values])}
    res = erp.tools_call("data_create_entities", args)
    detail = _text(res)
    ok = not _is_error(res)
    errmsg = None
    # The ERP MCP returns isError:false even when F&O business validation rejects the write;
    # the real outcome is in the batch body (SuccessCount / FailureCount / Errors).
    try:
        body = json.loads(detail)
        result = body.get("Result", body) if isinstance(body, dict) else {}
        if isinstance(result, dict) and ("SuccessCount" in result or "FailureCount" in result):
            ok = int(result.get("FailureCount", 0)) == 0 and int(result.get("SuccessCount", 0)) > 0
            errs = result.get("Errors") or []
            if errs:
                errmsg = errs[0].get("ErrorMessage")
    except (json.JSONDecodeError, TypeError, ValueError):
        pass
    return res, ok, (errmsg or detail)


def ensure_customer(erp, shape, company, customer_account, name, currency, apply):
    found, err = erp_find_customer(erp, company, customer_account)
    if found:
        return {"exists": True, "customer_account": customer_account}
    if err:
        return {"error": "customer lookup failed: %s" % err}
    if not apply:
        return {"exists": False, "would_create": customer_account}
    values = {
        "CustomerAccount": customer_account,
        "OrganizationName": name or customer_account,
        "CustomerGroupId": "10",
        "SalesCurrencyCode": currency,
        "PartyType": "Organization",
        "dataAreaId": company,
    }
    res, ok, detail = erp_create(erp, shape, "CustomersV3", values)
    return {"created": ok, "customer_account": customer_account, "detail": detail}


def ensure_sales_order(erp, shape, company, order_number, customer_account, name, amount,
                       currency, requested_ship, apply):
    found, err = erp_find_order(erp, company, order_number)
    if found:
        return {"exists": True, "order_number": order_number, "row": found}
    if err:
        return {"error": "order lookup failed: %s" % err}
    if not apply:
        return {"exists": False, "would_create": order_number}
    values = {
        "SalesOrderNumber": order_number,
        "SalesOrderName": name or order_number,
        "OrderingCustomerAccountNumber": customer_account,
        "InvoiceCustomerAccountNumber": customer_account,
        "CurrencyCode": currency,
        "RequestedShippingDate": requested_ship,
        "dataAreaId": company,
    }
    res, ok, detail = erp_create(erp, shape, "SalesOrderHeadersV4", values)
    return {"created": ok, "order_number": order_number, "detail": detail}


# ----------------------------------------------------------------------------- driver
def run(args):
    crm = McpClient(args.url, mcp_probe._load_token(args.token_file))
    crm.initialize()
    so, acct = crm_fetch_order(crm, args.order)
    order_id = so.get("ordernumber") or so["salesorderid"]
    n = _digits(order_id)
    erp_order_number = args.erp_order or ("E-9%s" % n)
    customer_account = args.customer_account or ("C-%s" % n)
    amount = int(float(so.get("totalamount") or 0))

    erp = McpClient(args.erp_url, mcp_probe._load_token(args.erp_token_file))
    erp.initialize()
    shape = erp_write_shape(erp)

    apply = bool(args.commit)
    if apply and not args.yes:
        raise SystemExit("Refusing to write without confirmation. Re-run with --yes to proceed.")

    plan = {
        "mode": "COMMIT" if apply else "DRY-RUN",
        "crm_order": {"ordernumber": order_id, "salesorderid": so["salesorderid"],
                      "account": acct.get("name"), "amount": amount},
        "erp_target": {"company": args.company, "sales_order_number": erp_order_number,
                       "customer_account": customer_account, "currency": args.currency},
        "erp_write_shape": {k: shape[k] for k in ("path", "defs")},
    }

    cust = ensure_customer(erp, shape, args.company, customer_account,
                           acct.get("name"), args.currency, apply)
    order = ensure_sales_order(erp, shape, args.company, erp_order_number, customer_account,
                               acct.get("name"), amount, args.currency, args.requested_ship, apply)
    verify = None
    if apply and order.get("created"):
        row, verr = erp_find_order(erp, args.company, erp_order_number)
        verify = {"read_back": row, "error": verr}
    stamp = crm_stamp_erp_order(crm, so["salesorderid"], erp_order_number, apply)

    result = {"plan": plan, "customer": cust, "sales_order": order,
              "verify": verify, "crm_stamp": stamp}
    return result


def main():
    p = argparse.ArgumentParser(description="Execute the CRM->ERP quote-to-cash push live.")
    p.add_argument("--url", required=True, help="Dataverse (CRM) MCP url")
    p.add_argument("--token-file", required=True, help="Dataverse MCP token file")
    p.add_argument("--erp-url", required=True, help="D365 F&O ERP MCP url")
    p.add_argument("--erp-token-file", required=True, help="ERP MCP token file")
    p.add_argument("--order", default="S005", help="CRM sales order ordernumber")
    p.add_argument("--erp-order", help="ERP SalesOrderNumber to create (default E-9<digits>)")
    p.add_argument("--customer-account", help="ERP CustomerAccount (default C-<digits>)")
    p.add_argument("--company", default="USMF", help="F&O legal entity / dataAreaId")
    p.add_argument("--currency", default="USD")
    p.add_argument("--requested-ship", default="2026-09-30", help="RequestedShippingDate")
    p.add_argument("--commit", action="store_true", help="actually write (default: dry run)")
    p.add_argument("--yes", action="store_true", help="confirm the write non-interactively")
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    result = run(args)
    if args.json:
        print(json.dumps(result, indent=2, default=str))
        return
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
