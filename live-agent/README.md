# live-agent — test the skills against real Dataverse orgs

This harness uses the **GitHub Copilot SDK** (`@github/copilot-sdk`) to drive the real
**Microsoft Dataverse MCP server** against one or more Dataverse orgs, running a per-skill
scenario suite and printing a PASS / FAIL / NA matrix per org. It is the "log in and test
these across the servers" path: you sign in interactively per org and the agent exercises
each skill through the live Dataverse MCP tools (`read_query`, `describe`, `create_record`,
`update_record`, `delete_record`, ...).

Fixture mode (`validate.py` in the repo root) still runs everything offline with zero real
data. This harness is the optional live counterpart.

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

- **PASS** — the skill's live operation succeeded on that org.
- **FAIL** — the operation was attempted but failed (error shown).
- **NA** — not applicable on that org: a required table/entity isn't present, or the skill
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
