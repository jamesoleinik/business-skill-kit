"""Ablation run harness: produce an artifact for the with-skill and without-skill conditions.

Two conditions per case:

- with:    invoke the real skill's run(store, args) and extract named datasets from its
           structured result. This is the skill doing its job.
- without: build the baseline datasets the case declares. The baseline models an agent that
           has the same data access (it can read tables) but does not have the skill's
           procedure, so it cannot produce the skill's derived output (scores, rankings,
           the CRM to ERP write chain). That gap is exactly what ablation measures.

Fixture mode (default) needs no login and is deterministic. Live mode is a planned
extension: the same two conditions become a real model run with and without the skill loaded,
driven through the Dataverse MCP server; this module keeps the artifact shape identical so
the judge, stats, and report do not change.
"""
import importlib.util
import os
import sys
import types

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from bskit.config import default_store_path  # noqa: E402
from bskit.store import Store  # noqa: E402

_MODULE_CACHE = {}


def _load_skill(rel_path):
    """Import a skill module from its file path, once."""
    if rel_path in _MODULE_CACHE:
        return _MODULE_CACHE[rel_path]
    abs_path = os.path.join(ROOT, rel_path.replace("/", os.sep))
    name = "bskit_skill_" + rel_path.replace("/", "_").replace(".py", "").replace(".", "_")
    spec = importlib.util.spec_from_file_location(name, abs_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _MODULE_CACHE[rel_path] = mod
    return mod


def _dig(data, dotted):
    cur = data
    for part in dotted.split("."):
        if isinstance(cur, dict):
            cur = cur.get(part)
        else:
            return None
    return cur


def _args_namespace(arg_map):
    ns = types.SimpleNamespace(store=None, working=None, commit=False, json=False)
    for k, v in (arg_map or {}).items():
        setattr(ns, k, v)
    return ns


def _fresh_store():
    # A fresh store per run; reads only, so the base fixture is never mutated.
    return Store(default_store_path(), working=None)


def run_with(case_def):
    spec = case_def["with"]
    mod = _load_skill(spec["module"])
    store = _fresh_store()
    args = _args_namespace(spec.get("args"))
    result = mod.run(store, args)
    data = result.get("data", {})
    datasets = {name: _dig(data, path) for name, path in spec.get("datasets", {}).items()}
    return {"datasets": datasets, "text": result.get("text", "")}


def _baseline_dataset(store, spec):
    src = spec.get("source")
    if src == "table":
        return store.table(spec["table"])
    if src == "empty":
        return []
    if src == "empty_plan":
        return {"creates": [], "updates": [], "noops": []}
    raise ValueError("unknown baseline source %r" % src)


def run_without(case_def):
    spec = case_def["without"]
    store = _fresh_store()
    datasets = {name: _baseline_dataset(store, d) for name, d in spec.get("datasets", {}).items()}
    return {"datasets": datasets, "text": spec.get("text", "")}
