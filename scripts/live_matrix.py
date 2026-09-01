"""Optional live coverage matrix: read-only probe of the skills' tables across many orgs.

For each Dataverse org URL given, this reads (GET only, never writes) the standard tables
the skills operate on and prints a matrix of row counts (or the error per cell). It proves
the read path and auth breadth across environments/servers. Auth tokens come from the Azure
CLI at runtime; nothing is stored or committed.

Usage:
    python scripts/live_matrix.py --url https://<org-a>.crm.dynamics.com --url https://<org-b>.crm.dynamics.com
    python scripts/live_matrix.py --url LABEL=https://<org-a>.crm.dynamics.com ...
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from bskit.live import LiveError, LiveStore, get_token  # noqa: E402

# entity set names the fixture tables map to in a standard Dataverse org
ENTITY_SETS = ["systemusers", "accounts", "contacts", "leads", "opportunities", "incidents"]


def probe(url):
    row = {}
    try:
        token = get_token(url)
    except LiveError as e:
        return {es: "no-token" for es in ENTITY_SETS}, str(e)
    store = LiveStore(url, token=token)
    for es in ENTITY_SETS:
        try:
            key = es[:-1] + "id" if es != "systemusers" else "systemuserid"
            n = len(store.query(es, select=[key], top=50))
            row[es] = str(n) + ("+" if n == 50 else "")
        except LiveError as e:
            msg = str(e)
            code = next((c for c in ("404", "403", "401") if "HTTP " + c in msg), None)
            row[es] = code or "err"
    return row, None


def main():
    ap = argparse.ArgumentParser(description="Read-only coverage matrix across Dataverse orgs.")
    ap.add_argument("--url", action="append", default=[], help="org URL, optionally LABEL=url")
    args = ap.parse_args()
    if not args.url:
        print("Pass one or more --url.")
        sys.exit(2)

    targets = []
    for i, u in enumerate(args.url, 1):
        if "=" in u and u.split("=", 1)[0].isalnum():
            label, url = u.split("=", 1)
        else:
            label, url = "env%d" % i, u
        targets.append((label, url))

    results = {}
    for label, url in targets:
        row, fatal = probe(url)
        results[label] = row
        if fatal:
            print("# %s: token error: %s" % (label, fatal[:120]))

    cols = ["server"] + ENTITY_SETS
    widths = {c: len(c) for c in cols}
    for label, row in results.items():
        widths["server"] = max(widths["server"], len(label))
        for es in ENTITY_SETS:
            widths[es] = max(widths[es], len(str(row.get(es, "-"))))
    print(" | ".join(c.ljust(widths[c]) for c in cols))
    print("-+-".join("-" * widths[c] for c in cols))
    for label, row in results.items():
        cells = [label.ljust(widths["server"])] + [str(row.get(es, "-")).ljust(widths[es]) for es in ENTITY_SETS]
        print(" | ".join(cells))
    print("\nCounts are read-only row counts (top 50; '+' means 50 or more). "
          "404 = table absent, 403 = token identity not a member of the org, "
          "401 = not authorized (typically cross-tenant token), no-token = token unavailable. "
          "No writes were made.")


if __name__ == "__main__":
    main()
