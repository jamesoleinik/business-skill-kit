---
name: campaign-report
description: Roll up message open and click performance across channels. USE WHEN you want a performance roll-up across messages. DO NOT USE WHEN you want to validate journeys (use journey-check).
---

# campaign-report

Roll up message open and click performance across channels.

Part of the Business Skill Kit. Runs against the synthetic fixture in `fixtures/org.json`
with zero real data. Reads are the default; any write is shown as a dry-run plan and applied
only with `--commit`, writing to `out/working.json` and never to the base fixture.

## Usage

```
python skills/marketing/campaign-report/skill.py
```

Add `--json` for structured output, `--store <path>` to point at another store, and
`--working out/working.json` to read or extend an applied overlay.

## Inputs

- Required tables: emailmsg
- Config comes from the environment only (see `.env.example`); no secrets in code.

## Safety

- Dry-run-first and idempotent: re-running an applied change is a no-op.
- No confidential or customer data; the fixture is entirely fictional.
- Check readiness first with `python skills/marketing/campaign-report/preflight.py`.
