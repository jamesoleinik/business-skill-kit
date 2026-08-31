# Validation

Everything in this kit runs against the synthetic company fixture in
`fixtures/org.json` with zero real data. Validation is one command:

```
python validate.py
```

Expected result: `69 passed, 0 failed  All checks passed.`

## What validate.py checks

1. **Deterministic fixture.** `fixtures/make_fixture.py` rebuilds `org.json` and the
   file hash is captured up front.
2. **Preflight readiness (30).** Every skill's `preflight.py` reports `READY` and its
   required tables are present.
3. **Usage runs (30).** Every skill's documented usage line (from its `SKILL.md`) exits
   cleanly. Read and dry-run commands make no changes.
4. **Writes are dry-run-first and idempotent.**
   - `sales/lead-qualify --commit` applies, then re-running over its own
     `out/working.json` overlay is a no-op.
   - `cross-process/quote-to-cash --order S005 --commit` drives the whole
     CRM-order-to-ERP-invoice chain; re-running is a no-op ("Already fully invoiced").
   - An already-invoiced order (`S004`) is a no-op from the start.
   - `cross-process/master-data-sync --commit` applies its fixes, then reports the data
     already aligned on re-run.
5. **The base fixture is never mutated.** After every write above, the hash of
   `fixtures/org.json` still matches the value captured in step 1. Applied changes land
   only in `out/working.json`.

## Design guarantees these checks defend

- **Read-only by default.** Skills only write with `--commit`.
- **Idempotent writes.** `plan_upsert` diffs against the effective store, so a re-applied
  plan produces no changes.
- **No base mutation.** `Store.apply` writes to `out/working.json`; the committed fixture
  is immutable.
- **No third-party dependencies.** The engine and every skill use the Python standard
  library only, so validation runs anywhere with Python 3.8+.

## Notes

- Set `PYTHONIOENCODING=utf-8` on Windows terminals if box-drawing output does not render.
- `out/` is gitignored; delete `out/working.json` to reset applied overlays.
- The private tool-surface mapping in `build-notes/` is never exercised by validation and
  never committed.

## Beyond validation: ablation

`validate.py` proves each skill *runs*; ablation proves each skill *helps*. All 30 skills
have a with-vs-without ablation case and every one earns a **HELPS** verdict:

```
python ablation/run_ablation.py
```

See `ablation/README.md` for the methodology, the full-suite coverage, and the live-mode
feasibility boundary.
