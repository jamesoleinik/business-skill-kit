---
name: consent-guard
description: Split contacts into mailable and blocked by consent before any send. USE WHEN you are about to send and must respect consent. DO NOT USE WHEN you want to build the audience (use segment-build).
---

# consent-guard

Split contacts into mailable and blocked by consent before any send.

Part of the Business Skill Kit. Runs against the synthetic fixture in `fixtures/org.json`
with zero real data. Reads are the default; any write is shown as a dry-run plan and applied
only with `--commit`, writing to `out/working.json` and never to the base fixture.

## Usage

```
python skills/marketing/consent-guard/skill.py
```

Add `--json` for structured output, `--store <path>` to point at another store, and
`--working out/working.json` to read or extend an applied overlay.

## Inputs

- Required tables: contact
- Config comes from the environment only (see `.env.example`); no secrets in code.

## Safety

- Dry-run-first and idempotent: re-running an applied change is a no-op.
- No confidential or customer data; the fixture is entirely fictional.
- Check readiness first with `python skills/marketing/consent-guard/preflight.py`.
