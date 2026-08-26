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

SEED_TAG = "zzz-bskit-seed"

# Each entry: table, a name field carrying the tag, and additional literal fields.
# Order matters: parents (account) before children (contact, opportunity) so lookups resolve.
MANIFEST = [
    {"key": "acc-northwind", "table": "account", "namefield": "name",
     "name": SEED_TAG + " Northwind Traders",
     "fields": {"telephone1": "425-555-0101", "websiteurl": "https://northwind.example"}},
    {"key": "acc-fabrikam", "table": "account", "namefield": "name",
     "name": SEED_TAG + " Fabrikam Manufacturing",
     "fields": {"telephone1": "425-555-0102"}},

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
]


def _text(res):
    try:
        return res["result"]["content"][0]["text"]
    except (KeyError, IndexError, TypeError):
        return json.dumps(res)


def _find_id(client, table, namefield, name):
    idfield = table + "id"
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
    return item


MANIFEST_BY_KEY = {e["key"]: e for e in MANIFEST}


def cmd_seed(client):
    created = {}
    for entry in MANIFEST:
        existing = _find_id(client, entry["table"], entry["namefield"], entry["name"])
        if existing:
            created[entry["key"]] = existing
            print("skip  %-14s %s (exists %s)" % (entry["table"], entry["name"], existing))
            continue
        item = _resolve(client, entry, created)
        res = client.tools_call("create_record", {"tablename": entry["table"], "item": item})
        txt = _text(res)
        if res.get("result", {}).get("isError"):
            print("FAIL  %-14s %s -> %s" % (entry["table"], entry["name"], txt))
            continue
        rid = txt.split()[-1] if "ID" in txt else None
        if rid:
            created[entry["key"]] = rid
        print("create %-14s %s -> %s" % (entry["table"], entry["name"], rid or txt))
    print("seeded %d/%d records" % (len(created), len(MANIFEST)))


def cmd_status(client):
    for table in ("account", "contact", "lead", "opportunity"):
        namefield = "lastname" if table == "contact" else ("subject" if table == "lead" else "name")
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
        rid = _find_id(client, entry["table"], entry["namefield"], entry["name"])
        if not rid:
            continue
        res = client.tools_call("delete_record", {
            "tablename": entry["table"], "recordId": rid, "hasUserApproved": True})
        ok = not res.get("result", {}).get("isError")
        print("%s %-14s %s" % ("del " if ok else "FAIL", entry["table"], entry["name"]))
        n += 1 if ok else 0
    print("removed %d record(s)" % n)


def main():
    p = argparse.ArgumentParser(description="Idempotent tagged CRM seeder for live ablation.")
    p.add_argument("--url", required=True)
    p.add_argument("--token-file", required=True)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--seed", action="store_true")
    g.add_argument("--status", action="store_true")
    g.add_argument("--teardown", action="store_true")
    args = p.parse_args()

    client = mcp_probe.McpClient(args.url, mcp_probe._load_token(args.token_file))
    client.initialize()
    if args.seed:
        cmd_seed(client)
    elif args.status:
        cmd_status(client)
    elif args.teardown:
        cmd_teardown(client)


if __name__ == "__main__":
    main()
