# live-agent: test the skills against real Dataverse orgs

This harness uses the **GitHub Copilot SDK** (`@github/copilot-sdk`) to drive the real
**Microsoft Dataverse MCP server** against one or more Dataverse orgs, running a per-skill
scenario suite and printing a PASS / FAIL / NA matrix per org. It is the "log in and test
these across the servers" path: you sign in interactively per org and the agent exercises
each skill through the live Dataverse MCP tools (`read_query`, `describe`, `create_record`,
`update_record`, `delete_record`, ...).

Fixture mode (`validate.py` in the repo root) still runs everything offline with zero real
data. This harness is the optional live counterpart.

## Two planes: Dataverse MCP (CRM) + D365 F&O ERP MCP

The portfolio's cross-process skills (e.g. `quote-to-cash`) span two live MCP servers for
the **same** environment, each an OAuth-protected resource with the identical auth pattern
(Entra auth-code + PKCE, a `<resource>/mcp.tools` scope, per-environment client allow-list):

| Plane | Endpoint | Scope |
| --- | --- | --- |
| CRM / Dataverse | `https://<env>.crm.dynamics.com/api/mcp` (or `/api/mcp_preview`) | `.../api/mcp/mcp.tools` |
| ERP / D365 F&O | `https://<env>.operations.dynamics.com/mcp` | `.../mcp/mcp.tools` |

The ERP path is **`/mcp`** (not `/api/mcp`). Both advertise their authorization server and
scope at `/.well-known/oauth-protected-resource`. The remote **Dynamics 365 ERP MCP Server**
exposes data tools (`data_find_entities_sql`, `data_get_entity_metadata`,
`data_find_entity_type`, `data_create_entities`/`update`/`delete`), API tools
(`api_find_actions`, `api_invoke_action`), and form tools (`form_*`). Query F&O with OData
`EntitySetName`s (e.g. `SalesOrderHeadersV4`) and a `companyId` (a legal-entity id or
`Cross-company`). The dual-write bridge entity `D365SalesOrderHeaders` links CRM sales
orders into F&O, which is the natural join for CRM->ERP skills.

Prereqs for the ERP plane (per Microsoft docs): F&O >= 10.0.46, the MCP feature enabled in
Feature Management, and the client app allow-listed at *System administration > Setup >
Allowed MCP clients* (separate from the Dataverse allow-list). Docs:
`learn.microsoft.com/dynamics365/fin-ops-core/dev-itpro/copilot/mcp/mcp-vscode`.

The stdlib helpers `signin.py` and `mcp_probe.py` work against **either** plane: pass the
respective `--url` and `--scope`; nothing is hardcoded to an environment.

## How auth works (important)

The Dataverse MCP endpoint is `https://<org>.crm.dynamics.com/api/mcp`. It is an
OAuth-protected resource:

- Unauthenticated requests get `401` + a `WWW-Authenticate` challenge pointing at
  `/.well-known/oauth-protected-resource`, which advertises the Entra authorization server
  and the `.../api/mcp/mcp.tools` scope (auth-code + PKCE).
- The endpoint only accepts tokens from **client apps on the environment's approved MCP
  client list**. A raw `az`/`pac` token is rejected with `403` ("application ... is not
  authorized to access MCP") because its app id isn't approved.

So the SDK performs an **interactive browser sign-in** as an approved client (for example
*Microsoft GitHub Copilot*). That is your login step. `mcpOAuthTokenStorage: "persistent"`
caches it so you sign in once per org.

## Prerequisites

1. **GitHub Copilot CLI** installed and authenticated (`copilot --version`). The SDK uses it.
2. **Node.js 20+**.
3. For each org you want to test, the **Microsoft GitHub Copilot** MCP client must be
   allowed in that environment (Power Platform admin center > environment > the MCP client
   allow-list). See https://aka.ms/configuremcpclientlist. Without this you get `403`.
4. `npm install` in this folder.

## Configure your orgs

Copy the example and fill in the orgs you can sign into:

```bash
cp orgs.example.json orgs.json
```

`orgs.json` (gitignored) is a list of `{ "label", "url", "tenantId" }`. `tenantId` is
optional and only used as a hint. Real URLs never leave your machine.

## Run

```bash
# read-only first (default): only query/describe scenarios
npm run run

# a subset of skills
npm run run -- --only records,opportunity-catchup,case-triage

# include write scenarios (creates uniquely tagged 'zzz-bskit-test' records, then deletes them)
npm run run -- --mode all

# point at a specific orgs file / model
npm run run -- --orgs orgs.smoke.json --model auto
```

The first time each org is contacted, complete the browser sign-in. Results print as a
matrix and are saved (gitignored) under `reports/`.

### Flags

| flag | meaning |
| --- | --- |
| `--orgs <path>` | orgs file (default `orgs.json`) |
| `--only a,b,c` | run only these skill slugs |
| `--mode read\|all` | `read` (default, safe) skips write scenarios; `all` includes them |
| `--no-write` | force-skip write scenarios even in `--mode all` |
| `--model <name>` | model for the agent loop (default `auto`) |

## What the matrix means

Each scenario asks the agent to finish with a `RESULT:` line, which the harness parses:

- **PASS**: the skill's live operation succeeded on that org.
- **FAIL**: the operation was attempted but failed (error shown).
- **NA**: not applicable on that org: a required table/entity isn't present, or the skill
  is local-only (scaffold) or targets non-Dataverse systems (ERP / Business Central /
  Customer Insights - Journeys), which the portable fixture models but a standard Dataverse
  org does not expose.

`scenarios.json` maps every one of the 30 skills to a live scenario or marks it fixture-only,
so the matrix honestly separates "works live here" from "no live Dataverse equivalent".

## Safety

- Read-only by default. Writes only with `--mode all`, and every test record is tagged
  `zzz-bskit-test` and deleted before the scenario finishes.
- No org URLs, GUIDs, tenant ids, tokens, or row data are committed: `orgs.json`,
  `orgs.smoke.json`, `reports/`, and logs are gitignored.
