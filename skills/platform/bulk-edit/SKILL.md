---
name: bulk-edit
description: Propose and apply a reviewed set of field changes, dry-run-first. USE WHEN you need to set one or more fields across a filtered set of records. DO NOT USE WHEN you only need to read (use records).
---

# bulk-edit

Propose and apply a reviewed set of field changes, dry-run-first.

Part of the Business Skill Kit. Runs against the synthetic fixture in `fixtures/org.json`
with zero real data. Reads are the default; any write is shown as a dry-run plan and applied
only with `--commit`, writing to `out/working.json` and never to the base fixture.

## Usage

```
python skills/platform/bulk-edit/skill.py --table lead --where status=new --set status=qualified
```

Add `--json` for structured output, `--store <path>` to point at another store, and
`--working out/working.json` to read or extend an applied overlay.

## Inputs

- Required tables: lead
- Config comes from the environment only (see `.env.example`); no secrets in code.

## Safety

- Dry-run-first and idempotent: re-running an applied change is a no-op.
- No confidential or customer data; the fixture is entirely fictional.
- Check readiness first with `python skills/platform/bulk-edit/preflight.py`.
