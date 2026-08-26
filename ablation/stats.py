"""Small ablation statistics, standard library only.

No numpy, no scipy. We implement just the handful of estimators the report needs:

- pass@k   capability: probability at least one of k tries passes (unbiased estimator).
- pass^k   reliability: probability all k tries pass.
- pass_rate / avg_score: simple means over the runs.
- Wilson score interval: a well-behaved confidence interval for a proportion, better than
  the normal approximation at small sample sizes.
- ablation delta: with-skill minus without-skill, on pass_rate, with a normal-approximation
  two-proportion interval and a rough P(improvement).

These are public statistics. Nothing here is specific to any internal tool.
"""
import math
from math import comb


def pass_at_k(n, c, k):
    """Unbiased estimate that at least one of k samples passes, given c passes in n runs."""
    if k > n:
        k = n
    if n == 0 or k == 0:
        return 0.0
    if c >= n:
        return 1.0
    if c <= 0:
        return 0.0
    return 1.0 - comb(n - c, k) / comb(n, k)


def pass_hat_k(n, c, k):
    """Estimate that all of k samples pass (reliability), given c passes in n runs."""
    if k > n:
        k = n
    if n == 0 or k == 0:
        return 0.0
    if c < k:
        return 0.0
    return comb(c, k) / comb(n, k)


def wilson(c, n, z=1.96):
    """Wilson score interval for a binomial proportion. Returns (low, high)."""
    if n == 0:
        return (0.0, 0.0)
    p = c / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    margin = (z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n)) / denom
    return (max(0.0, center - margin), min(1.0, center + margin))


def _normal_cdf(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def two_proportion_delta(c_with, n_with, c_without, n_without, z=1.96):
    """Delta in pass-rate (with - without) with a normal-approx interval and P(improvement).

    P(improvement) is a rough one-sided probability that the true delta is positive under a
    normal approximation. It is a signal, not a guarantee, and it is weak at small N.
    """
    if n_with == 0 or n_without == 0:
        return {"delta": 0.0, "low": 0.0, "high": 0.0, "p_improve": 0.5, "se": 0.0}
    p1 = c_with / n_with
    p0 = c_without / n_without
    delta = p1 - p0
    se = math.sqrt(p1 * (1 - p1) / n_with + p0 * (1 - p0) / n_without)
    if se == 0:
        # Deterministic separation (common in fixture mode): no spread to interval.
        p_improve = 1.0 if delta > 0 else (0.0 if delta < 0 else 0.5)
        return {"delta": delta, "low": delta, "high": delta, "p_improve": p_improve, "se": 0.0}
    return {
        "delta": delta,
        "low": delta - z * se,
        "high": delta + z * se,
        "p_improve": _normal_cdf(delta / se),
        "se": se,
    }


def summarize_runs(run_passes, run_scores, k=None):
    """Fold a list of per-run booleans and scores into the core metrics for one condition."""
    n = len(run_passes)
    c = sum(1 for p in run_passes if p)
    if k is None:
        k = n
    lo, hi = wilson(c, n)
    return {
        "n": n,
        "passes": c,
        "pass_rate": (c / n) if n else 0.0,
        "pass_at_k": pass_at_k(n, c, k),
        "pass_hat_k": pass_hat_k(n, c, k),
        "avg_score": (sum(run_scores) / len(run_scores)) if run_scores else 0.0,
        "wilson_low": lo,
        "wilson_high": hi,
    }
