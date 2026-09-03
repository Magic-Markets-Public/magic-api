#!/usr/bin/env python3
"""
05 — REMOVED.

This example compared MagicMarkets prices against external benchmarks using
`GET /web/offerhist/{sport}/{event_id}/{bet_type}/`.

That endpoint returns 404. It is not in the published OpenAPI spec
(https://magicmarkets.com/v2/openapi.yaml) and is not referenced anywhere in
https://magicmarkets.com/llms-full.txt — it appears never to have been part
of the public API.

There is currently no supported endpoint for external price history, so there
is no faithful replacement. For MagicMarkets' own price history, keep your own
series from the `offer` messages on the stream (see 02-price-book.py).

This stub is kept so the removal is explained rather than silent. It is safe
to delete.
"""

import sys

sys.exit(__doc__.strip())
