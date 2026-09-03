# MagicMarkets: Recipes

Task-shaped patterns. All against `https://magicmarkets.com/v2/` and
`wss://magicmarkets.com/v2/stream`.

Assumes `MAGIC_API_KEY` is exported. Runnable versions live in
[`../examples/`](../examples/). For concepts see [`../SKILL.md`](../SKILL.md);
for schemas see [`rest.md`](rest.md) and [`streaming.md`](streaming.md).

---

## A: See what is tradeable right now

There is no REST endpoint listing events. The stream's initial sync **is** the
discovery mechanism: connect, collect `["event", …]` entries until
`["sync", …]`, then disconnect if that is all you need.

```python
import json, os
from websockets.sync.client import connect

with connect(f"wss://magicmarkets.com/v2/stream?api_key={os.environ['MAGIC_API_KEY']}") as ws:
    events, synced = [], False
    while not synced:
        for entry in json.loads(ws.recv())["data"]:
            if entry[0] == "event":
                events.append(entry[1])
            elif entry[0] == "sync":
                synced = True

for e in sorted(events, key=lambda e: e["start_time"]):
    label = e.get("event_name") or f"{e.get('home')} v {e.get('away')}"
    print(f"{e['start_time']}  {e['sport']:<8} {label}")
```

This returns only events **with live prices**: far fewer than the full
fixture list. Expect single or low double digits outside peak hours.

---

## B: Place a back order end to end

```
verify key → connect stream → sync → register_event → pick offer
  → POST /v2/betslips/ → wait for pmm → POST /v2/orders/ → watch order
```

1. `GET /v2/balance/`: fail fast on a bad key.
2. Connect the stream; collect events until `sync`.
3. `["register_event", sport, event_id]`; collect `["offer", …]` until the ok
   `["response", …]`.
4. Pick an offer with a non-empty `price_list`. Its `sport`, `event_id` and
   `bet_type` are all you need: pass them through verbatim.
5. `POST /v2/betslips/` → `betslip_id`.
6. Wait for `["pmm", …]` on the socket whose `betslip_id` matches and whose
   `price_list` is non-empty.
7. `POST /v2/orders/` with `betslip_id`, `price` from the quote, `stake`,
   `duration`, and a fresh `request_uuid`.
8. Watch `["order", …]` until `status` is `done` or `failed`.

### curl variant

Assumes you already have `sport` / `event_id` / `bet_type` from an offer.

```bash
API=https://magicmarkets.com/v2
H="X-Api-Key: $MAGIC_API_KEY"

# 1. deadman's switch (10-300s)
HB=$(curl -s -X POST "$API/heartbeats/" -H "$H" -H 'Content-Type: application/json' \
  -d '{"timeout": 60}' | jq -r .data.heartbeat_id)

# 2. betslip. Note: no prices in this response
BS=$(curl -s -X POST "$API/betslips/" -H "$H" -H 'Content-Type: application/json' \
  -d '{"sport":"fb","event_id":"2026-06-15,1001,2002","bet_type":"for,ah,h,1","betslip_type":"normal"}' \
  | jq -r .data.betslip_id)

# 3. poll for the quote (or read pmm off the stream)
curl -s "$API/betslips/$BS/" -H "$H" | jq '.data.price_list'

# 4. place, with an idempotency key
curl -s -X POST "$API/orders/" -H "$H" -H 'Content-Type: application/json' \
  -d "{\"betslip_id\":\"$BS\",\"price\":2.0,\"stake\":[\"USDT\",10.0],\"duration\":5.0,\"request_uuid\":\"$(uuidgen)\"}" | jq

# 5. refresh well inside the timeout, then release
curl -s -X POST "$API/heartbeats/$HB/refresh/" -H "$H" > /dev/null
curl -s -X DELETE "$API/heartbeats/$HB/" -H "$H" > /dev/null
```

---

## C: Maintain a live price book

Register the events you care about and keep a dict keyed by
`(sport, event_id, bet_type)`.

```python
book = {}

for entry in json.loads(ws.recv())["data"]:
    tag = entry[0]
    p = entry[1] if len(entry) > 1 else None
    if tag == "offer":
        book[(p["sport"], p["event_id"], p["bet_type"])] = p["price_list"]
    elif tag == "remove_offer":
        book.pop((p["sport"], p["event_id"], p["bet_type"]), None)
    elif tag == "clear_events":
        book.clear()          # upstream feed lost: everything held is stale
```

Three rules that separate a correct book from a subtly wrong one:

- **`offer` is a full replacement** for that triple, not a delta. Overwrite,
  do not merge.
- **`remove_offer`** means that bet type has no liquidity left. Delete it:
  do not leave last-known prices in the book.
- **`clear_events`** means the server lost its upstream feed. Drop everything
  and wait for the fresh snapshot + `sync`.

`price_list` is sorted descending, so `price_list[0]["effective"]` is the best
available price.

---

## D: Market-making with heartbeat protection

Any unattended strategy should sit inside a heartbeat so a crashed process
does not leave exposure open.

```
create heartbeat (timeout T)
  loop:
    refresh every T/3
    re-quote, place / close orders
  on exit: close orders, delete heartbeat
```

Choosing `T` (valid range **10-300 s**):
- Short (10-30 s): tight protection, but a slow tick risks self-inflicted
  closure. Refresh at `T/3`.
- Long (120-300 s): tolerant of hiccups, leaves exposure open longer after a
  genuine crash.

Refresh on a timer **independent of your trading loop**. If refreshing is
coupled to a loop that can block on a slow REST call, a stall expires the
heartbeat and closes your book.

Always send a `request_uuid`. Under retry, a reused uuid returns
`409 order_already_created` with the existing `order_id`: safe. Without one,
a timeout-then-retry can double-place.

---

## E: Bulk-close

```bash
API=https://magicmarkets.com/v2
H="X-Api-Key: $MAGIC_API_KEY"

# always look before closing
curl -s "$API/orders/" -H "$H" | jq '[.data[] | select(.closed == false)
      | {order_id, sport, bet_type, want_price, want_stake}]'

# one order
curl -s -X POST "$API/orders/12345/close/" -H "$H"

# a specific set
curl -s -X POST "$API/orders/close_many/" -H "$H" -H 'Content-Type: application/json' \
  -d '{"order_ids": [12345, 12346]}'

# everything: unfiltered and irreversible
curl -s -X POST "$API/orders/close_all/" -H "$H"
```

`close_all` takes no filter. Enumerate and close explicitly unless you really
do mean every open order. Closing an already-closed order returns
`400 order_closed`, distinct from `404 not_found`.

---

## F: Multi-event streaming

Register many events on one socket: do not open a socket per event.

```python
for ev in events[:20]:
    ws.send(json.dumps(["register_event", ev["sport"], ev["event_id"]]))
```

- The registered-event cap is counted across **all** your connections.
  Exceeding it returns `customer_event_limit_exceeded`: unregister first.
- `["list_registered_events"]` returns the current set.
- Registrations **do not survive a reconnect**. Re-register after any drop.
- Read fast. Backpressure closes the connection silently with a raw TCP close:
  no close frame, no error. If you do heavy work per message, hand frames to
  a queue and process them off the read loop.

---

## Cross-cutting patterns

### Frame parsing

Every frame is `{"ts": …, "data": [...]}`. Never assume one message per frame,
a fixed order, or that a type appears exactly once.

```python
for entry in json.loads(raw)["data"]:
    tag = entry[0]
    payload = entry[1] if len(entry) > 1 else None
```

### Reconnect

```python
delay = 1
while True:
    try:
        with connect(url) as ws:
            delay = 1
            resync(ws)          # collect events → sync
            re_register(ws)     # registrations are not preserved
            pump(ws)
    except Exception:
        time.sleep(delay)
        delay = min(delay * 2, 60)
```

A silent drop looks like a clean EOF. Treat any exit from `pump()` as a
reconnect trigger.

### Auth failures

Verify with `GET /v2/balance/` before connecting. WebSocket auth fails at the
handshake with a non-101 response, which client libraries surface as an opaque
error (`websockets` raises `InvalidStatus`): much harder to diagnose than a
`401 auth_error` from REST.
