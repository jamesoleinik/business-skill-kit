# Skills

Each skill is a self-contained folder that does one business job across the portfolio,
safely and testably. Skills are grouped by the portfolio area whose data and logic
they touch.

## The shared shape

```
skills/<slug>/
  SKILL.md       the business job, when to use it (and when not), inputs and outputs
  preflight.py   read-only readiness check; exits non-zero when the env is not ready
  <scripts>      the skill itself: read-only or dry-run-first, idempotent
  fixtures/      a synthetic dataset so the skill runs with zero real business data
```

## The safety contract

Every skill honors the same contract (see [`../AGENTS.md`](../AGENTS.md)):

1. Read-only by default; any write is dry-run-first and asks before it changes data.
2. Idempotent writes (upsert by alternate key), so a re-run is safe.
3. No secrets and no confidential content committed; configuration comes from the
   environment.
4. Validated against its synthetic fixture before it ships.

## Catalog (draft)

The concrete tool surface behind each area is mapped privately from the first-party
server inventory. The public catalog lists generic skill categories only.

### Dataverse (the business records)
- bulk-edit  propose and apply a reviewed set of record changes, dry-run-first.
- reconcile  find and resolve duplicate or drifted records before a close.
- audit  report who changed what, and flag sensitive-field access.

### Dynamics 365 (the domain jobs)
- lead-qualify  score and enrich a lead, then draft the next best action.
- case-triage  cluster and prioritize the service queue, draft responses.
- account-brief  assemble a one-page account summary from related records.

### Power Platform (automate, surface, and front with an agent)
- flow-scaffold  propose a Power Automate flow for a repeatable business step.
- app-surface  outline a Power Apps screen over a skill's inputs and outputs.
- agent-front  draft a Copilot Studio topic that calls a skill as a tool.

Each entry becomes a real skill folder once it is built and validated against a
fixture. Nothing here is published until it passes the review gate.
