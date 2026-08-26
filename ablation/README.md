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

## Live mode (planned)

Live mode replaces both conditions with a real model run, with and without the skill loaded,
driven through the Dataverse MCP server (the same interactive-OAuth path as `live-agent/`).
The artifact shape stays identical, so the judge, stats, and report do not change. Live mode
is gated on interactive sign-in and is not wired yet.

## Safety and scope

Reports are written to `reports/` (gitignored) because they can contain data-derived output.
Nothing in this folder reaches a real environment, and there are no environment URLs, tenant
or organization IDs, or tokens anywhere in it. The judge is rule-based and deterministic; a
model-backed judge can be dropped in behind the same `evaluate(artifact, assertions)`
interface without changing anything else.
