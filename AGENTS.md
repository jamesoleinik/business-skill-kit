# Agent conventions

Conventions for any coding agent working in this repo. Same discipline used across the
portfolio, adapted for skills that touch real business data across Dynamics 365,
Dataverse, and the Power Platform.

## Ground rules
- No secrets in code. Read the environment URL from `DATAVERSE_URL` and reuse an
  existing auth profile (see `.env.example`); never commit an `.env`, a token, or a
  real org URL.
- Read-only by default. A skill that can mutate business data shows what it would
  change and asks for confirmation before it writes. Reads never mutate.
- Idempotent writes. A re-run never creates duplicates or corrupts state. Prefer
  upsert by alternate key for writes.
- Validate before you claim. Every skill runs against its synthetic fixture before it
  ships, and against a live environment where feasible. Record what was verified.
- No confidential content. Only generic skill categories and synthetic fixtures are
  committed. Internal first-party inventories, real environment URLs, tenant or org
  IDs, application-user or user display names, and UPNs never appear here. Use
  placeholders like `<your-env>`, `<tenant-id>`, `<demo-user>`.
- House style. Refer to task categories generically; do not name third-party community
  tools, products, or authors. First-party Microsoft tooling (the Dataverse MCP server,
  the Dataverse Web API and SDK, Power Automate, Power Apps, Copilot Studio, PAC CLI)
  may be named. No em-dashes.

## Encoding
On Windows, set `PYTHONIOENCODING=utf-8` before running scripts so JSON and emoji do
not crash the console.

## Auth
Skills reuse an existing authentication profile; no skill performs an interactive
sign-in as a side effect. See `.env.example` and each skill's `preflight.py`.

## The shape of a skill
Each skill is a self-contained folder under `skills/<slug>/` with:
- `SKILL.md`  the business job, when to use it and when not to, inputs and outputs.
- `preflight.py`  a read-only check that the skill can run (auth works, environment
  reachable, prerequisites present). Exits non-zero when not ready.
- one or more scripts  the skill itself, read-only or dry-run-first, idempotent.
- a fixture  a synthetic dataset so the skill can be tried with zero real data.
