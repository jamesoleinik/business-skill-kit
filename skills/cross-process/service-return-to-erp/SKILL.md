---
name: service-return-to-erp
description: Turn an approved product return into an ERP credit. USE WHEN a resolved return case must be credited in ERP. DO NOT USE WHEN you just want to summarize the case (use case-summary).
---

# service-return-to-erp

Turn an approved product return into an ERP credit.

Part of the Business Skill Kit. Runs against the synthetic fixture in `fixtures/org.json`
with zero real data. Reads are the default; any write is shown as a dry-run plan and applied
only with `--commit`, writing to `out/working.json` and never to the base fixture.

## Usage

```
python skills/cross-process/service-return-to-erp/skill.py --case K004 --amount 210
```

Add `--json` for structured output, `--store <path>` to point at another store, and
`--working out/working.json` to read or extend an applied overlay.

## Inputs

- Required tables: case, account, erp_salesorder, erp_invoice
- Config comes from the environment only (see `.env.example`); no secrets in code.

## Safety

- Dry-run-first and idempotent: re-running an applied change is a no-op.
- No confidential or customer data; the fixture is entirely fictional.
- Check readiness first with `python skills/cross-process/service-return-to-erp/preflight.py`.
