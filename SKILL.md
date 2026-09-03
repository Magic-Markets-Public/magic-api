---
name: magicmarkets-magic-api
description: >
  MagicMarkets API assistant: peer-to-peer sports markets exchange with
  zero fees and zero commission. Covers the REST API at
  magicmarkets.com/v2/ for creating betslips, placing and closing orders,
  positions, balance and heartbeats, and the WebSocket stream at
  magicmarkets.com/v2/stream for event discovery, live offers, private
  betslip quotes and order updates. Use this skill when the user mentions
  MagicMarkets, the Magic API, magicmarkets.com, P2P sports exchange,
  betslips, placing orders, back/lay/parlay, heartbeats, the price stream,
  register_event, USDT stakes, X-Api-Key auth, betslip_id, order_id,
  request_uuid, or building trading tools against MagicMarkets.
allowed-tools: Bash(curl:*), Bash(python3:*), WebFetch
---

# MagicMarkets API

MagicMarkets is a **peer-to-peer sports markets exchange**: zero fees, zero
commission. Users back and lay against each other; all stakes are USDT.

| Detail | Value |
|--------|-------|
| **REST base** | `https://magicmarkets.com/v2/` |
| **WebSocket** | `wss://magicmarkets.com/v2/stream?api_key=<key>` |
| **REST auth** | `X-Api-Key: <key>` header |
| **WS auth** | `?api_key=<key>` query param (same key) |
| **Stakes** | `["USDT", <amount>]` tuples, always USDT in responses |
| **Prices** | Decimal odds on a fixed tick schedule |

Keys are created on the website: **Settings → API → Add API Key**. The value
is shown once at creation. There is no endpoint for key management.

---

## The published docs are the source of truth

MagicMarkets publishes complete, current documentation. **Fetch it rather
than trusting memory.** This skill is a working guide, not a replacement:

| URL | What |
|-----|------|
| `https://magicmarkets.com/llms.txt` | Index (~1 KB) |
| `https://magicmarkets.com/llms-full.txt` | Full reference, ~109 KB Markdown |
| `https://magicmarkets.com/v2/openapi.yaml` | OpenAPI 3.1: 18 paths, 29 schemas |
| `https://magicmarkets.com/v2/openapi.json` | Same spec as JSON |

Fetch `llms-full.txt` whenever you need exact request/response schemas, the
full sport-code table, per-endpoint error codes, or anything this file
summarises. Anything not covered below is covered there.

> `https://magicmarkets.com/docs` (the Redoc page linked from `llms.txt`)
> currently 404s. Use `llms-full.txt` or the OpenAPI spec instead.

**Retired: do not use.** `pro.magicmarkets.com` (301s to the root domain)
and the old `/magic-cpricefeed/v2` WebSocket (returns 502). Any code or doc
still referencing these is stale.

---

## Glossary

**Betslip**: a *quote request*. You name a selection (`sport`, `event_id`,
`bet_type`) and get a `betslip_id`. The prices arrive separately as `pmm`
messages on the WebSocket. Betslips are short-lived: watch `expiry_ts`.

**Order**: a *commitment*. A `betslip_id` plus a `price` and `stake`. Moves
`open → pending → done | failed`. `done` means **filled, not settled**: the
final `profit_loss` lands after the event finishes.

**Offer**: one priced selection on the public feed, keyed by
`(sport, event_id, bet_type)`. `for` and `against` on the same selection are
two separate offers.

**pmm**: your *private* quote for an open betslip, delivered on the WS.

**Heartbeat**: a deadman's switch. If you stop refreshing it, the server
closes every open order on the account, across all sessions and API keys.
Matched bets are unaffected.

---

## The flow

Discovery, prices, quotes and order updates all come over the WebSocket. REST
is for committing. You will normally hold one socket open and call REST
alongside it.

```
1. GET /v2/balance/            verify the key over REST first
2. connect wss://…/v2/stream   collect ["event", …] until ["sync", …]
3. ["register_event", sport, event_id]   → ["offer", …] snapshot
4. pick an offer → its sport/event_id/bet_type is all you need
5. POST /v2/betslips/          → betslip_id
6. wait for ["pmm", …] on the WS matching your betslip_id → prices
7. POST /v2/orders/            → order_id
8. watch ["order", …] / ["bet", …] on the WS until done|failed
```

**Verify the key over REST before opening the socket.** A missing or invalid
`api_key` fails the WebSocket *handshake* (non-101), which surfaces as an
opaque client-side error. Checking `GET /v2/balance/` first turns a confusing
socket failure into a clear `401 auth_error`.

---

## Wire format: read this before writing any WS code

**Every** server frame is a batch envelope:

```json
{"ts": 1586042815.269000, "data": [ <message>, <message>, … ]}
```

Each `data[]` entry is an array whose first element is a type tag:

```python
frame = json.loads(ws.recv())
for entry in frame["data"]:
    tag = entry[0]          # "event" | "offer" | "pmm" | "order" | "sync" | …
    payload = entry[1]
```

Batching boundaries carry **no meaning**. Never rely on ordering, grouping,
or a type appearing exactly once per frame. Always iterate `data[]` and
dispatch on `entry[0]`.

### Discovery

On connect the server dumps the currently-priced events as `["event", {…}]`
entries, ending with `["sync", {"session_id": …}]`. This is the discovery
mechanism: **there is no REST endpoint for listing events.**

The snapshot contains only events that currently have prices, and may span
several envelopes. After sync, changed events re-arrive as `["event", …]` and
events losing prices arrive as `["remove_event", …]`.

Two event shapes: dispatch on `event_type`:
- `normal`: a match; carries `home` and `away`.
- `multirunner`: outright/futures; no home/away, carries a `teams` array
  (`[{"team_id", "name"}, …]`) and an `end_time`.

### Commands

```json
["register_event", "<sport>", "<event_id>"]     → offer snapshot, then ok response
["unregister_event", "<sport>", "<event_id>"]   → ok (idempotent)
["list_registered_events"]                       → {"registered_events": [[sport, id], …]}
["echo", "anything"]                             → echoed back verbatim
```

Registering an event with no prices is **not** an error: you get an empty
snapshot. There is no "unknown event" error.

### Message types you will see

`event`, `remove_event`, `sync`, `offer`, `remove_offer`, `pmm`, `betslip`,
`betslip_closed`, `order`, `bet`, `balance`, `xrate`, `info`, `response`,
`clear_events`, plus in-play state (`event_time`, `event_score`,
`event_red_cards`, `ir_info`).

Two that matter for correctness:
- **`clear_events`**: the server lost its upstream feed. Discard all event,
  offer and live-state data you hold; a fresh snapshot follows.
- **`betslip_closed`**: `{betslip_id, close_reason}`. No further `pmm` will
  arrive; create a new betslip to re-quote.

### Offers

```json
["offer", {
  "sport": "fb", "event_id": "2026-06-15,1001,2002",
  "bet_type": "for,ah,h,1", "market_type": "ah", "in_running": false,
  "price_list": [
    {"effective": {"price": 2.0, "min": ["USDT", 5.0], "max": ["USDT", 150.0]}},
    {"effective": {"price": 1.99, "min": null, "max": ["USDT", 80.0]}}
  ]
}]
```

`price_list` is sorted by decimal price **descending**, one entry per price.
`min` is `null` when there is no minimum; `max` is the stake available at that
price. An empty `price_list` means no liquidity: pick another offer.

---

## Bet types

`bet_type` is a comma-separated string; the first token is the direction:
`for` (back) or `against` (lay). The rest encodes market, handicap and
outcome: e.g. `for,ah,h,1` backs the home team on the +1 Asian handicap.

**Never construct a `bet_type` by hand.** Read it off an offer and pass it
through verbatim. To validate one, use
`GET /v2/sports/{sport}/bet_types/{bet_type}/`.

`sport` codes are lowercase and period-scoped (`fb`, `fb_ht`, `basket_q1`,
`tennis`, `af`, `horse`, `esports`, `politics`, …). Treat the list as **open**:
new codes are added; do not hard-fail on an unknown one. On parlays, `sport`
is the literal string `parlay` and per-leg sports sit inside `legs[]`.

Full sport table and market grammar: fetch `llms-full.txt`.

---

## Prices and ticks

All prices sit on a fixed tick schedule that widens as the price grows
(0.01 from 1.01-2, 0.02 from 2-3, 0.05 from 3-4, 0.10 from 4-6, 0.20 from
6-10, 0.50 from 10-20, then 1, 2, 5, 10).

- Prices from the feed are **already on-tick**: quote them straight through.
- A price you submit is snapped to the nearest tick that does not tighten
  your limit: **down** for `for`, **up** for `against`.

---

## Errors

REST errors share one envelope:

```json
{"status": "error", "code": "validation_error",
 "data": {"validation_errors": {"bet_type": ["invalid_bet_type"]}}}
```

Always check `status` before reading `data`. Branch on `code`, not the HTTP
status alone.

| HTTP | `code` | Meaning |
|------|--------|---------|
| 400 | `validation_error` | `data.validation_errors` is `{field: [reason]}`; cross-field issues in `non_field_errors` |
| 400 | `order_closed` | Order exists but is already closed/settled |
| 401 | `auth_error` | Key missing, malformed, or rejected |
| 403 | `forbidden` | Valid key, action not allowed |
| 404 | `not_found` | Unknown, or not visible to this key |
| 409 | `order_already_created` | `request_uuid` reused; `data` has the existing `order_id` |
| 409 | `limit_reached` | Per-customer cap hit |
| 429 | `throttled` | Honour `Retry-After` / `data.retry_after` |
| 500 | `server_error` | `data` carries a support token: quote it |

WebSocket command errors arrive **in-band** and leave the socket open:
`["response", {"status": "error", "code": "…"}]`. Codes: `bad_json`,
`invalid_input`, `already_registered`, `customer_event_limit_exceeded`,
`invalid_customer`, `system_error`. Treat any other code as opaque: log and
retry with backoff.

**Silent drops.** Three failures close an established connection with a raw
TCP close: no close frame, no error: backpressure (you read too slowly), I/O
error, and internal error. Always implement reconnect-with-backoff and
re-register your events; do not assume a quiet socket is a healthy one.

---

## Rate limits

Per **account** (all keys share one budget), sliding window:

| Applies to | Limit |
|---|---|
| All endpoints | 100 req/s burst, 1200 req/min sustained |
| `POST /v2/betslips/` | 10 req/s |
| `POST /v2/orders/` | 5 req/s |

Placement limits are dedicated budgets, not drawn from the general one. No
daily caps, no per-IP limit. Success responses carry **no** remaining-quota
header, so track your own rate. The WS stream has no message-rate limit.

---

## Idempotency

`POST /v2/orders/` accepts an optional `request_uuid`. Reusing one returns
`409 order_already_created` with the existing `order_id`: so a retry after a
timeout is safe and will not double-place. **Always send one** from automated
code. `GET /v2/orders/tracked/{uuid}/` retrieves an order by its
`request_uuid` for up to 6 hours after placement.

---

## Endpoint index

Betslips: `GET|POST /v2/betslips/` · `GET /v2/betslips/{id}/` ·
`POST /v2/betslips/{id}/refresh/`

Orders: `GET|POST /v2/orders/` · `GET /v2/orders/{id}/` ·
`GET /v2/orders/updates/` · `GET /v2/orders/tracked/{uuid}/` ·
`POST /v2/orders/{id}/close/` · `POST /v2/orders/close_many/` ·
`POST /v2/orders/close_all/` · `GET /v2/orders/position/`

Account: `GET /v2/balance/` · `GET /v2/xrates/`

Heartbeats: `GET|POST /v2/heartbeats/` · `GET|DELETE /v2/heartbeats/{id}/` ·
`POST /v2/heartbeats/{id}/refresh/`

Reference: `GET /v2/sports/{sport}/bet_types/{bet_type}/`

Stream: `GET /v2/stream` (WebSocket upgrade)

Exact schemas, parameters and per-endpoint error codes: fetch
`https://magicmarkets.com/llms-full.txt`.

---

## Deeper reference

- [`references/streaming.md`](references/streaming.md): full WebSocket protocol.
- [`references/rest.md`](references/rest.md): REST flow, betslip/order shapes, heartbeats.
- [`references/recipes.md`](references/recipes.md): task-shaped patterns.
- [`examples/`](examples/): runnable Python scripts.

---

## Common mistakes

- **Using `/magic-cpricefeed/v2`.** Retired, returns 502. It is `/v2/stream`.
- **Using `pro.magicmarkets.com`.** Retired; 301s to the root domain.
- **Looking for a REST endpoint to list events.** There isn't one: discovery
  is the WS sync stream.
- **Treating a frame as a message.** Frames are batch envelopes; iterate `data[]`.
- **Expecting prices in the `POST /v2/betslips/` response.** They arrive as
  `pmm` messages on the WebSocket.
- **Constructing `bet_type` strings.** Read them off offers.
- **Treating `done` as settled.** It means filled; `profit_loss` finalises later.
- **Assuming a quiet socket is healthy.** Silent TCP closes are documented.
  Reconnect with backoff and re-register.
- **Omitting `request_uuid`** on automated order placement.
