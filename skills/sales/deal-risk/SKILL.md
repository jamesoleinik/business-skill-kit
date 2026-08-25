---
name: deal-risk
description: Rank open opportunities by risk with an explained score. USE WHEN you want to know which open deals need attention. DO NOT USE WHEN you want a plain pipeline roll-up (use opportunity-catchup).
---

# deal-risk

Rank open opportunities by risk with an explained score.

Part of the Business Skill Kit. Runs against the synthetic fixture in `fixtures/org.json`
with zero real data. Reads are the default; any write is shown as a dry-run plan and applied
only with `--commit`, writing to `out/working.json` and never to the base fixture.

## Usage

```
python skills/sales/deal-risk/skill.py --threshold 40
```

Add `--json` for structured output, `--store <path>` to point at another store, and
`--working out/working.json` to read or extend an applied overlay.

## Inputs

- Required tables: opportunity
- Config comes from the environment only (see `.env.example`); no secrets in code.

## Safety

- Dry-run-first and idempotent: re-running an applied change is a no-op.
- No confidential or customer data; the fixture is entirely fictional.
- Check readiness first with `python skills/sales/deal-risk/preflight.py`.
