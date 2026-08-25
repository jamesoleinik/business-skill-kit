---
name: bc-action
description: Discover and dry-run a Business Central item action. USE WHEN you need to run a bounded item action like adjust-inventory. DO NOT USE WHEN you need a plain create/update (use bc-record).
---

# bc-action

Discover and dry-run a Business Central item action.

Part of the Business Skill Kit. Runs against the synthetic fixture in `fixtures/org.json`
with zero real data. Reads are the default; any write is shown as a dry-run plan and applied
only with `--commit`, writing to `out/working.json` and never to the base fixture.

## Usage

```
python skills/business-central/bc-action/skill.py --action adjust-inventory --id B001 --by -5
```

Add `--json` for structured output, `--store <path>` to point at another store, and
`--working out/working.json` to read or extend an applied overlay.

## Inputs

- Required tables: bc_item
- Config comes from the environment only (see `.env.example`); no secrets in code.

## Safety

- Dry-run-first and idempotent: re-running an applied change is a no-op.
- No confidential or customer data; the fixture is entirely fictional.
- Check readiness first with `python skills/business-central/bc-action/preflight.py`.
