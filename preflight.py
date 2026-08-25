"""Root readiness check: the fixture loads and the engine imports cleanly."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bskit.config import default_store_path  # noqa: E402
from bskit.store import Store  # noqa: E402


def main():
    path = default_store_path()
    if not os.path.exists(path):
        print("NOT READY: fixture missing at %s. Run: python fixtures/make_fixture.py" % path)
        sys.exit(1)
    try:
        s = Store(path)
    except Exception as e:  # noqa: BLE001
        print("NOT READY: cannot load fixture: %s" % e)
        sys.exit(1)
    print("READY: fixture %s with %d tables." % (path, len(s.tables)))
    sys.exit(0)


if __name__ == "__main__":
    main()
