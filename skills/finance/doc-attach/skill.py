"""doc-attach: record a document attachment against a business record.

Writes a small attachment manifest to out/ and logs the linkage; it never uploads a real
file and never mutates the target record's business fields. Deterministic manifest keyed by
entity and record id, so re-running updates the same manifest entry.
"""
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
import bskit.skill as sk  # noqa: E402
from bskit import config  # noqa: E402


def run(store, args):
    rec = store.get(args.entity, "id", args.id) if args.entity in store.tables else None
    if not rec:
        return {"text": "No %s record with id '%s'." % (args.entity, args.id), "data": {"error": "not-found"}}
    manifest_path = os.path.join(config.out_dir(), "attachments.json")
    manifest = {}
    if os.path.exists(manifest_path):
        with open(manifest_path, encoding="utf-8") as f:
            manifest = json.load(f)
    key = "%s:%s" % (args.entity, args.id)
    entry = {"entity": args.entity, "record": args.id, "filename": args.name, "note": args.note or ""}
    changed = manifest.get(key) != entry
    lines = ["doc-attach %s -> %s (%s)" % (args.name, key, rec.get("name") or rec.get("title") or args.id)]
    if not changed:
        lines.append("Already attached with the same metadata; no change.")
    elif args.commit:
        manifest[key] = entry
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)
        lines.append("APPLIED: wrote manifest entry to %s" % manifest_path)
    else:
        lines.append("(dry run; pass --commit to write %s)" % manifest_path)
    return {"text": "\n".join(lines), "data": {"key": key, "entry": entry, "changed": changed}}


def add_args(p):
    p.add_argument("--entity", required=True, help="target entity / table")
    p.add_argument("--id", required=True, help="target record id")
    p.add_argument("--name", required=True, help="document file name")
    p.add_argument("--note", help="optional note")


if __name__ == "__main__":
    sk.run_cli(run, "Attach a document to a record (manifest only).", add_args)
