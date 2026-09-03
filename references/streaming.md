# MagicMarkets: WebSocket stream reference

`wss://magicmarkets.com/v2/stream?api_key=<key>[&lang=en]`

A separate service from the REST API. This is where **event discovery, live
offers, private betslip quotes, and order/bet updates** all arrive.

> Canonical source: `https://magicmarkets.com/llms-full.txt` (Streaming API
> section). Fetch it when you need detail beyond this file.

---

## Connection

| Param | Required | Notes |
|-------|----------|-------|
| `api_key` | yes | Same value as the `X-Api-Key` header |
| `lang` | no | `en` (default), `ko`, `zh-hans` |

**Auth is enforced at the HTTP handshake.** A missing or invalid key fails the
upgrade with a non-101 response, and the `websockets` library raises
`InvalidStatus`. An invalid key takes slightly longer to reject than a missing
one. **Verify the key against a REST endpoint before opening the socket** so
an auth problem reads as `401 auth_error` rather than an opaque socket error.

**The server does not restrict the `Origin` header.** Browser-based clients
can connect directly with the `api_key` query parameter, including pages
opened from `file://`. No server-side proxy is required.

The retired `/magic-cpricefeed/v2` endpoint returns 502. Do not use it.

---

## Wire format

Every frame the server sends is a batch envelope:

```json
{"ts": 1586042815.269000, "data": [ <message>, <message>, … ]}
```

- `ts`: Unix seconds with microsecond precision, stamped on write.
- `data`: one or more messages, each an array with a leading type tag.

Multiple messages may be batched: a register snapshot and its `response`
together, offers alongside account updates. **Batching boundaries are not
semantically meaningful.** Iterate `data[]` and dispatch on `entry[0]`. Never
rely on ordering, grouping, or a type appearing exactly once per frame.

```python
for entry in json.loads(ws.recv())["data"]:
    match entry[0]:
        case "event":  ...
        case "offer":  ...
        case "pmm":    ...
```

---

## Initial sync

On connect the server sends a snapshot of currently-priced events, then a
`["sync", {"session_id": …}]` marker. The `session_id` is useful when
correlating with REST errors or contacting support.

```json
{"ts": 1586042815.269, "data": [
  ["event", {"event_type": "normal", "sport": "fb",
             "event_id": "2026-06-15,1001,2002", "competition_id": 1,
             "competition_name": "England Premier League",
             "competition_country": "XE", "home": "Arsenal", "away": "Chelsea",
             "event_name": "Arsenal vs. Chelsea", "ir_status": "pre_event",
             "start_time": "2026-06-15T15:00:00Z"}],
  ["event", {"event_type": "multirunner", "sport": "af",
             "event_id": "2026-02-23,multirunner,100364405",
             "competition_id": 545, "competition_name": "USA NFL",
             "teams": [{"team_id": 21614, "name": "Arizona Cardinals"}, …],
             "event_name": "NFL Super Bowl Winner",
             "start_time": "2026-02-23T21:00:00Z",
             "end_time": "2027-02-14T21:00:00Z"}],
  ["sync", {"session_id": "…"}]
]}
```

**This snapshot is not the full fixture list**: only events that currently
have live prices. It may span several envelopes; `sync` is the last `data[]`
entry of the final one.

Two shapes, dispatch on `event_type`:

| `event_type` | Carries | Notes |
|---|---|---|
| `normal` | `home`, `away` | A match |
| `multirunner` | `teams[]`, `end_time` | Outright / futures; no home/away |

After sync: changed events re-arrive as `["event", …]`; events losing all
prices arrive as `["remove_event", {"sport", "event_id", …}]`.

---

## Commands

### `register_event`

```json
["register_event", "<sport>", "<event_id>"]
```

Server immediately sends one `["offer", …]` per active bet type (the
snapshot), then an ok response: typically batched in one envelope:

```json
{"ts": …, "data": [["offer", {…}], ["offer", {…}],
                   ["response", {"status": "ok", "data": null}]]}
```

From then on, whenever offers on the event change the **full current set** is
re-broadcast, and any bet type that has lost all liquidity arrives as
`["remove_offer", …]`.

Registering an event with no prices is **not** an error: you get an empty
snapshot, and offers start flowing if it becomes priced. Prefer event ids you
saw in the sync stream.

### `unregister_event`

```json
["unregister_event", "<sport>", "<event_id>"]
```

Returns ok even when the event was not registered (idempotent). No further
`offer` / `remove_offer` for that event.

### `list_registered_events`

```json
["list_registered_events"]
→ ["response", {"status": "ok", "data": {
     "registered_events": [["fb", "2026-06-15,1001,2002"],
                           ["tennis", "2026-06-16,501,502"]]}}]
```

### `echo` (keepalive)

```json
["echo", "any-payload"]
→ ["response", {"status": "ok", "data": ["any-payload"]}]
```

Arguments optional, any JSON, echoed verbatim. The server also emits an
`["info", …]` entry every few seconds, so an idle connection still receives
regular traffic.

---

## Market data messages

### `offer`

One offer per `(sport, event_id, bet_type)` triple. The `bet_type` encodes
market, handicap, outcome and direction, so `for` and `against` on the same
selection are **two separate offers**.

```json
["offer", {
  "sport": "fb", "event_id": "2026-06-15,1001,2002",
  "bet_type": "for,ah,h,1", "market_type": "ah", "in_running": false,
  "price_list": [
    {"effective": {"price": 2.0,  "min": ["USDT", 5.0], "max": ["USDT", 150.0]}},
    {"effective": {"price": 1.99, "min": null,          "max": ["USDT", 80.0]}}
  ]
}]
```

Each entry is `{"effective": {"price", "min", "max"}}`:
- `min`: minimum stake at that price; `null` when there is none.
- `max`: total stake available at that price. Always `["USDT", amount]`;
  a price with no available stake is simply not published.

Ordered by `price` **descending**, at most one entry per price.

### `remove_offer`

```json
["remove_offer", {"sport": "fb", "event_id": "…", "bet_type": "for,ah,h,1"}]
```

That bet type has no remaining liquidity on the event.

### Live event state (in-play)

```json
["event_time",      {"sport": "fb", "event_id": "…", "time": ["1h", 23]}]
["event_score",     {"sport": "fb", "event_id": "…", "score": [1, 0]}]
["event_red_cards", {"sport": "fb", "event_id": "…", "score": [0, 1]}]
```

- `time`: `[period, minutes]`; football periods are `"1h"`, `"2h"`, `"ht"`.
  `null` when no clock is available.
- `score`: `[home, away]`. `event_red_cards` reuses the `score` key.
- `["ir_info", {…}]`: full in-running snapshot, fields vary by sport;
  `["remove_ir_info", …]` signals it is gone. Both informational.
- `["event_exchange_dark_liquidity", {"sport", "event_id", "lines"}]`: rough
  estimate of extra liquidity beyond published offers. Informational.

Payloads are sport-specific. Treat unknown state messages as informational.

---

## Account messages

Delivered as siblings of market data inside the same envelope.

```json
{"ts": …, "data": [
  ["balance", {"balance": ["USDT", 10000.1], "open_stake": ["USDT", 152.55]}],
  ["xrate",   {"ccy": "EUR", "rate": 1.1347}],
  ["order",   {…}], ["bet", {…}], ["pmm", {…}], ["betslip", {…}], ["info", {…}]
]}
```

| Tag | Meaning | Currency |
|---|---|---|
| `balance` | `balance`, `open_stake` | Account's native currency |
| `xrate` | Exchange rate update | - |
| `order` | `want_stake`, `stake`, `profit_loss`; nested `bets[]` | USDT |
| `bet` | `want_stake`, `got_stake`, `profit_loss` | USDT |
| `pmm` | Live private quote for an open betslip | USDT |
| `betslip` | Betslip state | USDT |
| `betslip_closed` | `{betslip_id, close_reason}`: expired or closed | - |
| `info` | Feed status; `registered_events` is the count on this connection | - |
| `clear_events` | Upstream feed lost: **discard all cached market data** | - |

The order, presence and count of entry types within `data[]` are **not
contractual**.

### `pmm`: your private quote

```json
["pmm", {
  "betslip_id": "65b6ff7da480479b9dda1c7ff765c434",
  "sport": "fb", "event_id": "2026-06-15,1001,2002",
  "bet_type": "for,ah,h,1", "status": {"code": "success"},
  "price_list": [{"effective": {"price": 2.0, "min": ["USDT", 5.0],
                                "max": ["USDT", 150.0]}}],
  "total": ["USDT", 150.0]
}]
```

Same `price_list` format as offers. A pmm whose `price_list` stays empty means
no liquidity for that selection right now: pick another offer and re-quote.

### `clear_events` handling

The server lost its upstream market data feed. Discard **all** event, offer
and live-state data you hold. A fresh snapshot (events, then `sync`) follows
when the feed recovers. Failing to clear leaves you trading on stale prices.

---

## Errors

### In-band (socket stays open)

```json
{"ts": …, "data": [["response", {"status": "error", "code": "<code>"}]]}
```

| Code | When |
|------|------|
| `bad_json` | Frame is not valid JSON, not an array, or an empty array |
| `invalid_input` | Command name not a string / not recognised, or wrong argument shape |
| `already_registered` | `register_event` for an already-registered event |
| `customer_event_limit_exceeded` | Would exceed the registered-events cap (counted across **all** your connections). Unregister something first |
| `invalid_customer` | Feed does not recognise your customer record yet (e.g. after a server restart). Retry with backoff |
| `system_error` | Transient server-side failure: retry with backoff |

There is **no** "unknown event" error. Treat any other code as **opaque**:
log it and retry after a short backoff.

### Silent drops

Three classes of failure drop an *established* connection with a raw TCP
close: no WebSocket close frame, no in-band error:

1. **Backpressure**: you are reading too slowly and the server's outbound
   buffer overflows. Reconnect and resume.
2. **I/O error**: any read/write failure on the socket.
3. **Internal error**: rare, server-side, not client-triggerable, and
   observably identical to an I/O error.

Always reconnect with backoff and **re-register your events**: registrations
do not survive a reconnect. Do not treat a quiet socket as a healthy one.

---

## Minimal client

```python
import json, os
from websockets.sync.client import connect

KEY = os.environ["MAGIC_API_KEY"]
ws = connect(f"wss://magicmarkets.com/v2/stream?api_key={KEY}")

events, synced = [], False
while not synced:
    for entry in json.loads(ws.recv())["data"]:
        if entry[0] == "event":
            events.append(entry[1])
        elif entry[0] == "sync":
            synced = True

ev = events[0]
ws.send(json.dumps(["register_event", ev["sport"], ev["event_id"]]))

offers, registered = [], False
while not registered:
    for entry in json.loads(ws.recv())["data"]:
        if entry[0] == "offer":
            offers.append(entry[1])
        elif entry[0] == "response":
            if entry[1]["status"] != "ok":
                raise SystemExit(f"register failed: {entry[1]['code']}")
            registered = True
```
