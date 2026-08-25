---
name: agent-front
description: Draft an agent front-door spec (topics and grounded actions) to out/. USE WHEN you want to scaffold an agent that fronts these skills. DO NOT USE WHEN you want to run the agent (this only drafts the spec).
---

# agent-front

Draft an agent front-door spec (topics and grounded actions) to out/.

Part of the Business Skill Kit. Runs against the synthetic fixture in `fixtures/org.json`
with zero real data. Reads are the default; any write is shown as a dry-run plan and applied
only with `--commit`, writing to `out/working.json` and never to the base fixture.

## Usage

```
python skills/platform/agent-front/skill.py --skill lead-qualify
```

Add `--json` for structured output, `--store <path>` to point at another store, and
`--working out/working.json` to read or extend an applied overlay.

## Inputs

- Required tables: account
- Config comes from the environment only (see `.env.example`); no secrets in code.

## Safety

- Dry-run-first and idempotent: re-running an applied change is a no-op.
- No confidential or customer data; the fixture is entirely fictional.
- Check readiness first with `python skills/platform/agent-front/preflight.py`.
