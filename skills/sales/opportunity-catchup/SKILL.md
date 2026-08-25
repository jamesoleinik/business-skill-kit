---
name: opportunity-catchup
description: Summarize the open pipeline by stage, owner, and forecast. USE WHEN you want a fast standup view of the open pipeline. DO NOT USE WHEN you want to rank deals by risk (use deal-risk).
---

# opportunity-catchup

Summarize the open pipeline by stage, owner, and forecast.

Part of the Business Skill Kit. Runs against the synthetic fixture in `fixtures/org.json`
with zero real data. Reads are the default; any write is shown as a dry-run plan and applied
only with `--commit`, writing to `out/working.json` and never to the base fixture.

## Usage

```
python skills/sales/opportunity-catchup/skill.py
```

Add `--json` for structured output, `--store <path>` to point at another store, and
`--working out/working.json` to read or extend an applied overlay.

## Inputs

- Required tables: opportunity
- Config comes from the environment only (see `.env.example`); no secrets in code.

## Safety

- Dry-run-first and idempotent: re-running an applied change is a no-op.
- No confidential or customer data; the fixture is entirely fictional.
- Check readiness first with `python skills/sales/opportunity-catchup/preflight.py`.
