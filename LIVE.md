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

Run read-only against a real environment on 2026-08-25:

```
Connected (read-only) to https://<org>.crm.dynamics.com    (Product Launch 2.0)
WhoAmI: UserId=<guid> OrgId=<guid>
systemusers: read 3 row(s)      # real rows returned
accounts / contacts / opportunities: read 0 row(s)   # this env has no CRM sales data
Read-only smoke test complete. No writes were made.
```

The connection and reads succeed; the sales tables are simply empty in that particular
environment. No live output is committed to the repo.

## Coverage matrix across servers (read-only)

`scripts/live_matrix.py` probes several orgs at once and prints a row-count matrix for the
standard tables the skills touch. It is GET-only and prints per-cell status instead of data:

```
python scripts/live_matrix.py \
  --url labelA=https://<orgA>.crm.dynamics.com \
  --url labelB=https://<orgB>.crm.dynamics.com \
  --url labelC=https://<orgC>.crm.dynamics.com
```

Example shape of the output (labels generic; no real URLs, GUIDs, or data shown):

```
server | systemusers | accounts | contacts | leads | opportunities | incidents
-------+-------------+----------+----------+-------+---------------+----------
orgA   | 50+         | 0        | 0        | 0     | 0             | 0
orgB   | 401         | 401      | 401      | 401   | 401           | 401
orgC   | 403         | 403      | 403      | 403   | 403           | 403
```

Cell legend: a number is a read-only row count (top 50; `+` means 50 or more),
`404` = table absent, `403` = the token identity is not a member of that org,
`401` = not authorized (typically a cross-tenant token the org rejects),
`no-token` = a token could not be acquired. No writes are ever made.

What this proves and its limits: the read path and the skills' table surface resolve
cleanly against an org the signed-in identity actually belongs to. Because the runtime
token comes from a single `az` sign-in, orgs in other tenants return `401`/`403` until you
run an interactive per-tenant sign-in (`az login --tenant <id>`) for each. This is a
read-path/auth breadth check, not full per-skill write testing through the servers.

## Why the skills still target the fixture

The fixture uses simplified, portable table and field names so every skill runs anywhere
with zero setup and zero real data. Mapping each skill to a specific environment's schema
is deployment-time work; live mode here proves the read path and auth, not a full schema
binding. Any future live writes must stay dry-run-first and go through explicit approval,
exactly as the fixture path does.

## Agent-driven testing across servers (live-agent/)

`live-agent/` is a GitHub Copilot SDK harness that drives the real Dataverse MCP server
(`<org>/api/mcp`) against multiple orgs and prints a PASS / FAIL / NA matrix per skill per
org. Unlike the `az`-token read probes above, it authenticates via the endpoint's
interactive OAuth (auth-code + PKCE) as an approved MCP client, so you sign in per org and
it can exercise both reads and writes (writes create a `zzz-bskit-test` record and delete
it). Requires the *Microsoft GitHub Copilot* MCP client to be allowed on each environment
(https://aka.ms/configuremcpclientlist). See `live-agent/README.md`.
is deployment-time work; live mode here proves the read path and auth, not a full schema
binding. Any future live writes must stay dry-run-first and go through explicit approval,
exactly as the fixture path does.
