---
name: records
description: Read, query, and search business records with grounded, cited results. USE WHEN you need to look up or search records across any table. DO NOT USE WHEN you need to change data (use bulk-edit or a domain write skill).
---

# records

Read, query, and search business records with grounded, cited results.

Part of the Business Skill Kit. Runs against the synthetic fixture in `fixtures/org.json`
with zero real data. Reads are the default; any write is shown as a dry-run plan and applied
only with `--commit`, writing to `out/working.json` and never to the base fixture.

## Usage

```
python skills/platform/records/skill.py --table account --top 5
```

Add `--json` for structured output, `--store <path>` to point at another store, and
`--working out/working.json` to read or extend an applied overlay.

## Inputs

- Required tables: account
- Config comes from the environment only (see `.env.example`); no secrets in code.

## Safety

- Dry-run-first and idempotent: re-running an applied change is a no-op.
- No confidential or customer data; the fixture is entirely fictional.
- Check readiness first with `python skills/platform/records/preflight.py`.
