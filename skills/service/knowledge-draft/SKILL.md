---
name: knowledge-draft
description: Turn a resolved case into a draft knowledge article in out/. USE WHEN a resolved case is worth capturing as knowledge. DO NOT USE WHEN you want to reply to a customer (use response-draft).
---

# knowledge-draft

Turn a resolved case into a draft knowledge article in out/.

Part of the Business Skill Kit. Runs against the synthetic fixture in `fixtures/org.json`
with zero real data. Reads are the default; any write is shown as a dry-run plan and applied
only with `--commit`, writing to `out/working.json` and never to the base fixture.

## Usage

```
python skills/service/knowledge-draft/skill.py --case K004
```

Add `--json` for structured output, `--store <path>` to point at another store, and
`--working out/working.json` to read or extend an applied overlay.

## Inputs

- Required tables: case
- Config comes from the environment only (see `.env.example`); no secrets in code.

## Safety

- Dry-run-first and idempotent: re-running an applied change is a no-op.
- No confidential or customer data; the fixture is entirely fictional.
- Check readiness first with `python skills/service/knowledge-draft/preflight.py`.
