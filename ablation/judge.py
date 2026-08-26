"""Deterministic assertion judge for ablation.

The champion methodology scores each assertion with an LLM judge on a 1..5 scale and tags
assertions critical or expected. In fixture mode we use a deterministic rule-based judge so
the whole pipeline runs offline in CI with no model and no login: a passing assertion scores
5, a failing one scores 1. Live mode can swap this for a model-backed judge behind the same
interface (evaluate(artifact, assertions) -> verdict) without touching the runner or stats.

An artifact is a plain dict: {"datasets": {name: rows-or-plan}, "text": str}. Datasets are
either a list of record dicts (reads/rankings) or a dry-run plan dict (writes).
"""

PASS_SCORE = 5
FAIL_SCORE = 1


def _rows(artifact, name):
    return artifact.get("datasets", {}).get(name)


def _find(rows, idfield, ident):
    for r in rows or []:
        if r.get(idfield) == ident:
            return r
    return None


def _sorted_desc(rows, by):
    have = [r for r in (rows or []) if r.get(by) is not None]
    return sorted(have, key=lambda r: r.get(by), reverse=True)


def _check(a, artifact):
    """Return (passed, detail) for one assertion dict."""
    kind = a.get("kind")
    ds = _rows(artifact, a.get("dataset"))

    if kind == "ranked_first":
        s = _sorted_desc(ds, a["by"])
        if not s:
            return False, "no rows carry field '%s'" % a["by"]
        top = s[0].get(a["idfield"])
        return top == a["id"], "top by %s = %s (want %s)" % (a["by"], top, a["id"])

    if kind == "rank_position":
        s = _sorted_desc(ds, a["by"])
        pos = a["position"]
        got = s[pos].get(a["idfield"]) if pos < len(s) else None
        return got == a["id"], "position %d = %s (want %s)" % (pos, got, a["id"])

    if kind == "field_equals":
        r = _find(ds, a["idfield"], a["id"])
        if r is None:
            return False, "record %s not found" % a["id"]
        got = r.get(a["field"])
        return got == a["value"], "%s.%s = %r (want %r)" % (a["id"], a["field"], got, a["value"])

    if kind == "contains":
        return _find(ds, a["idfield"], a["id"]) is not None, "record %s present" % a["id"]

    if kind == "not_contains":
        return _find(ds, a["idfield"], a["id"]) is None, "record %s absent" % a["id"]

    if kind == "count_min":
        n = len(ds or [])
        return n >= a["n"], "count %d >= %d" % (n, a["n"])

    if kind == "plan_creates":
        creates = (ds or {}).get("creates", []) if isinstance(ds, dict) else []
        match = a.get("match", {})
        for rec in creates:
            if all(rec.get(f) == v for f, v in match.items()):
                return True, "create matching %s found" % match
        return False, "no create matching %s" % match

    if kind == "plan_updates":
        updates = (ds or {}).get("updates", []) if isinstance(ds, dict) else []
        for u in updates:
            if u.get("key") == a["key"]:
                diff = u.get("diff", {})
                if a["field"] in diff and diff[a["field"]][1] == a["to"]:
                    return True, "%s.%s -> %r" % (a["key"], a["field"], a["to"])
        return False, "no update setting %s.%s to %r" % (a["key"], a["field"], a["to"])

    if kind == "text_contains":
        return a["substr"].lower() in artifact.get("text", "").lower(), "text contains %r" % a["substr"]

    return False, "unknown assertion kind %r" % kind


def evaluate(artifact, assertions):
    """Score every assertion. The case passes when all critical assertions pass."""
    results = []
    critical_ok = True
    for a in assertions:
        passed, detail = _check(a, artifact)
        level = a.get("level", "expected")
        if level == "critical" and not passed:
            critical_ok = False
        results.append({
            "kind": a.get("kind"),
            "level": level,
            "passed": passed,
            "score": PASS_SCORE if passed else FAIL_SCORE,
            "detail": detail,
        })
    scores = [r["score"] for r in results]
    return {
        "passed": critical_ok,
        "avg_score": (sum(scores) / len(scores)) if scores else 0.0,
        "assertions": results,
    }
