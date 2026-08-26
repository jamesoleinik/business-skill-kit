"""Render an ablation run as a Markdown report card.

One section per skill, a per-case with-vs-without table, the ablation delta with its
interval and P(improvement), and a verdict on three axes:

- Triggering  did the skill produce its intended derived output at all.
- Functional  assertion pass-rate lift, with skill minus without skill.
- Performance a coarse cost proxy (assertions evaluated / output size) reported when live.

Verdict per skill: HELPS (a real, positive functional lift), NEUTRAL (no measurable lift,
flagged as possible dead weight), or REGRESS (the skill made things worse).
"""


def _pct(x):
    return "%.0f%%" % (100 * x)


def _verdict(delta):
    d = delta["delta"]
    if d > 0.001:
        return "HELPS"
    if d < -0.001:
        return "REGRESS"
    return "NEUTRAL"


def render(run):
    lines = []
    lines.append("# Ablation report")
    lines.append("")
    lines.append("Mode: **%s**  |  runs per condition (N): **%d**" % (run["mode"], run["n"]))
    lines.append("")
    lines.append("Ablation runs each task with the skill and without it, then measures the")
    lines.append("difference. A skill earns its place only when it produces a real, positive lift.")
    lines.append("")

    lines.append("## Summary")
    lines.append("")
    lines.append("| Skill | With pass-rate | Without pass-rate | Delta | P(improve) | Verdict |")
    lines.append("| --- | --- | --- | --- | --- | --- |")
    for s in run["skills"]:
        d = s["delta"]
        lines.append("| `%s` | %s | %s | %+.0f pts | %s | **%s** |" % (
            s["skill"], _pct(s["with"]["pass_rate"]), _pct(s["without"]["pass_rate"]),
            100 * d["delta"], _pct(d["p_improve"]), _verdict(d),
        ))
    lines.append("")

    for s in run["skills"]:
        d = s["delta"]
        lines.append("## `%s`" % s["skill"])
        lines.append("")
        lines.append("- Functional lift: **%+.0f points** (%s -> %s pass-rate), 95%% interval [%+.0f, %+.0f] pts."
                     % (100 * d["delta"], _pct(s["without"]["pass_rate"]), _pct(s["with"]["pass_rate"]),
                        100 * d["low"], 100 * d["high"]))
        lines.append("- Capability pass@%d: with %s, without %s. Reliability pass^%d: with %s, without %s."
                     % (run["n"], _pct(s["with"]["pass_at_k"]), _pct(s["without"]["pass_at_k"]),
                        run["n"], _pct(s["with"]["pass_hat_k"]), _pct(s["without"]["pass_hat_k"])))
        lines.append("- Avg assertion score (1..5): with **%.2f**, without **%.2f**."
                     % (s["with"]["avg_score"], s["without"]["avg_score"]))
        lines.append("- Verdict: **%s**." % _verdict(d))
        lines.append("")
        lines.append("| Case | With | Without | Critical assertions |")
        lines.append("| --- | --- | --- | --- |")
        for c in s["cases"]:
            crit = "; ".join(
                "%s %s" % ("PASS" if a["passed"] else "FAIL", a["detail"])
                for a in c["with_assertions"] if a["level"] == "critical"
            )
            lines.append("| %s | %s | %s | %s |" % (
                c["id"], "PASS" if c["with_pass"] else "FAIL",
                "PASS" if c["without_pass"] else "FAIL", crit,
            ))
        lines.append("")
    return "\n".join(lines)
