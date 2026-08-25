---
name: case-triage
description: Rank the active case queue by SLA, priority, and age. USE WHEN an agent needs to know which case to work next. DO NOT USE WHEN you want a deep summary of one case (use case-summary).
---

# case-triage

Rank the active case queue by SLA, priority, and age.

Part of the Business Skill Kit. Runs against the synthetic fixture in `fixtures/org.json`
with zero real data. Reads are the default; any write is shown as a dry-run plan and applied
only with `--commit`, writing to `out/working.json` and never to the base fixture.

## Usage

```
python skills/service/case-triage/skill.py
```

Add `--json` for structured output, `--store <path>` to point at another store, and
`--working out/working.json` to read or extend an applied overlay.

## Inputs

- Required tables: case
- Config comes from the environment only (see `.env.example`); no secrets in code.

## Safety

- Dry-run-first and idempotent: re-running an applied change is a no-op.
- No confidential or customer data; the fixture is entirely fictional.
- Check readiness first with `python skills/service/case-triage/preflight.py`.
