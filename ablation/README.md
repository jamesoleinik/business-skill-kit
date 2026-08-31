# Skill ablation

Validation proves a skill *runs*. Ablation proves a skill *helps*. This folder runs each
task twice, with the skill and without it, and measures the difference. A skill earns its
place in the kit only when it produces a real, positive lift; a skill with no measurable
lift is flagged as possible dead weight.

Standard library only, like the rest of the kit. No numpy, no model, no login required for
the default fixture mode.

## Run it

```bash
# from the repo root
python ablation/run_ablation.py                    # all cases, fixture mode, N=3
python ablation/run_ablation.py --only lead-qualify --n 5
python ablation/run_ablation.py --out ablation/reports/fixture-report.md
python ablation/run_ablation.py --json             # machine-readable
```

On Windows set `PYTHONIOENCODING=utf-8` first so the report prints cleanly.

## The two conditions

- **with**: the real skill runs (`skills/<slug>/skill.py`), and named datasets are pulled
  from its structured result.
- **without**: a baseline that has the same data access but not the skill's procedure. It
  can read the tables, but it cannot produce the skill's derived output, the scoring, the
  ranking, or the CRM to ERP write chain. That gap is what we measure.

This is the honest comparison: not "empty vs full", but "an agent that can see the data vs
the same agent given the skill".

## Test cases

Cases are JSON under `cases/<slug>.json` (JSON, not YAML, to keep the kit zero-dependency).
Each file declares the two conditions once and a list of cases, each with a `query` and a
list of `assertions`. Every assertion has a `level`:

- `critical`  the case fails if this fails.
- `expected`  contributes to the score but is not a gate.

Assertion kinds: `ranked_first`, `rank_position`, `field_equals`, `contains`,
`not_contains`, `count_min`, `plan_creates`, `plan_updates`, `text_contains`.

## Coverage

Every skill in the kit has an ablation case, and all of them **HELP** in fixture mode
(+100-point functional lift, with vs without). Reproduce with:

```bash
python ablation/run_ablation.py            # 30 skills, all HELPS
```

Coverage spans all seven domains: platform (8), sales (5), service (4), marketing (4),
finance (3), business-central (2), and cross-process (4). Read skills assert on the derived
datasets (ranking, filtering, rollups); write and plan skills assert on the dry-run plan
(`plan_creates` / `plan_updates`); generative skills assert on the drafted artifact text.

## Metrics

- **pass_rate**  fraction of runs whose critical assertions all pass.
- **pass@k**  capability: probability at least one of k tries passes (unbiased estimator).
- **pass^k**  reliability: probability all k tries pass.
- **avg_score**  mean assertion score on a 1..5 scale.
- **ablation delta**  with-skill pass_rate minus without-skill pass_rate, with a 95%
  interval and a rough P(improvement).

Verdict per skill: **HELPS**, **NEUTRAL** (dead-weight flag), or **REGRESS**.

## Fixture mode is deterministic

In fixture mode the two conditions are deterministic, so the N runs of a condition are
identical and pass^k equals pass@k. N still exercises the estimators and is the knob that
matters once live mode adds real variance. Do not read the fixture-mode intervals as
evidence of real-world spread; they are tight because the fixture is fixed.

## Live mode (wired)

Live mode re-runs the identical with/without conditions against a real Dataverse (and, for
the CRM-to-ERP chain, a real D365 Finance & Operations) environment, driven through the MCP
server over the same interactive-OAuth path as `live-agent/`. The artifact shape stays
identical, so the judge, stats, and report do not change; only the data source does.

- `live_ablation.py` reads seeded rows for a skill's tables through the MCP `read_query`
  tool, normalizes them into the store snapshot the harness expects, and runs the skill
  dry-run. Ground truth comes from the seed roles, not the skill's own output, so the
  assertions are an independent acceptance test.
- `live_q2c_ablation.py` plus `live-agent/q2c_commit.py` exercise the cross-process
  CRM-order-to-ERP-invoice chain, including a real, idempotent, approval-gated write into
  live ERP.

Proven live to date (verdict HELPS against a real environment): `sales/lead-qualify` and
`cross-process/quote-to-cash`. These span the two distinct live planes: a CRM read/scoring
skill and a CRM-to-ERP write chain.

### Live feasibility boundary (honest gap)

Not every skill can be faithfully live-run, and the kit does not pretend otherwise:

- **Live-capable** — skills over standard CRM tables that exist and are seeded in the target
  org (leads, accounts, contacts, opportunities, quotes, sales orders, cases).
- **Fixture-only, custom-field** — skills that score on fields the fixture adds for teaching
  (`days_since_activity`, `competitor`, `sla_status`, `category`, `consent`). Those columns
  are not present on standard live tables, so a faithful live run needs schema extension
  first. Fixture ablation fully covers them.
- **Fixture-only, table-not-deployed** — marketing (segment / journey / email message),
  finance ERP entities, and Business Central items are not surfaced as tables in every
  environment; where they are absent the skill is fixture-only by construction.

This boundary is a property of the target environment's schema, not of the skills: all 30
are proven by fixture ablation, and the live-capable subset is additionally proven live.

## Safety and scope

Reports are written to `reports/` (gitignored) because they can contain data-derived output.
Nothing in this folder reaches a real environment, and there are no environment URLs, tenant
or organization IDs, or tokens anywhere in it. The judge is rule-based and deterministic; a
model-backed judge can be dropped in behind the same `evaluate(artifact, assertions)`
interface without changing anything else.
