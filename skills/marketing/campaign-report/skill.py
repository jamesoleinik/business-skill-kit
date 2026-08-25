"""campaign-report: roll up message performance across channels.

Read-only. Computes open and click rates per message and an overall summary, and flags
messages performing below a click-rate floor.
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
import bskit.skill as sk  # noqa: E402
from bskit import report  # noqa: E402


def _rate(n, d):
    return round(100.0 * n / d, 1) if d else 0.0


def run(store, args):
    rows, tot_sends, tot_opens, tot_clicks = [], 0, 0, 0
    for m in store.table("emailmsg"):
        sends = m.get("sends") or 0
        opens = m.get("opens") or 0
        clicks = m.get("clicks") or 0
        tot_sends += sends
        tot_opens += opens
        tot_clicks += clicks
        rows.append({
            "id": m["id"], "name": m.get("name"), "channel": m.get("channel"),
            "sends": sends, "open_rate": _rate(opens, sends), "click_rate": _rate(clicks, sends),
        })
    rows.sort(key=lambda r: r["click_rate"], reverse=True)
    low = [r for r in rows if r["channel"] == "email" and r["click_rate"] < args.min_click]
    text = "Campaign report: %d message(s), %d sends, overall open %.1f%%, click %.1f%%.\n%s\n\nBelow %.1f%% click (email): %s" % (
        len(rows), tot_sends, _rate(tot_opens, tot_sends), _rate(tot_clicks, tot_sends),
        report.table(rows, ["id", "name", "channel", "sends", "open_rate", "click_rate"]),
        args.min_click, ", ".join(r["id"] for r in low) or "none",
    )
    return {"text": text, "data": {"messages": rows, "totals": {"sends": tot_sends, "opens": tot_opens, "clicks": tot_clicks}, "below_floor": low}}


def add_args(p):
    p.add_argument("--min-click", dest="min_click", type=float, default=5.0, help="click-rate floor in percent")


if __name__ == "__main__":
    sk.run_cli(run, "Roll up campaign message performance.", add_args)
