---
name: lead-qualify
description: Score inbound leads on fit and intent, then set score and status. USE WHEN you have new leads to score and qualify. DO NOT USE WHEN you want to convert a qualified lead into a deal (use lead-to-order).
---

# lead-qualify

Score inbound leads on fit and intent, then set score and status.

Part of the Business Skill Kit. Runs against the synthetic fixture in `fixtures/org.json`
with zero real data. Reads are the default; any write is shown as a dry-run plan and applied
only with `--commit`, writing to `out/working.json` and never to the base fixture.

## Usage

```
python skills/sales/lead-qualify/skill.py --threshold 50
```

Add `--json` for structured output, `--store <path>` to point at another store, and
`--working out/working.json` to read or extend an applied overlay.

## Inputs

- Required tables: lead
- Config comes from the environment only (see `.env.example`); no secrets in code.

## Safety

- Dry-run-first and idempotent: re-running an applied change is a no-op.
- No confidential or customer data; the fixture is entirely fictional.
- Check readiness first with `python skills/sales/lead-qualify/preflight.py`.
