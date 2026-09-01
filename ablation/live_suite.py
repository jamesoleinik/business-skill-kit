"""Generalized LIVE ablation suite: run several skills against a real Dataverse org.

This is the multi-skill generalization of live_ablation.py. For each skill spec it:

  1. reads the seeded rows for every table the skill needs, through the MCP server
     (read_query), filtered by the seed tag,
  2. maps the live Dataverse columns onto the field names the skill's Store expects
     (build a snapshot), pointing the harness at that snapshot (harness.set_store_path),
  3. runs the identical with-skill / without-skill conditions, judge, stats, and report.

Ground truth is derived from the seeded roles (e.g. the opted-in vs. non-consented contact,
the breached-high case), not from the skill's own output, so each assertion is an independent
acceptance test. The with condition (skill loaded) must produce the derived result; the
without condition (raw table rows, no procedure) cannot, and that gap is the ablation signal.

Every skill runs dry-run (no --commit); this never writes back to the live environment.
Nothing is hardcoded to an org: pass --url and --token-file (see live-agent/signin.py).

Usage (from repo root):
    python ablation/live_suite.py \
        --url https://<org>.crm.dynamics.com/api/mcp_preview \
        --token-file build-notes/<org>-token.json \
        --tag "zzz-bskit-seed" --n 3 --out ablation/reports/live-suite.md
Optionally restrict to some skills: --only consent-guard,case-triage
"""
import argparse
import datetime
import importlib.util
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from ablation import harness, judge, report as report_mod, stats  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "mcp_probe", os.path.join(ROOT, "live-agent", "mcp_probe.py"))
mcp_probe = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mcp_probe)


def _text(res):
    try:
        return res["result"]["content"][0]["text"]
    except (KeyError, IndexError, TypeError):
        return json.dumps(res)


def _as_bool(v):
    return v in (True, 1, "1", "true", "True")


def _as_int(v, default=0):
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def _days_since(iso):
    if not iso:
        return 0
    try:
        d = datetime.datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
        if d.tzinfo is None:
            d = d.replace(tzinfo=datetime.timezone.utc)
        now = datetime.datetime.now(datetime.timezone.utc)
        return max(0, (now - d).days)
    except ValueError:
        return 0


_PRIORITY = {1: "high", 2: "normal", 3: "low"}
_STATECODE = {0: "active", 1: "resolved", 2: "cancelled"}
_OPP_STATE = {0: "open", 1: "won", 2: "lost"}
_STAGE = {0: "qualify", 1: "develop", 2: "propose", 3: "close"}


# ---- live-column -> fixture-field maps (generic; no environment specifics) --------------

def _map_contact(r):
    return {
        "id": r["contactid"],
        "name": (" ".join(x for x in (r.get("firstname"), r.get("lastname")) if x)).strip(),
        "email": r.get("emailaddress1"),
        "consent": _as_bool(r.get("contact_bskit_consent")),
        "accountid": None,
    }


def _map_case(r):
    return {
        "id": r["incidentid"],
        "title": r.get("title"),
        "priority": _PRIORITY.get(_as_int(r.get("prioritycode"), 2), "normal"),
        "sla_status": r.get("incident_bskit_sla_status"),
        "category": r.get("incident_bskit_category"),
        "days_open": _days_since(r.get("createdon")),
        "status": _STATECODE.get(_as_int(r.get("statecode"), 0), "active"),
        "accountid": None,
    }


def _map_account(r):
    return {
        "id": r["accountid"],
        "name": r.get("name"),
        "revenue": r.get("revenue"),
        "industry": None,
        "city": r.get("address1_city"),
        "owner": None,
    }


def _map_opportunity(r):
    return {
        "id": r["opportunityid"],
        "name": r.get("name"),
        "amount": _as_int(r.get("estimatedvalue"), 0),
        "probability": _as_int(r.get("closeprobability"), 0),
        "closedate": (r.get("estimatedclosedate") or "")[:10],
        "stage": _STAGE.get(_as_int(r.get("salesstage"), 0), "qualify"),
        "status": _OPP_STATE.get(_as_int(r.get("statecode"), 0), "open"),
        "owner": None,
        "days_since_activity": 0,
        "competitor": None,
        "accountid": None,
    }


def _map_lead(r):
    return {
        "id": r["leadid"],
        "name": r.get("subject"),
        "company": r.get("companyname"),
        "budget": _as_int(r.get("budgetamount"), 0),
        "source": None,
        "status": "new",
        "owner": None,
    }


# Custom Dataverse tables carry a publisher prefix (e.g. <prefix>_name). Pass it with
# --prefix so the committed driver stays environment-agnostic; the maps below read the
# prefix-stripped column names produced by fetch_table.

def _map_segment(r):
    return {
        "id": r.get("bskitsegmentid"),
        "name": r.get("name"),
        "definition": r.get("definition"),
        "status": r.get("status"),
        "membercount": _as_int(r.get("membercount"), 0),
    }


def _map_journey(r):
    return {
        "id": r.get("bskitjourneyid"),
        "name": r.get("name"),
        "status": r.get("status"),
        "segmentid": r.get("segmentid"),
        "errors": _as_int(r.get("errors"), 0),
    }


def _map_emailmsg(r):
    return {
        "id": r.get("bskitemailmsgid"),
        "name": r.get("name"),
        "channel": r.get("channel"),
        "sends": _as_int(r.get("sends"), 0),
        "opens": _as_int(r.get("opens"), 0),
        "clicks": _as_int(r.get("clicks"), 0),
    }


def _map_bcitem(r):
    return {
        "id": r.get("bskititemid"),
        "number": r.get("number"),
        "description": r.get("description"),
        "price": _as_int(r.get("price"), 0),
        "inventory": _as_int(r.get("inventory"), 0),
    }


# ---- role finders (ground truth from the seed) -----------------------------------------

def _by_needle(rows, field, needle):
    for r in rows:
        if needle.lower() in (r.get(field) or "").lower():
            return r["id"]
    raise SystemExit("no seeded row whose %s contains %r" % (field, needle))


def _first_id(by, target):
    rows = by.get(target) or []
    if not rows:
        raise SystemExit("no seeded rows for target %r" % target)
    return rows[0]["id"]


def _with(base, **extra):
    merged = dict(base)
    merged.update(extra)
    return merged


# ---- assertion builders (all take (by, ctx)) -------------------------------------------

def _assert_consent(by, ctx):
    contacts = by["contact"]
    optin = _by_needle(contacts, "name", "Optin")
    noconsent = _by_needle(contacts, "name", "Noconsent")
    return [
        {"level": "critical", "kind": "not_contains", "dataset": "mailable",
         "idfield": "id", "id": noconsent},
        {"level": "critical", "kind": "field_equals", "dataset": "mailable",
         "idfield": "id", "id": optin, "field": "consent", "value": True},
        {"level": "expected", "kind": "count_min", "dataset": "blocked", "n": 1},
    ]


def _assert_triage(by, ctx):
    breach = _by_needle(by["case"], "title", "Breached")
    return [
        {"level": "critical", "kind": "ranked_first", "dataset": "queue",
         "by": "score", "idfield": "id", "id": breach},
        {"level": "critical", "kind": "field_equals", "dataset": "queue",
         "idfield": "id", "id": breach, "field": "sla", "value": "breached"},
    ]


def _billing_case_id(by):
    for r in by["case"]:
        if r.get("category") == "billing":
            return r["id"]
    raise SystemExit("no seeded case with category 'billing'")


def _args_billing_case(by, ctx):
    return {"case": _billing_case_id(by)}


def _assert_summary(by, ctx):
    return [{"level": "critical", "kind": "text_contains",
             "substr": "verify the invoice line items"}]


def _assert_response(by, ctx):
    return [{"level": "critical", "kind": "text_contains",
             "substr": "Thanks for flagging the billing question"}]


def _assert_records(by, ctx):
    return [{"level": "critical", "kind": "count_min", "dataset": "hits", "n": 1}]


def _assert_bulk(by, ctx):
    lead = _by_needle(by["lead"], "name", "Hot")
    return [{"level": "critical", "kind": "plan_updates", "dataset": "plan",
             "key": lead, "field": "status", "to": "qualified"}]


def _assert_lead_qualify(by, ctx):
    lead = _by_needle(by["lead"], "name", "Hot")
    return [{"level": "critical", "kind": "plan_updates", "dataset": "plan",
             "key": lead, "field": "status", "to": "qualified"}]


def _assert_model(by, ctx):
    acct = _first_id(by, "account")
    return [{"level": "critical", "kind": "plan_updates", "dataset": "plan",
             "key": acct, "field": "region", "to": "unknown"}]


def _assert_audit(by, ctx):
    return [{"level": "critical", "kind": "count_min", "dataset": "sensitive", "n": 1}]


def _assert_appsurface(by, ctx):
    return [{"level": "critical", "kind": "text_contains", "substr": "Screen for 'account'"}]


def _assert_flow(by, ctx):
    return [{"level": "critical", "kind": "text_contains", "substr": "Drafted flow 'nightly-sync'"}]


def _assert_agentfront(by, ctx):
    return [{"level": "critical", "kind": "text_contains", "substr": "Topic for skill 'lead-qualify'"}]


def _assert_catchup(by, ctx):
    return [{"level": "critical", "kind": "count_min", "dataset": "by_stage", "n": 1}]


def _assert_deal_risk(by, ctx):
    risky = _by_needle(by["opportunity"], "name", "Risky")
    return [{"level": "critical", "kind": "ranked_first", "dataset": "ranked",
             "by": "risk", "idfield": "id", "id": risky}]


def _assert_brief(by, ctx):
    return [{"level": "critical", "kind": "count_min", "dataset": "open_opportunities", "n": 1}]


def _args_account_brief(by, ctx):
    return {"account": ctx["account_id"]}


def _args_lead_to_order(by, ctx):
    return {"lead": _by_needle(by["lead"], "name", "Hot"), "closedate": "2026-12-31",
            "force": True}


def _assert_lead_to_order(by, ctx):
    return [{"level": "critical", "kind": "plan_creates", "dataset": "opp_plan",
             "match": {"stage": "qualify"}}]


def _assert_mds(by, ctx):
    return [{"level": "critical", "kind": "count_min", "dataset": "flags", "n": 1}]


def _args_entity_edit(by, ctx):
    return {"entity": "account", "key": "id", "id": _first_id(by, "account"),
            "set": ["city=Metropolis"]}


def _assert_entity_edit(by, ctx):
    return [{"level": "critical", "kind": "plan_updates", "dataset": "plan",
             "key": _first_id(by, "account"), "field": "city", "to": "Metropolis"}]


def _assert_entity_query(by, ctx):
    return [{"level": "critical", "kind": "text_contains", "substr": "entity account | filter"}]


def _args_doc_attach(by, ctx):
    return {"entity": "account", "id": _first_id(by, "account"), "name": "invoice.pdf",
            "note": None}


def _assert_doc_attach(by, ctx):
    return [{"level": "critical", "kind": "text_contains", "substr": "doc-attach invoice.pdf"}]


# ---- marketing (custom tables) + business-central (custom table) + reconcile -----------

def _args_segment_build(by, ctx):
    return {"segment": _first_id(by, "segment"), "source": "account"}


def _assert_segment_build(by, ctx):
    return [{"level": "critical", "kind": "count_min", "dataset": "members", "n": 1}]


def _assert_journey_check(by, ctx):
    return [{"level": "critical", "kind": "count_min", "dataset": "no_go", "n": 1}]


def _assert_campaign_report(by, ctx):
    return [{"level": "critical", "kind": "count_min", "dataset": "below_floor", "n": 1}]


def _assert_bc_record(by, ctx):
    return [{"level": "critical", "kind": "count_min", "dataset": "rows", "n": 1}]


def _args_bc_action(by, ctx):
    return {"id": _first_id(by, "bc_item")}


def _assert_bc_action(by, ctx):
    item = (by.get("bc_item") or [{}])[0]
    new_inv = _as_int(item.get("inventory"), 0) + 5
    return [{"level": "critical", "kind": "plan_updates", "dataset": "plan",
             "key": item.get("id"), "field": "inventory", "to": new_inv}]


def _assert_reconcile(by, ctx):
    return [{"level": "critical", "kind": "count_min", "dataset": "findings", "n": 1}]


# ---- shared fetch specs ----------------------------------------------------------------

_CONTACT_FETCH = {
    "table": "contact", "namefield": "lastname", "target": "contact",
    "select": ["contactid", "firstname", "lastname", "emailaddress1", "contact_bskit_consent"],
    "map": _map_contact,
}
_INCIDENT_FETCH = {
    "table": "incident", "namefield": "title", "target": "case",
    "select": ["incidentid", "title", "prioritycode", "statecode",
               "incident_bskit_category", "incident_bskit_sla_status", "createdon"],
    "map": _map_case,
}
_ACCOUNT_FETCH = {
    "table": "account", "namefield": "name", "target": "account",
    "select": ["accountid", "name", "revenue", "address1_city"],
    "map": _map_account,
}
_OPP_FETCH = {
    "table": "opportunity", "namefield": "name", "target": "opportunity",
    "select": ["opportunityid", "name", "estimatedvalue", "closeprobability",
               "estimatedclosedate", "salesstage", "statecode"],
    "map": _map_opportunity,
}
_LEAD_FETCH = {
    "table": "lead", "namefield": "subject", "target": "lead",
    "select": ["leadid", "subject", "companyname", "budgetamount"],
    "map": _map_lead,
}

# Custom tables: base logical name (no prefix) + prefix-stripped select columns. fetch_table
# prepends --prefix at run time so nothing environment-specific is committed.
_SEGMENT_FETCH = {
    "table": "bskitsegment", "custom": True, "namefield": "name", "target": "segment",
    "select": ["bskitsegmentid", "name", "definition", "status", "membercount"],
    "map": _map_segment,
}
_JOURNEY_FETCH = {
    "table": "bskitjourney", "custom": True, "namefield": "name", "target": "journey",
    "select": ["bskitjourneyid", "name", "status", "segmentid", "errors"],
    "map": _map_journey,
}
_EMAILMSG_FETCH = {
    "table": "bskitemailmsg", "custom": True, "namefield": "name", "target": "emailmsg",
    "select": ["bskitemailmsgid", "name", "channel", "sends", "opens", "clicks"],
    "map": _map_emailmsg,
}
_BCITEM_FETCH = {
    "table": "bskititem", "custom": True, "namefield": "name", "target": "bc_item",
    "select": ["bskititemid", "name", "number", "description", "price", "inventory"],
    "map": _map_bcitem,
}

_EMPTY_PLAN = {"source": "empty_plan"}


SPECS = {
    # ---- marketing ----
    "consent-guard": {
        "skill": "skills/marketing/consent-guard/skill.py",
        "args": {"account": None},
        "fetch": [_CONTACT_FETCH],
        "with_datasets": {"mailable": "mailable", "blocked": "blocked"},
        "without": {"text": "Here is the contact list for the send.",
                    "datasets": {"mailable": {"source": "table", "table": "contact"},
                                 "blocked": {"source": "empty"}}},
        "assertions": _assert_consent,
    },
    # ---- service ----
    "case-triage": {
        "skill": "skills/service/case-triage/skill.py",
        "args": {"top": 25},
        "fetch": [_INCIDENT_FETCH],
        "with_datasets": {"queue": "queue"},
        "without": {"text": "Here are the open cases.",
                    "datasets": {"queue": {"source": "table", "table": "case"}}},
        "assertions": _assert_triage,
    },
    "case-summary": {
        "skill": "skills/service/case-summary/skill.py",
        "args": {}, "args_builder": _args_billing_case,
        "fetch": [_INCIDENT_FETCH],
        "with_datasets": {},
        "without": {"text": "This case is about a billing question from the customer.",
                    "datasets": {}},
        "assertions": _assert_summary,
    },
    "response-draft": {
        "skill": "skills/service/response-draft/skill.py",
        "args": {}, "args_builder": _args_billing_case,
        "fetch": [_INCIDENT_FETCH],
        "with_datasets": {},
        "without": {"text": "Hi, thanks for reaching out about your issue. We will follow up.",
                    "datasets": {}},
        "assertions": _assert_response,
    },
    # ---- sales ----
    "opportunity-catchup": {
        "skill": "skills/sales/opportunity-catchup/skill.py",
        "args": {"owner": None, "stale_days": 30},
        "fetch": [_OPP_FETCH],
        "with_datasets": {"by_stage": "by_stage"},
        "without": {"text": "Here is the raw opportunity list.",
                    "datasets": {"by_stage": {"source": "empty"}}},
        "assertions": _assert_catchup,
    },
    "deal-risk": {
        "skill": "skills/sales/deal-risk/skill.py",
        "args": {"threshold": 40, "today": "2026-08-31"},
        "fetch": [_OPP_FETCH],
        "with_datasets": {"ranked": "ranked", "at_risk": "at_risk"},
        "without": {"text": "Here are the open opportunities.",
                    "datasets": {"ranked": {"source": "table", "table": "opportunity"}}},
        "assertions": _assert_deal_risk,
    },
    "account-brief": {
        "skill": "skills/sales/account-brief/skill.py",
        "args": {}, "args_builder": _args_account_brief,
        "fetch": [_ACCOUNT_FETCH,
                  _with(_CONTACT_FETCH, stamp={"accountid": "account_id"}),
                  _with(_OPP_FETCH, stamp={"accountid": "account_id"}),
                  _with(_INCIDENT_FETCH, stamp={"accountid": "account_id"})],
        "with_datasets": {"open_opportunities": "open_opportunities"},
        "without": {"text": "Here is the account and some related rows.",
                    "datasets": {"open_opportunities": {"source": "empty"}}},
        "assertions": _assert_brief,
    },
    # ---- platform ----
    "records": {
        "skill": "skills/platform/records/skill.py",
        "args": {"search": "zzz-bskit", "table": None, "where": None, "select": None,
                 "order_by": None, "desc": False, "top": 50},
        "fetch": [_ACCOUNT_FETCH, _CONTACT_FETCH],
        "with_datasets": {"hits": "hits"},
        "without": {"text": "I looked but produced no structured, cited hit list.",
                    "datasets": {"hits": {"source": "empty"}}},
        "assertions": _assert_records,
    },
    "bulk-edit": {
        "skill": "skills/platform/bulk-edit/skill.py",
        "args": {"table": "lead", "key": "id", "where": ["status=new"],
                 "set": ["status=qualified"]},
        "fetch": [_LEAD_FETCH],
        "with_datasets": {"plan": ""},
        "without": {"text": "I can describe the change but produced no reviewable plan.",
                    "datasets": {"plan": _EMPTY_PLAN}},
        "assertions": _assert_bulk,
    },
    # ---- sales (lead scoring) ----
    "lead-qualify": {
        "skill": "skills/sales/lead-qualify/skill.py",
        "args": {"threshold": 50, "all": False},
        "fetch": [_LEAD_FETCH],
        "with_datasets": {"plan": "plan"},
        "without": {"text": "These inbound leads look worth a follow-up.",
                    "datasets": {"plan": _EMPTY_PLAN}},
        "assertions": _assert_lead_qualify,
    },
    "model": {
        "skill": "skills/platform/model/skill.py",
        "args": {"add_column": "account:region=unknown", "create_table": None},
        "fetch": [_ACCOUNT_FETCH],
        "with_datasets": {"plan": ""},
        "without": {"text": "I can suggest a column but produced no migration plan.",
                    "datasets": {"plan": _EMPTY_PLAN}},
        "assertions": _assert_model,
    },
    "audit": {
        "skill": "skills/platform/audit/skill.py",
        "args": {},
        "fetch": [_ACCOUNT_FETCH, _CONTACT_FETCH],
        "with_datasets": {"sensitive": "sensitive"},
        "without": {"text": "I did not scan for sensitive fields.",
                    "datasets": {"sensitive": {"source": "empty"}}},
        "assertions": _assert_audit,
    },
    "app-surface": {
        "skill": "skills/platform/app-surface/skill.py",
        "args": {"table": "account"},
        "fetch": [_ACCOUNT_FETCH],
        "with_datasets": {},
        "without": {"text": "An app over the account table would be useful.", "datasets": {}},
        "assertions": _assert_appsurface,
    },
    "flow-scaffold": {
        "skill": "skills/platform/flow-scaffold/skill.py",
        "args": {"name": "nightly-sync", "trigger": "when_a_record_is_updated",
                 "table": "opportunity", "steps": None},
        "fetch": [_ACCOUNT_FETCH],
        "with_datasets": {},
        "without": {"text": "A nightly sync flow sounds reasonable.", "datasets": {}},
        "assertions": _assert_flow,
    },
    "agent-front": {
        "skill": "skills/platform/agent-front/skill.py",
        "args": {"skill": "lead-qualify", "inputs": None},
        "fetch": [_ACCOUNT_FETCH],
        "with_datasets": {},
        "without": {"text": "You could build an agent for lead-qualify.", "datasets": {}},
        "assertions": _assert_agentfront,
    },
    # ---- finance (entity-agnostic; run against the real account table) ----
    "entity-query": {
        "skill": "skills/finance/entity-query/skill.py",
        "args": {"entity": "account", "where": None, "select": None, "order_by": None,
                 "desc": False, "top": 50},
        "fetch": [_ACCOUNT_FETCH],
        "with_datasets": {},
        "without": {"text": "There are some account rows.", "datasets": {}},
        "assertions": _assert_entity_query,
    },
    "entity-edit": {
        "skill": "skills/finance/entity-edit/skill.py",
        "args": {}, "args_builder": _args_entity_edit,
        "fetch": [_ACCOUNT_FETCH],
        "with_datasets": {"plan": ""},
        "without": {"text": "I can suggest a city change but produced no plan.",
                    "datasets": {"plan": _EMPTY_PLAN}},
        "assertions": _assert_entity_edit,
    },
    "doc-attach": {
        "skill": "skills/finance/doc-attach/skill.py",
        "args": {}, "args_builder": _args_doc_attach,
        "fetch": [_ACCOUNT_FETCH],
        "with_datasets": {},
        "without": {"text": "You could attach a document to that record.", "datasets": {}},
        "assertions": _assert_doc_attach,
    },
    # ---- cross-process (CRM-side, dry-run) ----
    "lead-to-order": {
        "skill": "skills/cross-process/lead-to-order/skill.py",
        "args": {}, "args_builder": _args_lead_to_order,
        "fetch": [_LEAD_FETCH],
        "with_datasets": {"opp_plan": "plans.opportunity"},
        "without": {"text": "This lead could become an opportunity.",
                    "datasets": {"opp_plan": _EMPTY_PLAN}},
        "assertions": _assert_lead_to_order,
    },
    "master-data-sync": {
        "skill": "skills/cross-process/master-data-sync/skill.py",
        "args": {},
        "fetch": [_ACCOUNT_FETCH],
        "with_datasets": {"flags": "flags"},
        "without": {"text": "CRM and ERP might be out of sync.",
                    "datasets": {"flags": {"source": "empty"}}},
        "assertions": _assert_mds,
    },
    # ---- marketing (custom tables) ----
    "segment-build": {
        "skill": "skills/marketing/segment-build/skill.py",
        "args": {"source": "account", "segment": None}, "args_builder": _args_segment_build,
        "fetch": [_SEGMENT_FETCH, _ACCOUNT_FETCH],
        "with_datasets": {"members": "members"},
        "without": {"text": "The segment membership is unclear.",
                    "datasets": {"members": {"source": "empty"}}},
        "assertions": _assert_segment_build,
    },
    "journey-check": {
        "skill": "skills/marketing/journey-check/skill.py",
        "args": {},
        "fetch": [_JOURNEY_FETCH, _SEGMENT_FETCH],
        "with_datasets": {"no_go": "no_go"},
        "without": {"text": "The journeys look about ready to go live.",
                    "datasets": {"no_go": {"source": "empty"}}},
        "assertions": _assert_journey_check,
    },
    "campaign-report": {
        "skill": "skills/marketing/campaign-report/skill.py",
        "args": {"min_click": 5.0},
        "fetch": [_EMAILMSG_FETCH],
        "with_datasets": {"below_floor": "below_floor"},
        "without": {"text": "The campaign seems to be performing fine.",
                    "datasets": {"below_floor": {"source": "empty"}}},
        "assertions": _assert_campaign_report,
    },
    # ---- business-central (custom table) ----
    "bc-record": {
        "skill": "skills/business-central/bc-record/skill.py",
        "args": {"id": None, "set": None},
        "fetch": [_BCITEM_FETCH],
        "with_datasets": {"rows": "rows"},
        "without": {"text": "There may be some items in Business Central.",
                    "datasets": {"rows": {"source": "empty"}}},
        "assertions": _assert_bc_record,
    },
    "bc-action": {
        "skill": "skills/business-central/bc-action/skill.py",
        "args": {"action": "adjust-inventory", "by": "5", "value": None, "id": None},
        "args_builder": _args_bc_action,
        "fetch": [_BCITEM_FETCH],
        "with_datasets": {"plan": ""},
        "without": {"text": "You could adjust the item inventory.",
                    "datasets": {"plan": _EMPTY_PLAN}},
        "assertions": _assert_bc_action,
    },
    # ---- platform (duplicate detection over the real account table) ----
    "reconcile": {
        "skill": "skills/platform/reconcile/skill.py",
        "args": {"table": "account"},
        "fetch": [_ACCOUNT_FETCH],
        "with_datasets": {"findings": "findings"},
        "without": {"text": "The records look consistent.",
                    "datasets": {"findings": {"source": "empty"}}},
        "assertions": _assert_reconcile,
    },
}


def _resolve_context(client, tag):
    q = ("SELECT accountid, name FROM account WHERE name LIKE '%s%%'"
         % tag.replace("'", "''"))
    res = client.tools_call("read_query", {"querytext": q})
    rows = []
    if not res.get("result", {}).get("isError"):
        try:
            rows = json.loads(_text(res))
        except (json.JSONDecodeError, TypeError):
            rows = []
    account_id = None
    for r in rows:
        if "northwind" in (r.get("name") or "").lower():
            account_id = r["accountid"]
            break
    if account_id is None and rows:
        account_id = rows[0]["accountid"]
    return {"account_id": account_id}


def fetch_table(client, spec, tag, ctx, prefix=None):
    custom = spec.get("custom")
    pfx = (prefix + "_") if (custom and prefix) else ""
    if custom and not prefix:
        raise SystemExit("skill needs custom table %r; pass --prefix <publisher-prefix>"
                         % spec["table"])
    table = pfx + spec["table"] if custom else spec["table"]
    namefield = pfx + spec["namefield"] if custom else spec["namefield"]
    cols = ", ".join((pfx + c) if custom else c for c in spec["select"])
    q = "SELECT %s FROM %s WHERE %s LIKE '%s%%'" % (
        cols, table, namefield, tag.replace("'", "''"))
    res = client.tools_call("read_query", {"querytext": q})
    if res.get("result", {}).get("isError"):
        raise SystemExit("read_query failed for %s: %s" % (table, _text(res)))
    raw = json.loads(_text(res))
    if custom and prefix:
        strip = prefix + "_"
        raw = [{(k[len(strip):] if k.startswith(strip) else k): v for k, v in r.items()}
               for r in raw]
    rows = [spec["map"](r) for r in raw]
    for field, ctx_key in (spec.get("stamp") or {}).items():
        for row in rows:
            row[field] = ctx.get(ctx_key)
    return rows


def _run_condition(runner, case_def, assertions, n):
    passes, scores, last = [], [], []
    for _ in range(n):
        artifact = runner(case_def)
        verdict = judge.evaluate(artifact, assertions)
        passes.append(verdict["passed"])
        scores.append(verdict["avg_score"])
        last = verdict["assertions"]
    return passes, scores, last


def run_skill(client, skill_id, spec, tag, n, ctx, prefix=None):
    by_target, snapshot_tables = {}, {}
    for f in spec["fetch"]:
        rows = fetch_table(client, f, tag, ctx, prefix)
        if not rows:
            raise SystemExit("no seeded rows for %s (%s); run live-agent/seed.py --seed first"
                             % (skill_id, f["table"]))
        by_target[f["target"]] = rows
        snapshot_tables[f["target"]] = rows
    assertions = spec["assertions"](by_target, ctx)
    snapshot = {"tables": snapshot_tables}
    run_args = dict(spec.get("args") or {})
    if spec.get("args_builder"):
        run_args.update(spec["args_builder"](by_target, ctx))

    fd, snap_path = tempfile.mkstemp(prefix="bskit-live-", suffix=".json")
    os.close(fd)
    with open(snap_path, "w", encoding="utf-8") as fh:
        json.dump(snapshot, fh)

    try:
        harness.set_store_path(snap_path)
        case_def = {
            "with": {"module": spec["skill"], "args": run_args,
                     "datasets": spec["with_datasets"]},
            "without": spec["without"],
        }
        wp, ws, wa = _run_condition(harness.run_with, case_def, assertions, n)
        op, os_, oa = _run_condition(harness.run_without, case_def, assertions, n)
    finally:
        harness.set_store_path(None)
        os.remove(snap_path)

    w = stats.summarize_runs(wp, ws, k=n)
    o = stats.summarize_runs(op, os_, k=n)
    delta = stats.two_proportion_delta(w["passes"], w["n"], o["passes"], o["n"])
    seeded = sum(len(v) for v in by_target.values())
    return {
        "skill": "%s (LIVE)" % skill_id, "with": w, "without": o, "delta": delta,
        "cases": [{
            "id": "live-%s (%d seeded row(s))" % (skill_id, seeded),
            "with_pass": all(wp), "without_pass": all(op),
            "with_assertions": wa, "without_assertions": oa,
        }],
    }


def run_live(url, token_file, tag, n, only, prefix=None):
    client = mcp_probe.McpClient(url, mcp_probe._load_token(token_file))
    client.initialize()
    ctx = _resolve_context(client, tag)
    ids = only or list(SPECS.keys())
    skills = [run_skill(client, sid, SPECS[sid], tag, n, ctx, prefix) for sid in ids]
    return {"mode": "live", "n": n, "skills": skills}


def main():
    p = argparse.ArgumentParser(description="Generalized live ablation suite.")
    p.add_argument("--url", required=True)
    p.add_argument("--token-file", required=True)
    p.add_argument("--tag", default="zzz-bskit-seed")
    p.add_argument("--n", type=int, default=3)
    p.add_argument("--only", help="comma-separated skill ids (default: all)")
    p.add_argument("--prefix", help="publisher prefix for custom tables (e.g. crXXX)")
    p.add_argument("--out", help="write the Markdown report here (else print)")
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    only = [s.strip() for s in args.only.split(",")] if args.only else None
    if only:
        unknown = [s for s in only if s not in SPECS]
        if unknown:
            raise SystemExit("unknown skill id(s): %s; known: %s"
                             % (unknown, list(SPECS.keys())))
    result = run_live(args.url, args.token_file, args.tag, args.n, only, args.prefix)
    if args.json:
        print(json.dumps(result, indent=2, default=str))
        return
    md = report_mod.render(result)
    if args.out:
        os.makedirs(os.path.dirname(args.out), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(md)
        print("wrote %s" % args.out)
    else:
        print(md)


if __name__ == "__main__":
    main()
