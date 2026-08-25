---
name: lead-to-order
description: Promote a qualified lead into an opportunity, creating the account if needed. USE WHEN a qualified lead should become a pipeline opportunity. DO NOT USE WHEN you only need to score the lead (use lead-qualify).
---

# lead-to-order

Promote a qualified lead into an opportunity, creating the account if needed.

Part of the Business Skill Kit. Runs against the synthetic fixture in `fixtures/org.json`
with zero real data. Reads are the default; any write is shown as a dry-run plan and applied
only with `--commit`, writing to `out/working.json` and never to the base fixture.

## Usage

```
python skills/cross-process/lead-to-order/skill.py --lead L003
```

Add `--json` for structured output, `--store <path>` to point at another store, and
`--working out/working.json` to read or extend an applied overlay.

## Inputs

- Required tables: lead, account, opportunity
- Config comes from the environment only (see `.env.example`); no secrets in code.

## Safety

- Dry-run-first and idempotent: re-running an applied change is a no-op.
- No confidential or customer data; the fixture is entirely fictional.
- Check readiness first with `python skills/cross-process/lead-to-order/preflight.py`.
