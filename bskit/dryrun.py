"""Dry-run helpers. Any write is shown as a plan before it touches data."""


def render_plan(plan):
    kf = plan["key_field"]
    lines = [
        "Plan for {t} (key={k}): {c} create, {u} update, {n} unchanged".format(
            t=plan["table"], k=kf, c=len(plan["creates"]), u=len(plan["updates"]), n=len(plan["noops"])
        )
    ]
    for c in plan["creates"][:25]:
        lines.append("  + create {v}".format(v=c.get(kf)))
    for u in plan["updates"][:25]:
        changes = ", ".join("{f}: {a} -> {b}".format(f=f, a=d[0], b=d[1]) for f, d in u["diff"].items())
        lines.append("  ~ update {v}: {c}".format(v=u["key"], c=changes))
    return "\n".join(lines)


def is_noop(plan):
    return not plan["creates"] and not plan["updates"]
