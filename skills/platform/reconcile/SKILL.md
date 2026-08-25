---
name: reconcile
description: Find duplicate or drifted records and propose fixes before a close. USE WHEN you want a data-quality pass before reporting or a close. DO NOT USE WHEN you want to align CRM and ERP master data end to end (use master-data-sync).
---

# reconcile

Find duplicate or drifted records and propose fixes before a close.

Part of the Business Skill Kit. Runs against the synthetic fixture in `fixtures/org.json`
with zero real data. Reads are the default; any write is shown as a dry-run plan and applied
only with `--commit`, writing to `out/working.json` and never to the base fixture.

## Usage

```
python skills/platform/reconcile/skill.py --table account
```

Add `--json` for structured output, `--store <path>` to point at another store, and
`--working out/working.json` to read or extend an applied overlay.

## Inputs

- Required tables: account, erp_customer
- Config comes from the environment only (see `.env.example`); no secrets in code.

## Safety

- Dry-run-first and idempotent: re-running an applied change is a no-op.
- No confidential or customer data; the fixture is entirely fictional.
- Check readiness first with `python skills/platform/reconcile/preflight.py`.
