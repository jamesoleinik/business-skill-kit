---
name: master-data-sync
description: Align CRM accounts with ERP customers and flag orphans, dry-run-first. USE WHEN CRM and ERP master data may have drifted or lost links. DO NOT USE WHEN you only want an in-table duplicate check (use reconcile).
---

# master-data-sync

Align CRM accounts with ERP customers and flag orphans, dry-run-first.

Part of the Business Skill Kit. Runs against the synthetic fixture in `fixtures/org.json`
with zero real data. Reads are the default; any write is shown as a dry-run plan and applied
only with `--commit`, writing to `out/working.json` and never to the base fixture.

## Usage

```
python skills/cross-process/master-data-sync/skill.py
```

Add `--json` for structured output, `--store <path>` to point at another store, and
`--working out/working.json` to read or extend an applied overlay.

## Inputs

- Required tables: account, erp_customer
- Config comes from the environment only (see `.env.example`); no secrets in code.

## Safety

- Dry-run-first and idempotent: re-running an applied change is a no-op.
- No confidential or customer data; the fixture is entirely fictional.
- Check readiness first with `python skills/cross-process/master-data-sync/preflight.py`.
