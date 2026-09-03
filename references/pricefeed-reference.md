# RETIRED: see [`streaming.md`](streaming.md)

This file documented the **`/magic-cpricefeed/v2`** WebSocket, which has been
retired. That endpoint now returns **502 Bad Gateway** and no MagicMarkets
documentation references it.

Its contents were wrong in ways that would break any client written from them:

| This file said | Reality |
|---|---|
| `wss://pro.magicmarkets.com/magic-cpricefeed/v2` | `wss://magicmarkets.com/v2/stream` |
| `["watch_event", [comp_id, sport, event_id]]` | `["register_event", sport, event_id]` |
| `["offers_event", …]` messages | `["offer", …]` entries inside a `{"ts", "data"}` envelope |
| `pro.magicmarkets.com` host | `magicmarkets.com` (the `pro.` subdomain 301s) |

**Use [`streaming.md`](streaming.md) instead**, or fetch the canonical source:
`https://magicmarkets.com/llms-full.txt` (Streaming API section).

This stub is kept only so that anything still linking here lands somewhere
truthful. It is safe to delete.
