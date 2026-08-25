"""Validate the whole kit against the synthetic fixture with zero real data.

What it checks:
  1. The fixture rebuilds deterministically.
  2. Every skill's preflight reports READY.
  3. Every skill's documented usage command exits cleanly (reads and dry-runs make no
     changes).
  4. Writes are dry-run-first and idempotent: a committed change re-run over its own
     working overlay is a no-op.
  5. The base fixture is never mutated; applied changes land only in out/working.json.

Run:
    python validate.py
Exit code is non-zero if any check fails.
"""
import hashlib
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from scaffold_skills import SPECS  # noqa: E402

PY = sys.executable
OUT_WORKING = os.path.join(ROOT, "out", "working.json")
FIXTURE = os.path.join(ROOT, "fixtures", "org.json")

passes, failures = [], []


def run(args, label):
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    p = subprocess.run([PY] + args, cwd=ROOT, capture_output=True, text=True, env=env)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def check(cond, label, detail=""):
    (passes if cond else failures).append(label)
    print(("PASS " if cond else "FAIL ") + label + (("  -> " + detail) if detail and not cond else ""))


def sha(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def clean_working():
    if os.path.exists(OUT_WORKING):
        os.remove(OUT_WORKING)


def main():
    # 1. deterministic fixture
    code, _ = run(["fixtures/make_fixture.py"], "fixture rebuild")
    check(code == 0, "fixture rebuilds")
    base_hash = sha(FIXTURE)

    # 2 + 3. preflight and usage for every skill
    for domain, slug, *_rest in SPECS:
        pf = "skills/%s/%s/preflight.py" % (domain, slug)
        code, out = run([pf], "preflight %s/%s" % (domain, slug))
        check(code == 0 and "READY" in out, "preflight ready: %s/%s" % (domain, slug), out.strip())

    for spec in SPECS:
        domain, slug = spec[0], spec[1]
        usage = spec[7]
        args = usage.split()[1:]  # drop leading 'python'
        clean_working()
        code, out = run(args, "usage %s/%s" % (domain, slug))
        check(code == 0, "usage runs: %s/%s" % (domain, slug), out.strip()[-300:])

    # 4. write + idempotency: lead-qualify
    clean_working()
    code, out = run(["skills/sales/lead-qualify/skill.py", "--commit"], "lead-qualify commit")
    check(code == 0 and "APPLIED" in out, "lead-qualify applies on commit", out.strip()[-300:])
    code, out = run(["skills/sales/lead-qualify/skill.py", "--working", "out/working.json", "--commit"], "lead-qualify rerun")
    check(code == 0 and "APPLIED" not in out, "lead-qualify idempotent on rerun", out.strip()[-300:])

    # 4b. cross-process quote-to-cash end to end + idempotency
    clean_working()
    code, out = run(["skills/cross-process/quote-to-cash/skill.py", "--order", "S005", "--commit"], "q2c commit")
    check(code == 0 and "APPLIED" in out, "quote-to-cash applies chain", out.strip()[-400:])
    code, out = run(["skills/cross-process/quote-to-cash/skill.py", "--order", "S005", "--working", "out/working.json", "--commit"], "q2c rerun")
    check(code == 0 and "Already fully invoiced" in out, "quote-to-cash idempotent", out.strip()[-400:])

    # 4c. already-invoiced order is a no-op from the start
    clean_working()
    code, out = run(["skills/cross-process/quote-to-cash/skill.py", "--order", "S004"], "q2c s004")
    check("Already fully invoiced" in out, "quote-to-cash no-op for invoiced order", out.strip()[-300:])

    # 4d. master-data-sync applies then aligns
    clean_working()
    code, out = run(["skills/cross-process/master-data-sync/skill.py", "--commit"], "mds commit")
    check(code == 0 and "APPLIED" in out, "master-data-sync applies", out.strip()[-400:])
    code, out = run(["skills/cross-process/master-data-sync/skill.py", "--working", "out/working.json"], "mds rerun")
    check("already aligned" in out, "master-data-sync idempotent", out.strip()[-400:])

    # 5. base fixture never mutated
    check(sha(FIXTURE) == base_hash, "base fixture unchanged after all writes")

    clean_working()
    print("\n%d passed, %d failed" % (len(passes), len(failures)))
    if failures:
        print("FAILED:")
        for f in failures:
            print("  - " + f)
        sys.exit(1)
    print("All checks passed.")


if __name__ == "__main__":
    main()
