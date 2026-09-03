#!/usr/bin/env python3
"""
01 — Discover what is tradeable right now.

There is no REST endpoint listing events. The WebSocket's initial sync IS the
discovery mechanism: connect, collect ["event", ...] entries until ["sync", ...].

Only events that currently have live prices appear — far fewer than the full
fixture list.

Usage:
    export MAGIC_API_KEY=...
    python examples/01-discover.py            # everything priced
    python examples/01-discover.py fb tennis  # filter by sport
"""

import sys
from collections import Counter

from _common import label, open_stream, sync_events, verify_key


def main(sports):
    verify_key()

    with open_stream() as ws:
        events = sync_events(ws)

    if sports:
        events = [e for e in events if e.get("sport") in sports]

    if not events:
        print("No priced events." + (f" (filtered to {', '.join(sports)})" if sports else ""))
        return

    by_sport = Counter(e.get("sport") for e in events)
    print(f"{len(events)} priced events across {len(by_sport)} sports")
    print("  " + "  ".join(f"{s}={n}" for s, n in by_sport.most_common()))
    print()

    for e in sorted(events, key=lambda e: e.get("start_time") or ""):
        kind = "OUT" if e.get("event_type") == "multirunner" else "   "
        print(f"{e.get('start_time', '?'):<26} {kind} {e.get('sport', '?'):<9} "
              f"{e.get('competition_name', ''):<28} {label(e)}")
        print(f"{'':26}     id: {e.get('event_id')}")


if __name__ == "__main__":
    main(set(sys.argv[1:]))
