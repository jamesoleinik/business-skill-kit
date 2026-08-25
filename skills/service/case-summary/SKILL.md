---
name: case-summary
description: Summarize a single case with its account, contact, and next action. USE WHEN you need a grounded summary of one case. DO NOT USE WHEN you need to rank the whole queue (use case-triage).
---

# case-summary

Summarize a single case with its account, contact, and next action.

Part of the Business Skill Kit. Runs against the synthetic fixture in `fixtures/org.json`
with zero real data. Reads are the default; any write is shown as a dry-run plan and applied
only with `--commit`, writing to `out/working.json` and never to the base fixture.

## Usage

```
python skills/service/case-summary/skill.py --case K001
```

Add `--json` for structured output, `--store <path>` to point at another store, and
`--working out/working.json` to read or extend an applied overlay.

## Inputs

- Required tables: case, account, contact
- Config comes from the environment only (see `.env.example`); no secrets in code.

## Safety

- Dry-run-first and idempotent: re-running an applied change is a no-op.
- No confidential or customer data; the fixture is entirely fictional.
- Check readiness first with `python skills/service/case-summary/preflight.py`.
