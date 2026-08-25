---
name: bc-record
description: List, create, or update a Business Central item, dry-run-first. USE WHEN you need to read or edit Business Central items. DO NOT USE WHEN you need to invoke an item action (use bc-action).
---

# bc-record

List, create, or update a Business Central item, dry-run-first.

Part of the Business Skill Kit. Runs against the synthetic fixture in `fixtures/org.json`
with zero real data. Reads are the default; any write is shown as a dry-run plan and applied
only with `--commit`, writing to `out/working.json` and never to the base fixture.

## Usage

```
python skills/business-central/bc-record/skill.py
```

Add `--json` for structured output, `--store <path>` to point at another store, and
`--working out/working.json` to read or extend an applied overlay.

## Inputs

- Required tables: bc_item
- Config comes from the environment only (see `.env.example`); no secrets in code.

## Safety

- Dry-run-first and idempotent: re-running an applied change is a no-op.
- No confidential or customer data; the fixture is entirely fictional.
- Check readiness first with `python skills/business-central/bc-record/preflight.py`.
