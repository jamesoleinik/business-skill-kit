# Skills

Each skill is a self-contained folder that does one business job across the portfolio,
safely and testably. Skills are grouped by the portfolio area whose data and logic
they touch.

## The shared shape

```
skills/<domain>/<slug>/
  SKILL.md       the business job, when to use it (and when not), inputs and outputs
  preflight.py   read-only readiness check; exits non-zero when the store is not ready
  skill.py       the skill itself: read-only or dry-run-first, idempotent
```

Every skill runs on the shared [`bskit`](../bskit/) engine against one synthetic company
fixture, [`fixtures/org.json`](../fixtures/org.json), so it can be tried and tested with
zero real business data. Reads run against the base fixture; any write is computed as a
plan and applied only with `--commit`, landing in `out/working.json` and never touching
the base fixture.

## Quick start

```
python preflight.py                                   # the fixture loads
python validate.py                                    # every skill runs (69 checks)

python skills/sales/account-brief/skill.py --account A001
python skills/service/case-triage/skill.py
python skills/cross-process/quote-to-cash/skill.py --order S005            # dry run
python skills/cross-process/quote-to-cash/skill.py --order S005 --commit   # apply
```

Common flags on every skill: `--json` for structured output, `--commit` to apply a write
skill's plan, `--store <path>` to point at another store, and `--working out/working.json`
to read or extend an applied overlay.

## The safety contract

Every skill honors the same contract (see [`../AGENTS.md`](../AGENTS.md)):

1. Read-only by default; any write is dry-run-first and asks before it changes data.
2. Idempotent writes (upsert by alternate key), so a re-run is safe.
3. No secrets and no confidential content committed; configuration comes from the
   environment.
4. Validated against its synthetic fixture before it ships.

## Catalog

Skills are organized by business domain. Each entry names the recurring job a
practitioner does today; the skill packages that job as an intent a coding agent can
run against the first-party surface, dry-run-first. The concrete tool binding for each
skill is kept in the private build notes; only generic skill categories ship here. All
30 skills below are built and validated against the fixture.

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

### Cross-process (CRM to ERP)
The flagship of the kit: skills that span application processes end to end, keeping CRM
and ERP in agreement.

- **quote-to-cash**  drive a won CRM sales order to an ERP invoice across the whole chain.
- **lead-to-order**  promote a qualified lead into an opportunity, creating the account if needed.
- **service-return-to-erp**  turn an approved product return into an ERP credit.
- **master-data-sync**  align CRM accounts with ERP customers and flag orphans.

Each entry is a real skill folder, built and validated against the fixture by
[`validate.py`](../validate.py). Nothing is published until it passes the review gate.
