"""Shared CLI and preflight plumbing so every skill stays small and consistent.

A skill module defines `run(store, args) -> {"text": str, "data": obj}` and calls
`run_cli(run, ...)` under `__main__`. Reads are the default; a skill that writes takes
`--commit` to apply its dry-run plan. Skills live three levels below the repo root, so
each one prepends the root to sys.path via `bootstrap()` before importing bskit.
"""
import argparse
import json
import os
import sys


def bootstrap():
    """Put the repo root on sys.path so `import bskit` works from a skill folder."""
    here = os.path.dirname(os.path.abspath(sys.argv[0])) if sys.argv and sys.argv[0] else os.getcwd()
    root = os.path.abspath(os.path.join(here, "..", "..", ".."))
    if root not in sys.path:
        sys.path.insert(0, root)
    return root


def _make_store(args):
    from .config import load_config
    from .store import Store

    cfg = load_config(getattr(args, "store", None))
    return Store(cfg["store"], working=getattr(args, "working", None))


def _add_common(p):
    p.add_argument("--store", help="path to a store JSON (default: fixtures/org.json)")
    p.add_argument("--working", help="path to a working overlay JSON (applied writes)")
    p.add_argument("--commit", action="store_true", help="apply the plan (writes only, dry-run otherwise)")
    p.add_argument("--json", action="store_true", help="print structured JSON instead of text")
    return p


def run_cli(run, description="", add_args=None):
    p = argparse.ArgumentParser(description=description)
    _add_common(p)
    if add_args:
        add_args(p)
    args = p.parse_args()
    store = _make_store(args)
    result = run(store, args)
    if getattr(args, "json", False):
        print(json.dumps(result.get("data", result), indent=2, ensure_ascii=False, default=str))
    else:
        print(result.get("text", ""))
    return result


def coerce(v):
    if v is None:
        return None
    s = str(v)
    if s.lower() in ("null", "none"):
        return None
    if s.lower() == "true":
        return True
    if s.lower() == "false":
        return False
    try:
        return int(s)
    except ValueError:
        pass
    try:
        return float(s)
    except ValueError:
        pass
    return s


def parse_pairs(items):
    """['a=1','b=x'] -> {'a':1,'b':'x'} with light type coercion."""
    out = {}
    for it in items or []:
        if "=" not in it:
            continue
        k, val = it.split("=", 1)
        out[k.strip()] = coerce(val.strip())
    return out


def preflight_main(required_tables, store=None):
    """A read-only readiness check shared by every skill's preflight.py."""
    from .config import load_config
    from .store import Store

    cfg = load_config(store)
    try:
        s = Store(cfg["store"])
    except Exception as e:  # noqa: BLE001
        print("NOT READY: cannot open store: %s" % e)
        sys.exit(1)
    missing = [t for t in required_tables if not s.tables.get(t)]
    if missing:
        print("NOT READY: store is missing/empty tables: %s" % ", ".join(missing))
        sys.exit(1)
    print("READY: store %s, tables present: %s" % (cfg["store"], ", ".join(required_tables)))
    sys.exit(0)
