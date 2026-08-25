---
name: response-draft
description: Draft a customer reply for a case to out/, never sending. USE WHEN you need a first-draft reply grounded in a case. DO NOT USE WHEN you want to write a KB article (use knowledge-draft).
---

# response-draft

Draft a customer reply for a case to out/, never sending.

Part of the Business Skill Kit. Runs against the synthetic fixture in `fixtures/org.json`
with zero real data. Reads are the default; any write is shown as a dry-run plan and applied
only with `--commit`, writing to `out/working.json` and never to the base fixture.

## Usage

```
python skills/service/response-draft/skill.py --case K001
```

Add `--json` for structured output, `--store <path>` to point at another store, and
`--working out/working.json` to read or extend an applied overlay.

## Inputs

- Required tables: case, contact
- Config comes from the environment only (see `.env.example`); no secrets in code.

## Safety

- Dry-run-first and idempotent: re-running an applied change is a no-op.
- No confidential or customer data; the fixture is entirely fictional.
- Check readiness first with `python skills/service/response-draft/preflight.py`.
