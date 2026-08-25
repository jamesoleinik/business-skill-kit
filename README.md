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
| Dynamics 365 | the domain jobs on top of that data: sales, service, field, finance and operations | model-driven apps and business logic over the same environment |
| Power Platform | automate the steps, surface them in an app, and put an agent in front | Power Automate, Power Apps, Copilot Studio |

Dynamics 365 apps and Dataverse share one unified environment (the Power Platform
unified experience); the kit treats them as one data-and-logic layer, not separate
stores.

## The shape of a skill

Every skill is a self-contained folder under [`skills/`](skills/):

- `SKILL.md`  the business job it does, when to use it (and when not to), and its
  inputs and outputs.
- `preflight.py`  a read-only check that the skill can run (auth works, the
  environment is reachable, prerequisites present). Exits non-zero when not ready.
- one or more scripts  the skill itself, read-only or dry-run-first, idempotent.
- a fixture  a synthetic dataset so the skill can be tried and tested with zero real
  business data.

See [`skills/README.md`](skills/README.md) for the shared shape and the safety
contract every skill honors.

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

Scaffolded. The skill catalog is being built up area by area from the private
first-party surface map; it stays private until it passes the publish review gate.

## License

MIT. See [LICENSE](LICENSE).
