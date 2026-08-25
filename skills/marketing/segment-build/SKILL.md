---
name: segment-build
description: Compute a segment's membership and refresh its count, dry-run-first. USE WHEN you need to (re)build a segment from its definition. DO NOT USE WHEN you want to check consent before sending (use consent-guard).
---

# segment-build

Compute a segment's membership and refresh its count, dry-run-first.

Part of the Business Skill Kit. Runs against the synthetic fixture in `fixtures/org.json`
with zero real data. Reads are the default; any write is shown as a dry-run plan and applied
only with `--commit`, writing to `out/working.json` and never to the base fixture.

## Usage

```
python skills/marketing/segment-build/skill.py --segment SEG1
```

Add `--json` for structured output, `--store <path>` to point at another store, and
`--working out/working.json` to read or extend an applied overlay.

## Inputs

- Required tables: segment, account
- Config comes from the environment only (see `.env.example`); no secrets in code.

## Safety

- Dry-run-first and idempotent: re-running an applied change is a no-op.
- No confidential or customer data; the fixture is entirely fictional.
- Check readiness first with `python skills/marketing/segment-build/preflight.py`.
