"""Idempotent CRM seeder for live ablation against a Dataverse environment.

Populates a small, self-contained CRM dataset (accounts, contacts, leads, opportunities)
so the with/without ablation conditions have real rows to reason over instead of fixtures.
Every seeded record's primary name carries the SEED_TAG prefix, so seeding is idempotent
(existing tagged rows are skipped) and teardown is exact (only tagged rows are deleted).

Nothing here hardcodes an environment: pass --url and --token-file (see signin.py). The
seeder reuses the MCP client in mcp_probe.py, so it speaks the same streamable-HTTP protocol.

Usage:
    python seed.py --url https://<org>.crm.dynamics.com/api/mcp_preview \
        --token-file ../build-notes/<org>-token.json --seed
    python seed.py --url ... --token-file ... --status
    python seed.py --url ... --token-file ... --teardown
"""
import argparse
import importlib.util
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("mcp_probe", os.path.join(HERE, "mcp_probe.py"))
mcp_probe = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mcp_probe)

_wspec = importlib.util.spec_from_file_location("webapi", os.path.join(HERE, "webapi.py"))
webapi = importlib.util.module_from_spec(_wspec)
_wspec.loader.exec_module(webapi)

SEED_TAG = "zzz-bskit-seed"

# Publisher prefix for the custom tables (set from --prefix at run time). Custom MANIFEST
# entries carry base names; the prefix is stamped on at run time so nothing in this file is
# environment-specific.
PREFIX = None


def _locators(entry):
    """Return (table_logical, namefield_logical, idfield) honouring the custom prefix."""
    if entry.get("custom"):
        if not PREFIX:
            raise SystemExit("entry %r needs a custom table; pass --prefix <publisher-prefix>"
                             % entry["key"])
        table = "%s_%s" % (PREFIX, entry["table"])
        namefield = "%s_%s" % (PREFIX, entry["namefield"])
        return table, namefield, table + "id"
    return entry["table"], entry["namefield"], entry["table"] + "id"

# Each entry: table, a name field carrying the tag, and additional literal fields.
# Order matters: parents (account) before children (contact, opportunity) so lookups resolve.
MANIFEST = [
    {"key": "acc-northwind", "table": "account", "namefield": "name",
     "name": SEED_TAG + " Northwind Traders",
     "fields": {"telephone1": "425-555-0101", "websiteurl": "https://northwind.example",
                "revenue": 5000000, "accountnumber": "C-1001"}},
    {"key": "acc-fabrikam", "table": "account", "namefield": "name",
     "name": SEED_TAG + " Fabrikam Manufacturing",
     "fields": {"telephone1": "425-555-0102", "revenue": 750000}},

    # Duplicate-named accounts for the reconcile skill. count=2 makes the seeder ensure two
    # rows with this exact name exist (idempotently), which reconcile flags as a duplicate.
    {"key": "acc-dupe", "table": "account", "namefield": "name",
     "name": SEED_TAG + " Dupe Co", "count": 2, "fields": {"revenue": 100000}},

    {"key": "con-northwind", "table": "contact", "namefield": "lastname",
     "name": SEED_TAG + " Reed",
     "fields": {"firstname": "Dana", "emailaddress1": "dana.reed@northwind.example"},
     "parent": {"field": "parentcustomerid", "table": "account", "key": "acc-northwind"}},

    {"key": "lead-hot", "table": "lead", "namefield": "subject",
     "name": SEED_TAG + " Hot inbound - 500 seats",
     "fields": {"firstname": "Alex", "lastname": SEED_TAG + " Morgan",
                "companyname": "Contoso Retail", "budgetamount": 250000,
                "emailaddress1": "alex.morgan@contoso.example"}},
    {"key": "lead-warm", "table": "lead", "namefield": "subject",
     "name": SEED_TAG + " Warm inbound - eval",
     "fields": {"firstname": "Sam", "lastname": SEED_TAG + " Patel",
                "companyname": "Tailspin Toys", "budgetamount": 40000,
                "emailaddress1": "sam.patel@tailspin.example"}},
    {"key": "lead-cold", "table": "lead", "namefield": "subject",
     "name": SEED_TAG + " Cold inbound - newsletter",
     "fields": {"firstname": "Jo", "lastname": SEED_TAG + " Kim",
                "companyname": "Wingtip", "budgetamount": 0}},

    {"key": "opp-northwind", "table": "opportunity", "namefield": "name",
     "name": SEED_TAG + " Northwind expansion",
     "fields": {"estimatedvalue": 180000, "closeprobability": 60},
     "parent": {"field": "parentaccountid", "table": "account", "key": "acc-northwind"}},

    # Risk-varied opportunities for deal-risk / opportunity-catchup (standard fields only:
    # low probability + a past close date make the risky one score highest).
    {"key": "opp-risky", "table": "opportunity", "namefield": "name",
     "name": SEED_TAG + " Risky stalled renewal",
     "fields": {"estimatedvalue": 90000, "closeprobability": 10,
                "estimatedclosedate": "2020-01-01"},
     "parent": {"field": "parentaccountid", "table": "account", "key": "acc-northwind"}},
    {"key": "opp-healthy", "table": "opportunity", "namefield": "name",
     "name": SEED_TAG + " Healthy new logo",
     "fields": {"estimatedvalue": 250000, "closeprobability": 85,
                "estimatedclosedate": "2027-12-31"},
     "parent": {"field": "parentaccountid", "table": "account", "key": "acc-northwind"}},

    # Consent contacts for the marketing consent-guard skill (contact_bskit_consent BIT).
    {"key": "con-optin", "table": "contact", "namefield": "lastname",
     "name": SEED_TAG + " Optin",
     "fields": {"firstname": "Ada", "emailaddress1": "ada.optin@northwind.example",
                "contact_bskit_consent": True}},
    {"key": "con-noconsent", "table": "contact", "namefield": "lastname",
     "name": SEED_TAG + " Noconsent",
     "fields": {"firstname": "Ben", "emailaddress1": "ben.noconsent@northwind.example",
                "contact_bskit_consent": False}},

    # Cases for the service skills (incident_bskit_category, incident_bskit_sla_status;
    # prioritycode High=1/Normal=2/Low=3; created Active). One breached-high to rank first.
    {"key": "inc-breach", "table": "incident", "namefield": "title",
     "name": SEED_TAG + " Breached billing overcharge",
     "fields": {"description": "Invoice shows a duplicate line item.", "prioritycode": 1,
                "incident_bskit_category": "billing", "incident_bskit_sla_status": "breached"},
     "parent": {"field": "customerid", "table": "account", "key": "acc-northwind"}},
    {"key": "inc-normal", "table": "incident", "namefield": "title",
     "name": SEED_TAG + " Login fails after update",
     "fields": {"description": "Customer cannot sign in following the latest update.", "prioritycode": 2,
                "incident_bskit_category": "technical", "incident_bskit_sla_status": "ok"},
     "parent": {"field": "customerid", "table": "account", "key": "acc-northwind"}},
    {"key": "inc-low", "table": "incident", "namefield": "title",
     "name": SEED_TAG + " How do I export a report",
     "fields": {"description": "Where is the export button in the new UI?", "prioritycode": 3,
                "incident_bskit_category": "how-to", "incident_bskit_sla_status": "ok"},
     "parent": {"field": "customerid", "table": "account", "key": "acc-northwind"}},

    # Records that must reach a *closed* state (won / resolved). MCP CRUD cannot set won or
    # resolved statecodes -- those transitions are managed messages (WinOpportunity,
    # CloseIncident) reached via the Web API in the --activate step below. Seeded Open/Active
    # here, transitioned there; both steps are idempotent.
    {"key": "opp-won", "table": "opportunity", "namefield": "name",
     "name": SEED_TAG + " Won expansion deal",
     "fields": {"estimatedvalue": 120000, "closeprobability": 100},
     "parent": {"field": "parentaccountid", "table": "account", "key": "acc-northwind"}},
    {"key": "inc-knowledge", "table": "incident", "namefield": "title",
     "name": SEED_TAG + " Resolved sign-in outage",
     "fields": {"description": "Sign-in outage resolved by a config rollback; good KB source.",
                "prioritycode": 2, "incident_bskit_category": "technical",
                "incident_bskit_sla_status": "ok"},
     "parent": {"field": "customerid", "table": "account", "key": "acc-northwind"}},
    {"key": "inc-return", "table": "incident", "namefield": "title",
     "name": SEED_TAG + " Return faulty units for credit",
     "fields": {"description": "Customer returning faulty units; needs a credit to ERP.",
                "prioritycode": 2, "incident_bskit_category": "return",
                "incident_bskit_sla_status": "ok"},
     "parent": {"field": "customerid", "table": "account", "key": "acc-northwind"}},

    # Custom-table records for marketing + business-central skills. These live in custom
    # Dataverse tables that carry a publisher prefix; pass it with --prefix and the seeder
    # stamps it onto the table and every column at run time (nothing prefix-specific here).
    {"key": "seg-enterprise", "table": "bskitsegment", "custom": True, "namefield": "name",
     "name": SEED_TAG + " Enterprise accounts",
     "fields": {"definition": "revenue >= 1000000", "status": "draft", "membercount": 1}},
    {"key": "jny-live-errors", "table": "bskitjourney", "custom": True, "namefield": "name",
     "name": SEED_TAG + " Welcome journey",
     "fields": {"status": "live", "segmentid": "unlinked", "errors": 2}},
    {"key": "msg-lowclick", "table": "bskitemailmsg", "custom": True, "namefield": "name",
     "name": SEED_TAG + " Underperforming blast",
     "fields": {"channel": "email", "sends": 1000, "opens": 200, "clicks": 10}},
    {"key": "msg-good", "table": "bskitemailmsg", "custom": True, "namefield": "name",
     "name": SEED_TAG + " Healthy newsletter",
     "fields": {"channel": "email", "sends": 1000, "opens": 500, "clicks": 100}},
    {"key": "item-widget", "table": "bskititem", "custom": True, "namefield": "name",
     "name": SEED_TAG + " Widget A100",
     "fields": {"number": "ITEM-A100", "description": "Standard widget", "price": 50,
                "inventory": 5}},
]


def _text(res):
    try:
        return res["result"]["content"][0]["text"]
    except (KeyError, IndexError, TypeError):
        return json.dumps(res)


def _find_id(client, table, namefield, name, idfield=None):
    idfield = idfield or (table + "id")
    q = "SELECT %s, %s FROM %s WHERE %s = '%s'" % (
        namefield, idfield, table, namefield, name.replace("'", "''"))
    res = client.tools_call("read_query", {"querytext": q})
    if res.get("result", {}).get("isError"):
        return None
    try:
        rows = json.loads(_text(res))
    except (json.JSONDecodeError, TypeError):
        return None
    if rows:
        return rows[0].get(idfield)
    return None


def _count_ids(client, table, namefield, name, idfield):
    q = "SELECT %s, %s FROM %s WHERE %s = '%s'" % (
        namefield, idfield, table, namefield, name.replace("'", "''"))
    res = client.tools_call("read_query", {"querytext": q})
    if res.get("result", {}).get("isError"):
        return []
    try:
        rows = json.loads(_text(res))
    except (json.JSONDecodeError, TypeError):
        return []
    return [r.get(idfield) for r in rows]


def _resolve(client, entry, created):
    item = dict(entry["fields"])
    item[entry["namefield"]] = entry["name"]
    parent = entry.get("parent")
    if parent:
        pid = created.get(parent["key"])
        if not pid:
            pid = _find_id(client, parent["table"], "name", MANIFEST_BY_KEY[parent["key"]]["name"])
        if pid:
            item[parent["field"]] = {"relatedTable": parent["table"], "recordId": pid}
    if entry.get("custom"):
        item = {"%s_%s" % (PREFIX, k): v for k, v in item.items()}
    return item


MANIFEST_BY_KEY = {e["key"]: e for e in MANIFEST}

# Records whose *closed* state is set post-create via managed Web API messages (see the
# --activate command). Idempotent: skipped when the record already reached statecode 1.
ACTIVATIONS = [
    {"key": "opp-won", "action": "WinOpportunity", "done": "Won"},
    {"key": "inc-knowledge", "action": "CloseIncident", "done": "Resolved"},
    {"key": "inc-return", "action": "CloseIncident", "done": "Resolved"},
]


def _is_closed(state):
    return state in (1, "1", "Won", "Resolved", "Inactive")


def cmd_activate(client, wc):
    for act in ACTIVATIONS:
        entry = MANIFEST_BY_KEY[act["key"]]
        table, namefield, idfield = _locators(entry)
        q = "SELECT %s, statecode FROM %s WHERE %s = '%s'" % (
            idfield, table, namefield, entry["name"].replace("'", "''"))
        res = client.tools_call("read_query", {"querytext": q})
        try:
            rows = json.loads(_text(res))
        except (json.JSONDecodeError, TypeError):
            rows = []
        if not rows:
            print("MISS %-12s %s (run --seed first)" % (table, entry["name"]))
            continue
        rid = rows[0].get(idfield)
        if _is_closed(rows[0].get("statecode")):
            print("skip %-12s %s (already %s)" % (table, entry["name"], act["done"]))
            continue
        if act["action"] == "WinOpportunity":
            status, _ = wc.win_opportunity(rid)
        else:
            status, _ = wc.close_incident(rid)
        ok = status in (200, 204)
        print("%s %-12s %s -> HTTP %s (%s)"
              % ("OK  " if ok else "FAIL", table, entry["name"], status, act["done"]))


def cmd_seed(client):
    created = {}
    for entry in MANIFEST:
        table, namefield, idfield = _locators(entry)
        want = entry.get("count")
        if want:
            have = _count_ids(client, table, namefield, entry["name"], idfield)
            created[entry["key"]] = have[0] if have else None
            for _ in range(max(0, want - len(have))):
                item = _resolve(client, entry, created)
                res = client.tools_call("create_record", {"tablename": table, "item": item})
                txt = _text(res)
                rid = txt.split()[-1] if "ID" in txt else None
                created[entry["key"]] = created[entry["key"]] or rid
                print("create %-16s %s (dup) -> %s" % (table, entry["name"], rid or txt))
            if want <= len(have):
                print("skip  %-16s %s (%d already exist)" % (table, entry["name"], len(have)))
            continue
        existing = _find_id(client, table, namefield, entry["name"], idfield)
        if existing:
            created[entry["key"]] = existing
            print("skip  %-16s %s (exists %s)" % (table, entry["name"], existing))
            continue
        item = _resolve(client, entry, created)
        res = client.tools_call("create_record", {"tablename": table, "item": item})
        txt = _text(res)
        if res.get("result", {}).get("isError"):
            print("FAIL  %-16s %s -> %s" % (table, entry["name"], txt))
            continue
        rid = txt.split()[-1] if "ID" in txt else None
        if rid:
            created[entry["key"]] = rid
        print("create %-16s %s -> %s" % (table, entry["name"], rid or txt))
    print("seeded %d/%d records" % (len(created), len(MANIFEST)))


def cmd_status(client):
    for table in ("account", "contact", "lead", "opportunity", "incident"):
        namefield = "lastname" if table == "contact" else (
            "subject" if table == "lead" else ("title" if table == "incident" else "name"))
        q = "SELECT %s, %sid FROM %s WHERE %s LIKE '%s%%'" % (
            namefield, table, table, namefield, SEED_TAG)
        res = client.tools_call("read_query", {"querytext": q})
        try:
            rows = json.loads(_text(res))
        except (json.JSONDecodeError, TypeError):
            rows = []
        print("%-12s %d tagged row(s)" % (table, len(rows)))
        for r in rows:
            print("   - %s" % r.get(namefield))


def cmd_teardown(client):
    n = 0
    for entry in reversed(MANIFEST):
        table, namefield, idfield = _locators(entry)
        rid = _find_id(client, table, namefield, entry["name"], idfield)
        if not rid:
            continue
        res = client.tools_call("delete_record", {
            "tablename": table, "recordId": rid, "hasUserApproved": True})
        ok = not res.get("result", {}).get("isError")
        print("%s %-16s %s" % ("del " if ok else "FAIL", table, entry["name"]))
        n += 1 if ok else 0
    print("removed %d record(s)" % n)


def main():
    p = argparse.ArgumentParser(description="Idempotent tagged CRM seeder for live ablation.")
    p.add_argument("--url", required=True)
    p.add_argument("--token-file", required=True)
    p.add_argument("--prefix", help="publisher prefix for the custom tables (e.g. crXXX)")
    p.add_argument("--webapi-token-file",
                   help="token file scoped to the org Web API (…/.default); "
                        "required for --activate to invoke WinOpportunity/CloseIncident")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--seed", action="store_true")
    g.add_argument("--activate", action="store_true",
                   help="win/resolve the dedicated closed-state records via the Web API")
    g.add_argument("--status", action="store_true")
    g.add_argument("--teardown", action="store_true")
    args = p.parse_args()

    global PREFIX
    PREFIX = args.prefix
    client = mcp_probe.McpClient(args.url, mcp_probe._load_token(args.token_file))
    client.initialize()
    if args.seed:
        cmd_seed(client)
    elif args.activate:
        if not args.webapi_token_file:
            raise SystemExit("--activate requires --webapi-token-file (org Web API scope)")
        wc = webapi.WebApiClient(args.url, webapi.load_token(args.webapi_token_file))
        cmd_activate(client, wc)
    elif args.status:
        cmd_status(client)
    elif args.teardown:
        cmd_teardown(client)


if __name__ == "__main__":
    main()
