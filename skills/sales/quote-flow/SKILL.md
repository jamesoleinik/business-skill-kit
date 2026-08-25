---
name: quote-flow
description: Advance a won opportunity to a quote and CRM sales order, dry-run-first. USE WHEN a deal is won and you need the quote and CRM order staged. DO NOT USE WHEN you need to push the order to ERP and invoice (use quote-to-cash).
---

# quote-flow

Advance a won opportunity to a quote and CRM sales order, dry-run-first.

Part of the Business Skill Kit. Runs against the synthetic fixture in `fixtures/org.json`
with zero real data. Reads are the default; any write is shown as a dry-run plan and applied
only with `--commit`, writing to `out/working.json` and never to the base fixture.

## Usage

```
python skills/sales/quote-flow/skill.py --opp O005
```

Add `--json` for structured output, `--store <path>` to point at another store, and
`--working out/working.json` to read or extend an applied overlay.

## Inputs

- Required tables: opportunity, quote, salesorder
- Config comes from the environment only (see `.env.example`); no secrets in code.

## Safety

- Dry-run-first and idempotent: re-running an applied change is a no-op.
- No confidential or customer data; the fixture is entirely fictional.
- Check readiness first with `python skills/sales/quote-flow/preflight.py`.
