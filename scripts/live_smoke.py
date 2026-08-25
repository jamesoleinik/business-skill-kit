"""Optional live smoke test: prove the read path works against a real Dataverse org.

Strictly read-only. It connects to the environment given by --url (or the LIVE_DATAVERSE_URL
environment variable), calls WhoAmI, and reads a few standard tables (accounts, contacts,
opportunities). It never writes. This is separate from validate.py, which runs every skill
against the synthetic fixture.

Auth: a bearer token comes from the Azure CLI for the org resource; nothing is stored.

Usage:
    python scripts/live_smoke.py --url https://<org>.crm.dynamics.com
    # or set LIVE_DATAVERSE_URL and run with no args
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from bskit.live import LiveError, LiveStore  # noqa: E402

READS = [
    ("systemusers", ["fullname"]),
    ("accounts", ["name", "accountnumber"]),
    ("contacts", ["fullname", "emailaddress1"]),
    ("opportunities", ["name", "estimatedvalue"]),
]


def main():
    ap = argparse.ArgumentParser(description="Read-only live smoke test against a Dataverse org.")
    ap.add_argument("--url", default=os.environ.get("LIVE_DATAVERSE_URL"), help="org URL, e.g. https://org.crm.dynamics.com")
    ap.add_argument("--top", type=int, default=3)
    args = ap.parse_args()
    if not args.url:
        print("No org URL. Pass --url or set LIVE_DATAVERSE_URL.")
        sys.exit(2)

    try:
        store = LiveStore(args.url)
        who = store.whoami()
        print("Connected (read-only) to %s" % args.url)
        print("WhoAmI: UserId=%s OrgId=%s" % (who.get("UserId"), who.get("OrganizationId")))
        for entityset, select in READS:
            rows = store.query(entityset, select=select, top=args.top)
            label = select[0]
            print("\n%s: read %d row(s)" % (entityset, len(rows)))
            for r in rows:
                print("  - %s" % (r.get(label) or "(no %s)" % label))
    except LiveError as e:
        print("LIVE READ FAILED: %s" % e)
        sys.exit(1)
    print("\nRead-only smoke test complete. No writes were made.")


if __name__ == "__main__":
    main()
