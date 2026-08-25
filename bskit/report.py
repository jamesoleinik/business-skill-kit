"""Small helpers for consistent, readable skill output."""
import json


def as_json(obj):
    return json.dumps(obj, indent=2, ensure_ascii=False)


def table(rows, columns):
    if not rows:
        return "(none)"
    widths = {c: len(c) for c in columns}
    for r in rows:
        for c in columns:
            widths[c] = max(widths[c], len(str(r.get(c, ""))))
    head = " | ".join(c.ljust(widths[c]) for c in columns)
    sep = "-+-".join("-" * widths[c] for c in columns)
    body = "\n".join(" | ".join(str(r.get(c, "")).ljust(widths[c]) for c in columns) for r in rows)
    return "\n".join([head, sep, body])


def bullets(items):
    return "\n".join("- " + str(i) for i in items) if items else "- (none)"
