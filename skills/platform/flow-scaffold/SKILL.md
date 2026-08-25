---
name: flow-scaffold
description: Scaffold an automation definition to out/ for review. USE WHEN you want a starting automation/flow definition as a file artifact. DO NOT USE WHEN you want to execute an automation (out of scope; this only drafts).
---

# flow-scaffold

Scaffold an automation definition to out/ for review.

Part of the Business Skill Kit. Runs against the synthetic fixture in `fixtures/org.json`
with zero real data. Reads are the default; any write is shown as a dry-run plan and applied
only with `--commit`, writing to `out/working.json` and never to the base fixture.

## Usage

```
python skills/platform/flow-scaffold/skill.py --name nightly-sync
```

Add `--json` for structured output, `--store <path>` to point at another store, and
`--working out/working.json` to read or extend an applied overlay.

## Inputs

- Required tables: account
- Config comes from the environment only (see `.env.example`); no secrets in code.

## Safety

- Dry-run-first and idempotent: re-running an applied change is a no-op.
- No confidential or customer data; the fixture is entirely fictional.
- Check readiness first with `python skills/platform/flow-scaffold/preflight.py`.
