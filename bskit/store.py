"""A fixture-backed data store that behaves like a small business data platform.

The base store (the committed synthetic fixture) is never mutated. Reads run against the
base by default. Writes are computed as a plan against the effective store (the working
overlay if one exists, else the base), and applied only to a working copy under out/.
That makes every write dry-run-first and idempotent: re-running an applied plan is a
no-op.
"""
import copy
import json
import os


class Store:
    def __init__(self, path, working=None):
        self.path = path
        with open(path, encoding="utf-8") as f:
            self.base = json.load(f)
        self.working_path = working
        if working and os.path.exists(working):
            with open(working, encoding="utf-8") as f:
                self.data = json.load(f)
        else:
            self.data = copy.deepcopy(self.base)
        self.tables = self.data.setdefault("tables", {})
        self.audit = self.data.setdefault("audit", [])

    # ---- reads ----
    def table(self, name):
        return [dict(r) for r in self.tables.get(name, [])]

    def query(self, table, where=None, select=None, top=None, order_by=None):
        rows = [dict(r) for r in self.tables.get(table, [])]
        if where:
            rows = [r for r in rows if where(r)]
        if order_by:
            key, reverse = order_by
            rows.sort(key=lambda r: (r.get(key) is None, r.get(key)), reverse=reverse)
        if top is not None:
            rows = rows[:top]
        if select:
            rows = [{k: r.get(k) for k in select} for r in rows]
        return rows

    def get(self, table, key_field, key_value):
        for r in self.tables.get(table, []):
            if r.get(key_field) == key_value:
                return dict(r)
        return None

    def search(self, text, tables=None):
        text = str(text).lower()
        hits = []
        for t, rows in self.tables.items():
            if tables and t not in tables:
                continue
            for r in rows:
                blob = " ".join(str(v) for v in r.values()).lower()
                if text in blob:
                    hits.append({"table": t, "record": dict(r)})
        return hits

    # ---- writes (plan then apply) ----
    def plan_upsert(self, table, records, key_field):
        existing = {r.get(key_field): r for r in self.tables.get(table, [])}
        creates, updates, noops = [], [], []
        for inc in records:
            k = inc.get(key_field)
            cur = existing.get(k)
            if cur is None:
                creates.append(inc)
            else:
                diff = {f: [cur.get(f), v] for f, v in inc.items() if cur.get(f) != v}
                if diff:
                    updates.append({"key": k, "diff": diff, "record": inc})
                else:
                    noops.append(k)
        return {
            "op": "upsert",
            "table": table,
            "key_field": key_field,
            "creates": creates,
            "updates": updates,
            "noops": noops,
        }

    def apply(self, plan):
        """Apply a plan to the working copy under out/. Never touches the base fixture."""
        table = plan["table"]
        key_field = plan["key_field"]
        rows = self.tables.setdefault(table, [])
        idx = {r.get(key_field): r for r in rows}
        for c in plan["creates"]:
            rows.append(dict(c))
            self._audit(table, c.get(key_field), "record", None, "created")
        for u in plan["updates"]:
            r = idx.get(u["key"])
            if r is not None:
                for f, (old, new) in u["diff"].items():
                    self._audit(table, u["key"], f, old, new)
                r.update(u["record"])
        self._save()
        return {"applied": len(plan["creates"]) + len(plan["updates"])}

    def _audit(self, entity, rec_id, field, old, new):
        self.audit.append(
            {"entity": entity, "id": rec_id, "field": field, "old": old, "new": new, "user": "<demo-user>"}
        )

    def _save(self):
        if not self.working_path:
            from .config import out_dir

            self.working_path = os.path.join(out_dir(), "working.json")
        with open(self.working_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2)
