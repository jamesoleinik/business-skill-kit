---
name: entity-query
description: Read any data entity with an explainable filter. USE WHEN you need an auditable read of any entity. DO NOT USE WHEN you need to write (use entity-edit).
---

# entity-query

Read any data entity with an explainable filter.

Part of the Business Skill Kit. Runs against the synthetic fixture in `fixtures/org.json`
with zero real data. Reads are the default; any write is shown as a dry-run plan and applied
only with `--commit`, writing to `out/working.json` and never to the base fixture.

## Usage

```
python skills/finance/entity-query/skill.py --entity erp_invoice
```

Add `--json` for structured output, `--store <path>` to point at another store, and
`--working out/working.json` to read or extend an applied overlay.

## Inputs

- Required tables: account
- Config comes from the environment only (see `.env.example`); no secrets in code.

## Safety

- Dry-run-first and idempotent: re-running an applied change is a no-op.
- No confidential or customer data; the fixture is entirely fictional.
- Check readiness first with `python skills/finance/entity-query/preflight.py`.
