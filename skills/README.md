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

Skills are organized by business domain. Each entry names the recurring job a
practitioner does today; the skill packages that job as an intent a coding agent can
run against the first-party surface, dry-run-first. The concrete tool binding for each
skill is kept in the private build notes; only generic skill categories ship here.

### Platform layer (Dataverse and Power Platform)
The data-and-automation foundation every domain skill builds on.

- **records**  read, query, and search business records; return grounded, cited results.
- **bulk-edit**  propose and apply a reviewed set of record changes, dry-run-first.
- **reconcile**  find and resolve duplicate or drifted records before a close.
- **model**  propose and apply table and column changes as a reviewed migration.
- **audit**  report who changed what, and flag sensitive-field access.
- **flow-scaffold**  propose a Power Automate flow for a repeatable business step.
- **app-surface**  outline a Power Apps screen over a skill's inputs and outputs.
- **agent-front**  draft a Copilot Studio topic that calls a skill as a tool.

### Sales
Move a deal forward with less manual work.

- **lead-qualify**  score and enrich a lead, then draft the next best action.
- **opportunity-catchup**  summarize what changed on an opportunity since last touch.
- **account-brief**  assemble a one-page account summary from related records.
- **deal-risk**  surface at-risk opportunities and the reason, with a suggested play.
- **quote-flow**  move a qualified opportunity through quote, order, and revision safely.

### Customer Service
Keep the queue clean and answers consistent.

- **case-triage**  cluster and prioritize the queue, flag SLA risk, draft responses.
- **case-summary**  summarize a case and its timeline for a fast handoff.
- **knowledge-draft**  turn a resolved case into a reviewed knowledge-article draft.
- **response-draft**  draft a grounded reply from case context and knowledge.

### Customer Insights (Marketing)
Reach the right audience without breaking consent.

- **segment-build**  define and refresh an audience segment from measures and traits.
- **journey-check**  validate and simulate a customer journey before it goes live.
- **campaign-report**  roll up channel, email, and journey performance into a brief.
- **consent-guard**  check consent, suppression, and frequency before any send.

### Finance and Operations
Do the operational jobs on trusted data.

- **entity-query**  read and report operational entities with a safe, explainable query.
- **entity-edit**  create or update operational records, dry-run-first and idempotent.
- **doc-attach**  attach and organize supporting documents against a record.

### Business Central
Small-business operations, same safety contract.

- **bc-record**  list, create, and update Business Central records safely.
- **bc-action**  discover and invoke a Business Central action with a dry run first.

Each entry becomes a real skill folder once it is built and validated against a
fixture. Nothing here is published until it passes the review gate.
