#!/usr/bin/env python3
"""
01 — MOVED.

Split into two examples that match how the API actually works:

  * 01-discover.py        — find events (the stream's sync snapshot; there is
                            no REST endpoint that lists events)
  * 03-market-making.py   — the full betslip -> quote -> order flow, under
                            heartbeat protection, dry-run by default

The original version searched for an event by team name against a REST
endpoint that does not exist, and streamed from the retired
`/magic-cpricefeed/v2` feed. Both are gone.

This stub is kept so the move is explained rather than silent. It is safe to
delete.
"""

import sys

sys.exit(__doc__.strip())
