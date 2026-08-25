---
name: journey-check
description: Pre-flight customer journeys and return a go/no-go list. USE WHEN you want to validate journeys before they run. DO NOT USE WHEN you want message performance (use campaign-report).
---

# journey-check

Pre-flight customer journeys and return a go/no-go list.

Part of the Business Skill Kit. Runs against the synthetic fixture in `fixtures/org.json`
with zero real data. Reads are the default; any write is shown as a dry-run plan and applied
only with `--commit`, writing to `out/working.json` and never to the base fixture.

## Usage

```
python skills/marketing/journey-check/skill.py
```

Add `--json` for structured output, `--store <path>` to point at another store, and
`--working out/working.json` to read or extend an applied overlay.

## Inputs

- Required tables: journey, segment
- Config comes from the environment only (see `.env.example`); no secrets in code.

## Safety

- Dry-run-first and idempotent: re-running an applied change is a no-op.
- No confidential or customer data; the fixture is entirely fictional.
- Check readiness first with `python skills/marketing/journey-check/preflight.py`.
