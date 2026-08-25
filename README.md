# Business Skill Kit

Reusable, safe, testable AI skills for real business work across the Microsoft
business-applications portfolio: Dynamics 365, Dataverse, and the Power Platform.
Describe a business outcome ("qualify this lead and draft the follow-up", "triage
today's cases", "reconcile these records before the month-end close") and let a
coding agent drive the first-party tools to do it, with the guardrails that make it
safe to run against real data.

Written by [James Oleinik](https://github.com/jamesoleinik). Personal and
open-source. Not official Microsoft documentation. Private and in active development.

## The idea

Business users do not want to invoke tools by hand. They want an outcome. A seller
wants a qualified pipeline, a service agent wants a clean queue, an operations lead
wants trustworthy data before a close. Each of those is a repeatable job that spans
several first-party surfaces: records in Dataverse, business logic in Dynamics 365,
and automation and apps in the Power Platform.

Business Skill Kit is a template plus a growing set of example skills for exactly that
loop. You describe intent, the agent selects the right first-party tool (the Dataverse
MCP server, the Dataverse Web API, Power Automate, Power Apps, Copilot Studio), you
review the proposed change, and it goes through source control. Every skill is small,
self-contained, testable against a fixture, and dry-run-first.

## The portfolio it spans

The kit organizes skills by the portfolio area whose data and logic they touch. The
concrete tool surface for each area is mapped privately from the first-party server
inventory; only generic, non-confidential skill categories ship here.

| Area | The business jobs | First-party surface |
|------|-------------------|---------------------|
| Dataverse | model, query, bulk-edit, reconcile, and audit the business records | Dataverse MCP server, Web API, SDK |
| Dynamics 365 Sales | qualify leads, brief accounts, catch up and de-risk opportunities, run quotes | model-driven Sales over the shared environment |
| Dynamics 365 Customer Service | triage the queue, summarize cases, draft grounded responses and knowledge | model-driven Customer Service over the shared environment |
| Dynamics 365 Customer Insights | build segments, validate journeys, report campaigns, guard consent | Customer Insights data and journeys |
| Finance, Operations, and Business Central | read and edit operational entities and documents on trusted data | Finance and Operations and Business Central |
| Power Platform | automate the steps, surface them in an app, and put an agent in front | Power Automate, Power Apps, Copilot Studio |
| Cross-process (CRM to ERP) | quote-to-cash, lead-to-order, returns-to-credit, and master-data sync spanning apps | the links between Dynamics 365 CRM and ERP |

Dynamics 365 apps and Dataverse share one unified environment (the Power Platform
unified experience); the kit treats them as one data-and-logic layer, not separate
stores.

## The shape of a skill

Every skill is a self-contained folder under [`skills/<domain>/`](skills/):

- `SKILL.md`  the business job it does, when to use it (and when not to), and its
  inputs and outputs.
- `preflight.py`  a read-only check that the skill can run (the store loads, required
  tables are present). Exits non-zero when not ready.
- `skill.py`  the skill itself, read-only or dry-run-first, idempotent.

All 30 skills share one small engine, [`bskit`](bskit/), and one synthetic company
fixture, [`fixtures/org.json`](fixtures/org.json), so every skill can be tried and tested
with zero real business data. Reads run against the base fixture; a write is shown as a
plan and applied only with `--commit`, writing to `out/working.json` and never mutating
the base.

See [`skills/README.md`](skills/README.md) for the full catalog and the safety contract
every skill honors.

## Quick start

Python 3.8+, standard library only. No install step.

```
python preflight.py     # the fixture loads and the engine imports
python validate.py      # runs every skill against the fixture (69 checks)

# read and summarize
python skills/sales/account-brief/skill.py --account A001
python skills/service/case-triage/skill.py

# a cross-process job: won CRM order all the way to an ERP invoice
python skills/cross-process/quote-to-cash/skill.py --order S005            # dry run
python skills/cross-process/quote-to-cash/skill.py --order S005 --commit   # apply
```

Regenerate the fixture any time with `python fixtures/make_fixture.py`, and the per-skill
`SKILL.md` and `preflight.py` with `python scripts/scaffold_skills.py`.

## Guardrails

These run through every skill in the kit, and are spelled out in
[`AGENTS.md`](AGENTS.md):

- **Read-only by default.** A skill that can change business data shows what it would
  change and asks for confirmation before it writes. Reads never mutate.
- **Idempotent writes.** Re-running a skill does not create duplicates or corrupt
  state. Writes upsert by alternate key.
- **No secrets in code.** Configuration (environment URL, auth profile) comes from
  environment variables; no `.env`, token, or real org URL is ever committed.
- **Validate before you claim.** Every skill runs against its synthetic fixture before
  it ships, and against a live environment where feasible.
- **No confidential content.** Only generic skill categories and synthetic fixtures
  are committed. Internal inventories, real environment URLs, tenant or org IDs, and
  user identities never appear here.

## Status

In active development, private. All 30 skills across seven domains (platform, sales,
service, marketing, finance, Business Central, and cross-process) are built and pass
`validate.py` against the synthetic fixture. The concrete first-party tool binding for
each skill is mapped in private build notes; it stays private until it passes the publish
review gate.

## License

MIT. See [LICENSE](LICENSE).
