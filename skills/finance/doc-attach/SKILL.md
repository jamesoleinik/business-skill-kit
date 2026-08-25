---
name: doc-attach
description: Record a document attachment against a record via a manifest in out/. USE WHEN you need to log a document linkage to a record. DO NOT USE WHEN you need to change the record's business fields (use entity-edit).
---

# doc-attach

Record a document attachment against a record via a manifest in out/.

Part of the Business Skill Kit. Runs against the synthetic fixture in `fixtures/org.json`
with zero real data. Reads are the default; any write is shown as a dry-run plan and applied
only with `--commit`, writing to `out/working.json` and never to the base fixture.

## Usage

```
python skills/finance/doc-attach/skill.py --entity erp_invoice --id N-7004 --name invoice.pdf
```

Add `--json` for structured output, `--store <path>` to point at another store, and
`--working out/working.json` to read or extend an applied overlay.

## Inputs

- Required tables: account
- Config comes from the environment only (see `.env.example`); no secrets in code.

## Safety

- Dry-run-first and idempotent: re-running an applied change is a no-op.
- No confidential or customer data; the fixture is entirely fictional.
- Check readiness first with `python skills/finance/doc-attach/preflight.py`.
