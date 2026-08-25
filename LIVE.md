# Live mode (optional, read-only)

The kit runs on the synthetic fixture by default and needs no environment. This optional
mode points the read path at a real Dataverse environment for a connectivity and read
smoke test. It is read-only by construction: `bskit/live.py` exposes GET-based helpers
only and never creates, updates, or deletes.

## Prerequisites

- The Azure CLI (`az`) signed in with access to the target Dataverse org. A bearer token
  is fetched at runtime with `az account get-access-token`; no secret is stored or
  committed.
- The org URL, e.g. `https://your-org.crm.dynamics.com`.

## Run it

```
python scripts/live_smoke.py --url https://your-org.crm.dynamics.com
# or
set LIVE_DATAVERSE_URL=https://your-org.crm.dynamics.com   # Windows
python scripts/live_smoke.py
```

It calls `WhoAmI`, then reads a few standard tables (`systemusers`, `accounts`,
`contacts`, `opportunities`) and prints a small sample. No writes are made.

## Verified

Run read-only against a real environment (agent365003 tenant) on 2026-08-25:

```
Connected (read-only) to https://<org>.crm.dynamics.com    (Product Launch 2.0)
WhoAmI: UserId=<guid> OrgId=<guid>
systemusers: read 3 row(s)      # real rows returned
accounts / contacts / opportunities: read 0 row(s)   # this env has no CRM sales data
Read-only smoke test complete. No writes were made.
```

The connection and reads succeed; the sales tables are simply empty in that particular
environment. No live output is committed to the repo.

## Why the skills still target the fixture

The fixture uses simplified, portable table and field names so every skill runs anywhere
with zero setup and zero real data. Mapping each skill to a specific environment's schema
is deployment-time work; live mode here proves the read path and auth, not a full schema
binding. Any future live writes must stay dry-run-first and go through explicit approval,
exactly as the fixture path does.
