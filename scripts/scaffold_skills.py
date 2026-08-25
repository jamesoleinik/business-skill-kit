"""Generate a SKILL.md and preflight.py for every skill from one spec registry.

Keeping the specs in a single place means every skill's front matter, required tables, and
usage line stay consistent. Run:

    python scripts/scaffold_skills.py

It writes skills/<domain>/<slug>/SKILL.md and skills/<domain>/<slug>/preflight.py. It never
overwrites skill.py.
"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# domain, slug, title, summary, tables, use_when, not_when, usage
SPECS = [
    # ---- platform ----
    ("platform", "records", "records", "Read, query, and search business records with grounded, cited results.",
     ["account"], "you need to look up or search records across any table",
     "you need to change data (use bulk-edit or a domain write skill)",
     "python skills/platform/records/skill.py --table account --top 5"),
    ("platform", "bulk-edit", "bulk-edit", "Propose and apply a reviewed set of field changes, dry-run-first.",
     ["lead"], "you need to set one or more fields across a filtered set of records",
     "you only need to read (use records)",
     "python skills/platform/bulk-edit/skill.py --table lead --where status=new --set status=qualified"),
    ("platform", "reconcile", "reconcile", "Find duplicate or drifted records and propose fixes before a close.",
     ["account", "erp_customer"], "you want a data-quality pass before reporting or a close",
     "you want to align CRM and ERP master data end to end (use master-data-sync)",
     "python skills/platform/reconcile/skill.py --table account"),
    ("platform", "model", "model", "Inspect a table's shape and stage a schema-style change, dry-run-first.",
     ["account"], "you need to understand or evolve the shape of a table",
     "you need to edit record values (use bulk-edit)",
     "python skills/platform/model/skill.py --add-column account:region=unknown"),
    ("platform", "audit", "audit", "Report what changed in the working copy for review and rollback.",
     ["account"], "you want to see the audit trail of applied dry-run changes",
     "you want to make changes (use a write skill)",
     "python skills/platform/audit/skill.py"),
    ("platform", "flow-scaffold", "flow-scaffold", "Scaffold an automation definition to out/ for review.",
     ["account"], "you want a starting automation/flow definition as a file artifact",
     "you want to execute an automation (out of scope; this only drafts)",
     "python skills/platform/flow-scaffold/skill.py --name nightly-sync"),
    ("platform", "app-surface", "app-surface", "Describe an app's surface (tables and views) as a portable spec.",
     ["account"], "you want a portable description of an app surface",
     "you want to change data or schema",
     "python skills/platform/app-surface/skill.py"),
    ("platform", "agent-front", "agent-front", "Draft an agent front-door spec (topics and grounded actions) to out/.",
     ["account"], "you want to scaffold an agent that fronts these skills",
     "you want to run the agent (this only drafts the spec)",
     "python skills/platform/agent-front/skill.py --skill lead-qualify"),
    # ---- sales ----
    ("sales", "lead-qualify", "lead-qualify", "Score inbound leads on fit and intent, then set score and status.",
     ["lead"], "you have new leads to score and qualify",
     "you want to convert a qualified lead into a deal (use lead-to-order)",
     "python skills/sales/lead-qualify/skill.py --threshold 50"),
    ("sales", "opportunity-catchup", "opportunity-catchup", "Summarize the open pipeline by stage, owner, and forecast.",
     ["opportunity"], "you want a fast standup view of the open pipeline",
     "you want to rank deals by risk (use deal-risk)",
     "python skills/sales/opportunity-catchup/skill.py"),
    ("sales", "account-brief", "account-brief", "Assemble a one-page account brief before a call.",
     ["account", "contact", "opportunity", "case"], "you need a grounded briefing for a single account",
     "you need a pipeline-wide summary (use opportunity-catchup)",
     "python skills/sales/account-brief/skill.py --account A001"),
    ("sales", "deal-risk", "deal-risk", "Rank open opportunities by risk with an explained score.",
     ["opportunity"], "you want to know which open deals need attention",
     "you want a plain pipeline roll-up (use opportunity-catchup)",
     "python skills/sales/deal-risk/skill.py --threshold 40"),
    ("sales", "quote-flow", "quote-flow", "Advance a won opportunity to a quote and CRM sales order, dry-run-first.",
     ["opportunity", "quote", "salesorder"], "a deal is won and you need the quote and CRM order staged",
     "you need to push the order to ERP and invoice (use quote-to-cash)",
     "python skills/sales/quote-flow/skill.py --opp O005"),
    # ---- service ----
    ("service", "case-triage", "case-triage", "Rank the active case queue by SLA, priority, and age.",
     ["case"], "an agent needs to know which case to work next",
     "you want a deep summary of one case (use case-summary)",
     "python skills/service/case-triage/skill.py"),
    ("service", "case-summary", "case-summary", "Summarize a single case with its account, contact, and next action.",
     ["case", "account", "contact"], "you need a grounded summary of one case",
     "you need to rank the whole queue (use case-triage)",
     "python skills/service/case-summary/skill.py --case K001"),
    ("service", "knowledge-draft", "knowledge-draft", "Turn a resolved case into a draft knowledge article in out/.",
     ["case"], "a resolved case is worth capturing as knowledge",
     "you want to reply to a customer (use response-draft)",
     "python skills/service/knowledge-draft/skill.py --case K004"),
    ("service", "response-draft", "response-draft", "Draft a customer reply for a case to out/, never sending.",
     ["case", "contact"], "you need a first-draft reply grounded in a case",
     "you want to write a KB article (use knowledge-draft)",
     "python skills/service/response-draft/skill.py --case K001"),
    # ---- marketing ----
    ("marketing", "segment-build", "segment-build", "Compute a segment's membership and refresh its count, dry-run-first.",
     ["segment", "account"], "you need to (re)build a segment from its definition",
     "you want to check consent before sending (use consent-guard)",
     "python skills/marketing/segment-build/skill.py --segment SEG1"),
    ("marketing", "journey-check", "journey-check", "Pre-flight customer journeys and return a go/no-go list.",
     ["journey", "segment"], "you want to validate journeys before they run",
     "you want message performance (use campaign-report)",
     "python skills/marketing/journey-check/skill.py"),
    ("marketing", "campaign-report", "campaign-report", "Roll up message open and click performance across channels.",
     ["emailmsg"], "you want a performance roll-up across messages",
     "you want to validate journeys (use journey-check)",
     "python skills/marketing/campaign-report/skill.py"),
    ("marketing", "consent-guard", "consent-guard", "Split contacts into mailable and blocked by consent before any send.",
     ["contact"], "you are about to send and must respect consent",
     "you want to build the audience (use segment-build)",
     "python skills/marketing/consent-guard/skill.py"),
    # ---- finance ----
    ("finance", "entity-query", "entity-query", "Read any data entity with an explainable filter.",
     ["account"], "you need an auditable read of any entity",
     "you need to write (use entity-edit)",
     "python skills/finance/entity-query/skill.py --entity erp_invoice"),
    ("finance", "entity-edit", "entity-edit", "Create or update a record in any entity, dry-run-first.",
     ["account"], "you need to change one record in any entity",
     "you only need to read (use entity-query)",
     "python skills/finance/entity-edit/skill.py --entity erp_invoice --id N-7004 --set status=paid"),
    ("finance", "doc-attach", "doc-attach", "Record a document attachment against a record via a manifest in out/.",
     ["account"], "you need to log a document linkage to a record",
     "you need to change the record's business fields (use entity-edit)",
     "python skills/finance/doc-attach/skill.py --entity erp_invoice --id N-7004 --name invoice.pdf"),
    # ---- business central ----
    ("business-central", "bc-record", "bc-record", "List, create, or update a Business Central item, dry-run-first.",
     ["bc_item"], "you need to read or edit Business Central items",
     "you need to invoke an item action (use bc-action)",
     "python skills/business-central/bc-record/skill.py"),
    ("business-central", "bc-action", "bc-action", "Discover and dry-run a Business Central item action.",
     ["bc_item"], "you need to run a bounded item action like adjust-inventory",
     "you need a plain create/update (use bc-record)",
     "python skills/business-central/bc-action/skill.py --action adjust-inventory --id B001 --by -5"),
    # ---- cross-process ----
    ("cross-process", "quote-to-cash", "quote-to-cash", "Drive a CRM sales order to an ERP invoice across the whole chain, dry-run-first.",
     ["salesorder", "erp_salesorder", "erp_invoice", "account"], "a won order must flow from CRM through ERP to an invoice",
     "you only need the CRM-side quote and order (use quote-flow)",
     "python skills/cross-process/quote-to-cash/skill.py --order S005"),
    ("cross-process", "lead-to-order", "lead-to-order", "Promote a qualified lead into an opportunity, creating the account if needed.",
     ["lead", "account", "opportunity"], "a qualified lead should become a pipeline opportunity",
     "you only need to score the lead (use lead-qualify)",
     "python skills/cross-process/lead-to-order/skill.py --lead L003"),
    ("cross-process", "service-return-to-erp", "service-return-to-erp", "Turn an approved product return into an ERP credit.",
     ["case", "account", "erp_salesorder", "erp_invoice"], "a resolved return case must be credited in ERP",
     "you just want to summarize the case (use case-summary)",
     "python skills/cross-process/service-return-to-erp/skill.py --case K004 --amount 210"),
    ("cross-process", "master-data-sync", "master-data-sync", "Align CRM accounts with ERP customers and flag orphans, dry-run-first.",
     ["account", "erp_customer"], "CRM and ERP master data may have drifted or lost links",
     "you only want an in-table duplicate check (use reconcile)",
     "python skills/cross-process/master-data-sync/skill.py"),
]

SKILL_MD = """---
name: {slug}
description: {summary} USE WHEN {use_when}. DO NOT USE WHEN {not_when}.
---

# {title}

{summary}

Part of the Business Skill Kit. Runs against the synthetic fixture in `fixtures/org.json`
with zero real data. Reads are the default; any write is shown as a dry-run plan and applied
only with `--commit`, writing to `out/working.json` and never to the base fixture.

## Usage

```
{usage}
```

Add `--json` for structured output, `--store <path>` to point at another store, and
`--working out/working.json` to read or extend an applied overlay.

## Inputs

- Required tables: {tables}
- Config comes from the environment only (see `.env.example`); no secrets in code.

## Safety

- Dry-run-first and idempotent: re-running an applied change is a no-op.
- No confidential or customer data; the fixture is entirely fictional.
- Check readiness first with `python skills/{domain}/{slug}/preflight.py`.
"""

PREFLIGHT = '''"""Readiness check for the {slug} skill: confirms the store and required tables exist."""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
import bskit.skill as sk  # noqa: E402

REQUIRED = {tables!r}

if __name__ == "__main__":
    sk.preflight_main(REQUIRED)
'''


def main():
    for domain, slug, title, summary, tables, use_when, not_when, usage in SPECS:
        d = os.path.join(ROOT, "skills", domain, slug)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "SKILL.md"), "w", encoding="utf-8") as f:
            f.write(SKILL_MD.format(slug=slug, title=title, summary=summary, use_when=use_when,
                                    not_when=not_when, usage=usage, tables=", ".join(tables), domain=domain))
        with open(os.path.join(d, "preflight.py"), "w", encoding="utf-8") as f:
            f.write(PREFLIGHT.format(slug=slug, tables=tables))
    print("generated SKILL.md and preflight.py for %d skills" % len(SPECS))


if __name__ == "__main__":
    main()
