# MagicMarkets: REST reference

Base: `https://magicmarkets.com/v2/` · Auth: `X-Api-Key: <key>` on every request.

> Canonical source: `https://magicmarkets.com/llms-full.txt` and
> `https://magicmarkets.com/v2/openapi.yaml`. Fetch those for exact schemas,
> every optional field, and per-endpoint error codes. This file covers the
> shapes you need in practice.

All responses share one envelope: check `status` before reading `data`:

```json
{"status": "ok", "data": …}
{"status": "error", "code": "<code>", "data": <details>}
```

---

## Betslips

### `POST /v2/betslips/`: create

Normal / lay: supply `sport`, `event_id`, `bet_type`. Parlay: supply `legs`
instead.

```json
{
  "sport": "fb",
  "event_id": "2026-06-15,1001,2002",
  "bet_type": "for,ah,h,1",
  "betslip_type": "normal"
}
```

| Field | Notes |
|---|---|
| `sport`, `event_id`, `bet_type` | Required for `normal` / `lay`. Copy verbatim off an offer |
| `legs[]` | For parlays: `[{sport, event_id, bet_type}, …]` |
| `betslip_type` | `normal` (default), `lay`, `parlay` |
| `equivalent_bets` | Default `true` |
| `exclude_danger` | Only use liquidity sources with no bets in danger status |
| `user_data` | Free-form string echoed back |

Returns **201** with `betslip_id`, `bet_type_description`, `expiry_ts`,
`is_open`, `close_reason`, `betslip_type`, `legs[]`.

**The create response carries no prices.** Quotes are gathered
asynchronously. Either:
- read them off the WebSocket as `["pmm", …]` entries matching your
  `betslip_id` (preferred: you should already hold the socket open), or
- poll `GET /v2/betslips/{betslip_id}/` until `price_list` populates.

Typically a couple of seconds. Watch `expiry_ts`: betslips are short-lived.
An empty `price_list` that stays empty means no liquidity; pick another offer.

On parlays, `sport` comes back as the literal `parlay` and `event_id` as `""`.

### Others

- `GET /v2/betslips/`: list.
- `GET /v2/betslips/{betslip_id}/`: fetch one, including `price_list`.
- `POST /v2/betslips/{betslip_id}/refresh/`: re-quote an existing betslip.

---

## Orders

### `POST /v2/orders/`: place

```json
{
  "betslip_id": "65b6ff7da480479b9dda1c7ff765c434",
  "price": 2.0,
  "stake": ["USDT", 10.0],
  "duration": 5.0,
  "request_uuid": "…"
}
```

| Field | Notes |
|---|---|
| `betslip_id` | Required |
| `price` | Decimal. Off-tick snaps **down** for `for`, **up** for `against` |
| `stake` | `["USDT", amount]` |
| `duration` | Order lifetime in **seconds**, default 15 |
| `request_uuid` | Idempotency key: **always send one** from automated code |
| `exchange_mode` | `make_and_take` (default), `take_only`, `dark`. See below |
| `keep_open_ir` | Keep the order open when the event goes in-play |
| `accept_partial_fill` | Default `true` |
| `accept_better_price` | Default `true` |
| `force_want_price` | Force the requested price |
| `min_taker_want_stake` | Stake tuple or `null`. Pair with `dark` to stop small probe orders discovering your price |
| `current_score` | `[home, away]` score assertion. See below |
| `exclude_danger` | As per betslips |

#### `exchange_mode`

Every mode takes crossing liquidity first. There is **no post-only mode**.
The difference is what happens to the unfilled remainder:

- `make_and_take` (default): advertises the remainder at your price and keeps
  taking newly available liquidity.
- `take_only`: never advertises the remainder. Nothing can match against you.
- `dark`: advertises the remainder invisibly. Other orders can match it when
  their price crosses yours, but they cannot see your price.

The values `make` and `take` do not exist. They were a documentation error in
old copies of the spec, and the API rejects them with `validation_error`.

#### `current_score`

Optional array of exactly two integers, `[home, away]`. It is a
placement-time assertion: if the value does not match the live score the
exchange holds for the event, the order is rejected with HTTP 400, code
`validation_error`, `non_field_errors: ["event_scores_dont_match"]`.
Rejection is always explicit. There is no silent flagging.

The check is only meaningful for football-style scores. For other sports,
and while no score is known yet, the server assumes `[0, 0]` and rejects any
other value. Omit the field outside football.

Returns **201** with `order_id` and `status: "open"`. `price`, `stake` and
`profit_loss` are `null` until the order fills.

Lifecycle: `open → pending → done | failed`. Watch `["order", …]` and
`["bet", …]` on the WebSocket, or `GET /v2/orders/{order_id}/`.

**`done` means filled, not settled.** The final `profit_loss` lands after the
event finishes.

### Idempotency

Reusing a `request_uuid` returns `409 order_already_created` with the existing
`order_id` in `data`: so retrying after a timeout is safe and cannot
double-place. `GET /v2/orders/tracked/{uuid}/` looks an order up by
`request_uuid` for up to **6 hours** after placement; after that it is `404`.

### Reading and closing

| Endpoint | Purpose |
|---|---|
| `GET /v2/orders/` | List orders |
| `GET /v2/orders/{order_id}/` | Fetch one |
| `GET /v2/orders/updates/` | Changes since a timestamp: requires `updated_at_from` |
| `GET /v2/orders/tracked/{uuid}/` | Look up by `request_uuid` (6 h window) |
| `POST /v2/orders/{order_id}/close/` | Close one. `400 order_closed` if already closed |
| `POST /v2/orders/close_many/` | Close a specified set |
| `POST /v2/orders/close_all/` | Close everything open |
| `GET /v2/orders/position/` | Current position; requires filter params |

`close_all` is unfiltered and irreversible: confirm intent before calling it.

---

## Account

- `GET /v2/balance/`: balance and open stake. Also the **cheapest key
  check**; call it before opening the WebSocket.
- `GET /v2/xrates/`: exchange rates.

---

## Heartbeats (deadman's switch)

When a heartbeat expires, the exchange closes **every open order on the
account** that was created before the expiry instant: unfilled stake is
cancelled and unmatched advertised liquidity is withdrawn. Bets that already
matched are unaffected. The switch is account-wide, covering all sessions and
API keys, and expiry is evaluated server-side about once per second. Use one
around any unattended strategy.

| Endpoint | Purpose |
|---|---|
| `POST /v2/heartbeats/` | Create: body `{"timeout": <seconds>}` |
| `GET /v2/heartbeats/` | List active |
| `GET /v2/heartbeats/{heartbeat_id}/` | Fetch one |
| `POST /v2/heartbeats/{heartbeat_id}/refresh/` | Reset the timer: call well inside `timeout` |
| `DELETE /v2/heartbeats/{heartbeat_id}/` | Cancel |

`timeout` must be **10-300 seconds**; outside that range returns `400`.
Create returns `heartbeat_id` and `expiry_time`.

Two behaviours to build risk handling around:

- `DELETE` only disarms the timer. It closes nothing.
- An expired heartbeat cannot be refreshed; its close-out has already been
  triggered. Open a new one instead.

Refresh on an interval comfortably shorter than `timeout`. A refresh that
races the expiry will not save the orders.

---

## Reference data

`GET /v2/sports/{sport}/bet_types/{bet_type}/`: validate and describe a bet
type. Use this instead of parsing or constructing `bet_type` strings yourself.

---

## Error codes

| HTTP | `code` | Meaning |
|------|--------|---------|
| 400 | `validation_error` | `data.validation_errors` is `{field: [reason]}`; cross-field in `non_field_errors` |
| 400 | `order_closed` | Order exists but already closed/settled (distinct from `not_found`) |
| 401 | `auth_error` | Key missing, malformed, or rejected |
| 403 | `forbidden` | Valid key, action not permitted |
| 404 | `not_found` | Unknown resource, or not visible to this key |
| 409 | `order_already_created` | `request_uuid` reused; `data` has the existing `order_id` |
| 409 | `limit_reached` | Per-customer cap; `data.detail` describes it |
| 429 | `throttled` | `data.retry_after` seconds, plus a `Retry-After` header |
| 500 | `server_error` | `data` is `["An error has occurred, token:", "<token>"]`: quote the token to support |
| 503 | *(no envelope)* | Upstream unreachable; body is `{"detail": "Service unavailable"}` |

Branch on `code`, not on the HTTP status alone. For `validation_error`, branch
on the keys of `data.validation_errors`.

---

## Rate limits

Per **account**: all keys share one budget, sliding window.

| Applies to | Limit |
|---|---|
| All endpoints | 100 req/s burst, 1200 req/min sustained |
| `POST /v2/betslips/` | 10 req/s |
| `POST /v2/orders/` | 5 req/s |

Placement limits are dedicated budgets, not drawn from the general one. No
daily caps, no per-IP limit. Success responses carry **no** remaining-quota
header: track your own rate. Limits can be raised per account via support.

---

## Currencies and price ticks

Stakes are `[currency, amount]` tuples and responses are always **USDT**.

Prices lie on a fixed tick schedule:

| Decimal price | Tick |
|---|---|
| 1.01 - 2 | 0.01 |
| 2 - 3 | 0.02 |
| 3 - 4 | 0.05 |
| 4 - 6 | 0.10 |
| 6 - 10 | 0.20 |
| 10 - 20 | 0.50 |
| 20 - 30 | 1 |
| 30 - 50 | 2 |
| 50 - 100 | 5 |
| 100 - 1000 | 10 |

Band boundaries are exact in decimal price. Feed prices are always already
on-tick; a submitted price is snapped to the nearest tick that does not
tighten your limit (down for `for`, up for `against`), and the snapped price
is what the order runs with.
