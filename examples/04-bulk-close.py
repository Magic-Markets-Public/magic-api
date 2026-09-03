#!/usr/bin/env python3
"""
04 — Inspect and bulk-close open orders.

DRY RUN BY DEFAULT — lists what would close. Pass --live to actually close.

Prefers close_many/ over close_all/: close_all takes no filter and is
irreversible, so this enumerates explicitly unless you ask for everything.

Usage:
    export MAGIC_API_KEY=...
    python examples/04-bulk-close.py                 # list all open orders
    python examples/04-bulk-close.py fb              # list open football orders
    python examples/04-bulk-close.py fb --live       # close them
    python examples/04-bulk-close.py --all --live    # close_all/ (no filter)
"""

import sys

from _common import rest, verify_key


def main(sport_filter, live, use_close_all):
    verify_key()

    if use_close_all:
        if not live:
            print("DRY RUN — would call POST /orders/close_all/ (every open order)")
            return
        rest("POST", "/orders/close_all/")
        print("close_all/ sent")
        return

    orders = rest("GET", "/orders/") or []
    openish = [o for o in orders if not o.get("closed")]
    if sport_filter:
        openish = [o for o in openish if o.get("sport") == sport_filter]

    if not openish:
        print("No open orders matched.")
        return

    print(f"{len(openish)} open order(s):")
    for o in openish:
        print(f"  {o['order_id']:<12} {o.get('sport', '?'):<9} "
              f"{o.get('bet_type', '?'):<26} @{o.get('want_price')} "
              f"{o.get('want_stake')}")

    if not live:
        print("\nDRY RUN — pass --live to close these.")
        return

    ids = [o["order_id"] for o in openish]
    rest("POST", "/orders/close_many/", json={"order_ids": ids})
    print(f"close_many/ sent for {len(ids)} order(s)")
    # Closing an already-closed order returns 400 order_closed, which is
    # distinct from 404 not_found.


if __name__ == "__main__":
    positional = [a for a in sys.argv[1:] if not a.startswith("--")]
    main(sport_filter=positional[0] if positional else None,
         live="--live" in sys.argv,
         use_close_all="--all" in sys.argv)
