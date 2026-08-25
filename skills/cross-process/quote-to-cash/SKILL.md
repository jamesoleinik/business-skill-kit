---
name: quote-to-cash
description: Drive a CRM sales order to an ERP invoice across the whole chain, dry-run-first. USE WHEN a won order must flow from CRM through ERP to an invoice. DO NOT USE WHEN you only need the CRM-side quote and order (use quote-flow).
---

# quote-to-cash

Drive a CRM sales order to an ERP invoice across the whole chain, dry-run-first.

Part of the Business Skill Kit. Runs against the synthetic fixture in `fixtures/org.json`
with zero real data. Reads are the default; any write is shown as a dry-run plan and applied
only with `--commit`, writing to `out/working.json` and never to the base fixture.

## Usage

```
python skills/cross-process/quote-to-cash/skill.py --order S005
```

Add `--json` for structured output, `--store <path>` to point at another store, and
`--working out/working.json` to read or extend an applied overlay.

## Inputs

- Required tables: salesorder, erp_salesorder, erp_invoice, account
- Config comes from the environment only (see `.env.example`); no secrets in code.

## Safety

- Dry-run-first and idempotent: re-running an applied change is a no-op.
- No confidential or customer data; the fixture is entirely fictional.
- Check readiness first with `python skills/cross-process/quote-to-cash/preflight.py`.
