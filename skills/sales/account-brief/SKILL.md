---
name: account-brief
description: Assemble a one-page account brief before a call. USE WHEN you need a grounded briefing for a single account. DO NOT USE WHEN you need a pipeline-wide summary (use opportunity-catchup).
---

# account-brief

Assemble a one-page account brief before a call.

Part of the Business Skill Kit. Runs against the synthetic fixture in `fixtures/org.json`
with zero real data. Reads are the default; any write is shown as a dry-run plan and applied
only with `--commit`, writing to `out/working.json` and never to the base fixture.

## Usage

```
python skills/sales/account-brief/skill.py --account A001
```

Add `--json` for structured output, `--store <path>` to point at another store, and
`--working out/working.json` to read or extend an applied overlay.

## Inputs

- Required tables: account, contact, opportunity, case
- Config comes from the environment only (see `.env.example`); no secrets in code.

## Safety

- Dry-run-first and idempotent: re-running an applied change is a no-op.
- No confidential or customer data; the fixture is entirely fictional.
- Check readiness first with `python skills/sales/account-brief/preflight.py`.
