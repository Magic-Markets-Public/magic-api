# MagicMarkets REST API — Field Reference

Detailed schema for every REST endpoint. Read [`../SKILL.md`](../SKILL.md)
first for the high-level workflow and concepts. WebSocket details are in
[`pricefeed-reference.md`](pricefeed-reference.md).

All requests require the `X-Api-Key` header. Base URL is
`https://pro.magicmarkets.com/v2/`. All responses are wrapped in:

```json
{ "data": <object or array>, "status": "ok" }
```

Error responses use the same envelope with `status: "error"` and a
`code`. See §13.

---

## 1. `GET /v2/xrates/` — Exchange rates

Returns the current rates for every supported currency.

```json
{
  "status": "ok",
  "data": [
    { "ccy": "USD", "rate": 1.265 },
    { "ccy": "EUR", "rate": 1.1347 },
    { "ccy": "USDT", "rate": 1.1538 }
  ]
}
```

Useful for converting display currencies. Stakes elsewhere are always in
USDT, but `event_info`'s `ccy_rate` field references this rate.

---

## 2a. Bet type grammar

`bet_type` is a comma-separated string. First token is direction:
`for` (back — win if it happens) or `against` (lay — win if it doesn't).

**Handicaps always refer to the home team. Asian handicap lines are integers
= 4 × the actual decimal line** (keeps wire format integer-only across 0.25 steps):

| Wire | Real | Wire | Real |
|------|------|------|------|
| `0` | 0.0 | `2` | 0.5 |
| `7` | 1.75 | `8` | 2.0 |
| `-4` | −1.0 | `-21` | −5.25 |

### Match result
| Bet type | Meaning |
|----------|---------|
| `for,h` / `for,d` / `for,a` | Home / Draw / Away win |
| `for,sd` | Score draw (any non-0–0 draw) |
| `for,win_90,h` | Home wins in 90 min (excl. extra time) |
| `for,dnb,h` | Home win, void if draw (draw-no-bet) |
| `for,hnb,a` | Away win, void if home wins |
| `for,anb,h` | Home win, void if away wins |
| `for,ml,h` | Moneyline home (draw = void) |
| `for,dc,h,d` | Double chance: home or draw |
| `for,uswin,h` | US-style home win (draw splits half-stake) |
| `for,awdw,h` | Asian win/draw/win |
| `for,ko,h` | Home team to kick off |
| `for,qualify,h` | Home team to qualify |

### Goals / totals
| Bet type | Meaning |
|----------|---------|
| `for,over,2.5` / `for,under,2.5` | Over/under non-integer line |
| `for,overeq,3` / `for,undereq,3` | Over/under integer line, inclusive |
| `for,exact_total,3` | Exactly 3 goals |
| `for,exact_total,3,inf` | 3 or more goals |
| `for,gr,1,3` | Goal range 1–3 inclusive (`inf` for open-ended upper) |
| `for,teamgr,h,0,2` | Home team scores 0–2 |
| `for,odd` / `for,even` | Total goals odd / even |
| `for,odd,h` / `for,even,a` | Per-team odd / even |

### Asian handicaps (lines = 4 × actual)
| Bet type | Meaning |
|----------|---------|
| `for,ah,h,-4` | Asian handicap home −1.0 |
| `for,ahover,7` / `for,ahunder,7` | Asian over/under 1.75 goals |
| `for,tahover,h,2` / `for,tahunder,a,2` | Team Asian over/under 0.5 goals |
| `for,eh,h,1` | English handicap home +1 |

### Correct score / margins
| Bet type | Meaning |
|----------|---------|
| `for,cs,2,1` | Correct score 2–1 |
| `for,othercs,3,3` | Any score outside home ≤ 3 AND away ≤ 3 |
| `for,wm,h,2,2` | Home wins by exactly 2 |
| `for,wm,h,2,inf` | Home wins by 2 or more |
| `for,wmo,h,1,2.5` | Home wins by 1 + over 2.5 goals total |
| `for,awm,1` | Absolute margin = 1 (either side) |
| `for,wg,h,2` | Home wins and scores ≥ 2 |
| `for,quatro,h,o,2.5` | Home wins AND over 2.5 goals |
| `for,moou,h,o,2.5` | Match result + over/under combo |
| `for,mo_both_score,h,yes` | Home wins AND both teams score |

### Score / clean sheet
| Bet type | Meaning |
|----------|---------|
| `for,score,both,yes` / `for,score,both,no` | Both teams (don't) score |
| `for,score,either` / `for,score,neither` / `for,score,one` | Score patterns |
| `for,score,h,yes` / `for,score,h,no` | Home (does not) score |
| `for,clean,h` | Home clean sheet |
| `for,clean,both` / `for,clean,either` / `for,clean,neither` | Clean-sheet patterns |

### Multirunner (outrights, racing)
| Bet type | Meaning |
|----------|---------|
| `for,win,<team_id>` | Runner to win outright |
| `for,top,<n>,<team_id>` | Runner to finish in top N |

### Time-period tokens (prepend before market)
| Token | Meaning |
|-------|---------|
| `tp,<period>` | Generic period: `all`, `reg`, `1`–`9` |
| `thalf,<n>` | Half (n=1 or 2) |
| `tquarter,<n>` | Quarter (basket, NFL) |
| `tinnings,<n>` | Inning (baseball; `all` = whole game) |
| `tperiod,<n>` | Period (handball; sport-specific — for ice hockey use `tp,reg` / `tp,all` instead, see WS price-feed reference for the ih market table) |
| `tmap,<n>` | Map (esports, n=1–5) |
| `sub,<subsport>` | Optional subsport modifier (e.g. `sub,180` for darts 180s) |

Pattern: `for,<period_token>[,sub,<subsport>],<market>[,<args>...]`

Examples:
- `for,tp,all,ahunder,16` — total under 4.0 across all periods
- `for,thalf,1,ah,h,0` — Asian handicap home 0.0, first half
- `for,tquarter,2,wdw,h` — home to win Q2
- `for,tmap,1,ahover,42` — esports map 1 total kills over 10.5
- `for,tp,all,sub,180,ahover,8` — darts, over 2.0 × 180s

### Tennis
`for,tset,<period>,<void_rule>,<unit>[,<market>,<args>]`

| Segment | Values |
|---------|--------|
| `period` | `1`–`5` (specific set) or `all` (match) |
| `void_rule` | `vwhole`, `vset1`, `vgame1` — when the bookie voids on retirement |
| `unit` | `set` or `game`, optionally followed by a market and args |

Examples:
- `for,tset,all,vset1,p1` — player 1 to win the match (voids unless set 1 completes)
- `for,tset,1,vwhole,p1` — player 1 to win set 1
- `for,tset,all,vwhole,game,ahover,62` — total games over 15.5 (62/4 = 15.5)

---

## 2. `GET /v2/sports/{sport}/bet_types/{bet_type}/` — Bet type info

Validates a `bet_type` string and returns metadata plus a 20×20 win/loss grid.

| Param | Type | Notes |
|-------|------|-------|
| `sport` (path) | string | Sport code (`fb`, `tennis`, …) |
| `bet_type` (path) | string | Bet type, e.g. `for,h` or `against,cs,2,1` |
| `home_team` | string | Optional — used in display labels |
| `away_team` | string | Optional — used in display labels |

Response:
```json
{
  "status": "ok",
  "data": {
    "sport": "Football",
    "bet_type_description": "Home",
    "winloss_grid": [
      ["l","l","l","l","l","l","l","l","l","l","l","l","l","l","l","l","l","l","l","l"],
      ["w","l","l","l","l","l","l","l","l","l","l","l","l","l","l","l","l","l","l","l"],
      ["w","w","l","l","l","l","l","l","l","l","l","l","l","l","l","l","l","l","l","l"]
      // 20×20 grid: rows = home goals 0-19, columns = away goals 0-19
    ]
  }
}
```

Each grid cell is `"w"` (win), `"l"` (loss), `"p"` (push), or `"v"` (void).

---

## 3. `POST /v2/betslips/` — Create betslip

A betslip is a quote — current prices/stakes available on the exchange.

### Request — `BetslipCreateRequest`

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| `sport` | string | — | Required for `normal` / `lay`. Omit for `parlay`. |
| `event_id` | string | — | Required for `normal` / `lay`. Omit for `parlay`. |
| `bet_type` | string | — | Required for `normal` / `lay`. Omit for `parlay`. |
| `legs` | `BetslipLeg[]` | — | 2–10 legs for `parlay`. Mutually exclusive with `sport`/`event_id`/`bet_type`. |
| `betslip_type` | `"normal"` \| `"lay"` \| `"parlay"` | `"normal"` | See SKILL.md for the four side × type combinations. |
| `equivalent_bets` | bool | `true` | Include equivalent bets across the exchange when computing prices. |
| `user_data` | string \| null | null | Optional reference (max 512 chars) — echoed on the betslip and any orders placed against it. |
| `exclude_danger` | bool | `false` | When true, only liquidity sources that don't hold bets in danger status are used. |

### `BetslipLeg` (parlay only)
```json
{ "sport": "fb", "event_id": "2026-05-10,1234,5678", "bet_type": "for,h" }
```

### Response — `BetslipResponse`

| Field | Type | Notes |
|-------|------|-------|
| `betslip_id` | string | Use this when placing an order |
| `sport` | string | |
| `event_id` | string | |
| `bet_type` | string | |
| `bet_type_description` | string | Human-readable, e.g. `"Home, Match Result"` |
| `expiry_ts` | number | Unix timestamp when this quote expires |
| `is_open` | bool | False once closed — refresh or re-create before ordering |
| `close_reason` | string \| null | E.g. `"expired"` |
| `equivalent_bets` | bool | Echoes the request flag |
| `customer_username` | string | The authenticated customer |
| `customer_ccy` | string | Customer's display currency code |
| `betslip_type` | enum | `normal` / `lay` / `parlay` |
| `price_list` | `PriceLevel[]` | Prices sorted descending (best first) |
| `total` | `["USDT", n]` \| null | Sum of max stakes across all price levels |
| `legs` | `ParlayLeg[]` \| null | Present only for parlay betslips |
| `user_data` | string \| null | |

### `PriceLevel`

```json
{
  "effective": {
    "price": 1.85,
    "min":   ["USDT", 1.0],
    "max":   ["USDT", 250.0]
  }
}
```

| Field | Type | Notes |
|-------|------|-------|
| `effective.price` | number | Decimal price |
| `effective.min` | `["USDT", n]` \| null | Minimum stake at this price level |
| `effective.max` | `["USDT", n]` \| null | Maximum stake at this price level |

### `StakeTuple`

```json
["USDT", 115.38]
```
Always exactly two elements: `[currency_code, amount]`. Currency is always
`USDT` in responses.

---

## 4. `GET /v2/betslips/` — List open betslips

No query parameters. Returns the IDs of betslips currently open for the
authenticated customer:

```json
{ "status": "ok", "data": ["abc123…", "def456…", …] }
```

---

## 5. `GET /v2/betslips/{betslip_id}/` — Get a betslip

Returns a single `BetslipResponse` envelope.

---

## 6. `POST /v2/betslips/{betslip_id}/refresh/` — Refresh betslip

Resets the betslip's `expiry_ts` to approximately 45 seconds from the time
of the refresh call. Returns `{ "data": null, "status": "ok" }` — you must
`GET` the betslip to see the new `expiry_ts`. Useful when you want to keep the
same `betslip_id` valid while you decide whether to place an order.

---

## 7. `POST /v2/orders/` — Place order

### Request — `OrderCreateRequest`

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| `betslip_id` | string | — required | From a prior `POST /v2/betslips/` |
| `price` | number | — required | Decimal odds you want |
| `stake` | `[ccy, amount]` | — required | E.g. `["USDT", 25.0]` |
| `duration` | number | — required | How long the order stays open, **in seconds** (e.g. `60` = 60 seconds) |
| `exchange_mode` | `"make_and_take"` | `make_and_take` | Only `"make_and_take"` is accepted; `"make"` and `"take"` return a `validation_error`. |
| `keep_open_ir` | bool | `false` | Keep order alive after the event goes in-play |
| `user_data` | string \| null | null | Optional reference (max 512 chars) |
| `request_uuid` | string | — | **Idempotency key** — same UUID returns the same order |
| `accept_partial_fill` | bool | `true` | If false, full stake must fill or the order doesn't fill |
| `accept_better_price` | bool | `true` | Take a price better than `want_price` if available |
| `force_want_price` | bool | `false` | Insist on the exact price (overrides `accept_better_price`) |
| `min_taker_want_stake` | `[ccy, amount]` \| null | null | Minimum taker stake before the order will engage |
| `current_score` | string \| null | null | Required for in-running orders, e.g. `"1-0"` |
| `exclude_danger` | bool | `false` | Same meaning as on betslip |

### Response — `OrderResponse`

| Field | Type | Notes |
|-------|------|-------|
| `order_id` | integer | Stable handle for this order |
| `order_type` | `"normal"` \| `"lay"` \| `"parlay"` | |
| `bet_type` | string | |
| `bet_type_description` | string | |
| `sport` | string | Or `"parlay"` for accumulators |
| `placer` | string | Customer username |
| `want_price` | number | Decimal odds requested |
| `want_stake` | `["USDT", n]` \| null | Stake requested |
| `ccy_rate` | number | Exchange rate at order time |
| `placement_time` | string | ISO datetime |
| `expiry_time` | string | ISO datetime — when the order auto-cancels |
| `closed` | bool | True once finished |
| `close_reason` | string \| null | E.g. `"order_filled"`, `"expired"`, `"cancelled"` |
| `event_info` | `EventInfo` \| null | See §11 |
| `bets` | `BetResponse[]` | Individual fills — see §10 |
| `user_data` | string \| null | |
| `status` | string | `open`, `pending`, `done`, `reconciled`, `failed`, `full_void` |
| `keep_open_ir` | bool | |
| `exchange_mode` | string \| null | |
| `price` | number \| null | Achieved aggregate price (null while open) |
| `stake` | `["USDT", n]` \| null | Achieved aggregate stake |
| `profit_loss` | `["USDT", n]` \| null | P&L once the event settles |
| `bet_bar_values` | object \| null | Stake breakdown by fill state — see below |
| `legs` | `ParlayLeg[]` \| null | Parlay legs (see §12) |

### `bet_bar_values`

```json
{
  "success":    ["USDT", 1.995],
  "inprogress": ["USDT", 0.0],
  "danger":     ["USDT", 0.0],
  "unplaced":   ["USDT", 0.005]
}
```

| Key | Meaning |
|-----|---------|
| `success` | Amount matched and confirmed |
| `inprogress` | Amount currently in the matching process |
| `danger` | Amount matched but at risk (e.g. pending result) |
| `unplaced` | Amount not yet matched out of `want_stake` |

`unplaced > 0` while the order is still open and looking for liquidity.
`success + inprogress + danger + unplaced` ≈ `want_stake`.

---

## 8. `GET /v2/orders/` — List orders

Paginated. All array params support multi-value (repeat the key).

| Param | Type | Default | Notes |
|-------|------|---------|-------|
| `page` | int (≥1) | 1 | |
| `page_size` | int | 25 | |
| `status` | string[] | — | `open`, `pending`, `done`, `reconciled`, `failed`, `full_void` |
| `sport` | string[] | — | |
| `event_id` | string[] | — | |
| `order_type` | string[] | — | `normal`, `lay`, `parlay` |
| `date_from` | string | — | ISO datetime lower bound |
| `date_to` | string | — | ISO datetime upper bound |
| `search` | string | — | Free-text search |

Response: `{ "status": "ok", "data": [<OrderResponse>, …] }`.

To pass multiple values: `?status=open&status=pending`.

---

## 9. `GET /v2/orders/{order_id}/`, `GET /v2/orders/tracked/{uuid}/`

Both return a single `OrderResponse` envelope. The `tracked` variant looks
up by `request_uuid` (the idempotency key you set on order creation),
available up to **6 hours** after placement.

Useful pattern: store your own `request_uuid` and look up via `tracked` —
you don't need to remember the API-assigned `order_id`.

---

## 10. `BetResponse` — individual bet inside an order

```json
{
  "bet_id": 14412868927,
  "order_id": 1530309664,
  "order_ccy_rate": 1.355423,
  "status": { "code": "done" },
  "sport": "basket",
  "event_id": "2026-04-28,29119,40897",
  "bet_type": "for,ml,a",
  "ccy_rate": 1.355423,
  "want_price": 1.22,
  "got_price": 1.22,
  "want_stake": ["USDT", 1.0],
  "got_stake":  ["USDT", 1.0],
  "profit_loss": null,
  "reconciled": null,
  "exchange_role": "maker"
}
```

| Field | Type | Notes |
|-------|------|-------|
| `bet_id` | integer | |
| `order_id` | integer | |
| `status` | object \| string | `{"code": "done"}` or just `"pending"`. Common codes: `success`, `done`, `failed`, `pending`. May include `response_pmm` with effective price details. |
| `sport`, `event_id`, `bet_type` | string | |
| `want_price`, `got_price` | number | Requested vs achieved decimal price |
| `want_stake`, `got_stake` | `["USDT", n]` \| null | Requested vs achieved stake |
| `profit_loss` | `["USDT", n]` \| null | Settled P&L (null until reconciled) |
| `reconciled` | string \| null | Reconciliation status |
| `exchange_role` | `"maker"` \| `"taker"` \| null | Whether this bet posted or consumed liquidity |
| `legs` | `ParlayLeg[]` \| null | |

---

## 11. `EventInfo`

```json
{
  "event_type": "normal",
  "event_id": "2026-04-28,328,198",
  "event_name": "PSG vs. Bayern München",
  "home_id": 328,
  "home_team": "PSG",
  "away_id": 198,
  "away_team": "Bayern München",
  "competition_id": 7,
  "competition_name": "UEFA Champions League",
  "competition_country": "XE",
  "start_time": "2026-04-28T19:00:00+00:00",
  "date": "2026-04-28",
  "result": { "ht_home": 1, "ht_away": 0, "ft_home": null, "ft_away": null }
}
```

| Field | Type | Notes |
|-------|------|-------|
| `event_type` | `normal` \| `multirunner` \| `parlay` | |
| `event_id` | string \| null | Null on parlay aggregates |
| `event_name` | string | |
| `home_id`, `home_team`, `away_id`, `away_team` | int / string \| null | Normal events only |
| `competition_id`, `competition_name`, `competition_country` | int / string | `competition_country` is an ISO code (`XE` = England, `XZ` = international, etc.) |
| `start_time` | string | ISO datetime with timezone |
| `date` | string | `YYYY-MM-DD` |
| `result` | `EventResult` \| null | See below |
| `teams` | `[{team_id, name}, …]` \| null | Multirunner field list |
| `end_time` | string \| null | Multirunner end time |
| `leg_event_infos` | `EventInfo[]` \| null | Sub-event info for each parlay leg |

### `EventResult`

| Field | Type | Notes |
|-------|------|-------|
| `ht_home`, `ht_away` | int \| null | Half-time scores |
| `ft_home`, `ft_away` | int \| null | Full-time scores (null until final whistle) |
| `runner_results` | `RunnerResult[]` \| null | Multirunner finishing order |
| `non_runner_count` | int \| null | |

### `RunnerResult`

| Field | Type | Notes |
|-------|------|-------|
| `team_id` | int | |
| `position` | int | `1`=first, `2`=second, `0`=unknown, `-1`=void, `-2`=non-runner, `-3`=eliminated |

---

## 12. `ParlayLeg`

```json
{
  "id": 1,
  "sport": "fb",
  "event_id": "2026-05-10,1234,5678",
  "bet_type": "for,h",
  "bet_type_description": "Home, Match Result",
  "price": 1.85,
  "outcome": "won"
}
```

`outcome`: `"won"` / `"lost"` / `"void"` / `"push"` / `null` (until settled).

For a parlay `OrderResponse`, the `event_info` has `event_type: "parlay"` and
`event_id: null`. Full per-leg detail is in `event_info.leg_event_infos[]` —
each entry is a full `EventInfo` for that leg's underlying event.

---

## 12a. Lay order pricing — how fill prices work

**On MagicMarkets lay orders fill at the complement price, not the back price.**

When you place a lay order with `accept_better_price: true` (the default), the
engine matches you against existing back orders in the book. The fill price
reported is the implied back price expressed as the fair value of the complement:

```
P_fill = P_back_in_book / (P_back_in_book - 1)
```

Examples from live trading:
| Back price in book | Lay fill price | Formula check |
|--------------------|---------------|---------------|
| 2.38 | 1.73 | 2.38 / 1.38 = 1.725 ✓ |
| 2.80 | 1.55 | 2.80 / 1.80 = 1.556 ✓ |
| 4.10 | 1.32 | 4.10 / 3.10 = 1.323 ✓ |

**Payoff structure** for a lay at fill price `F` with stake `S`:
- If selection **loses**: profit = `(F - 1) × S`
- If selection **wins**: loss = `S`

This is equivalent to backing the opposite outcome at price `F`.

**`force_want_price: true` with lay orders**: the engine waits for a back in
the book at exactly your requested price. If backs are sitting at 2.38 and you
lay with `force_want_price=true` at 2.40, it will not fill and will expire.
Without `force_want_price`, the default `accept_better_price=true` means the
engine takes the best available backs (lower fill price = less liability for
the layer = "better").

**`against,X` (normal) vs `for,X` (lay)**: these are economically similar but
access **different liquidity pools**. `against,h` creates a normal back order
looking for layers of the "not home" selection — that pool is typically empty.
`for,h` with `betslip_type: "lay"` creates a lay order matched against existing
backs of the home selection — this pool has liquidity. Empirically, `for,X lay`
fills reliably while `against,X` (normal) consistently times out.

---

## 13. `GET /v2/orders/updates/` — Recently updated orders

Returns every order whose `updated_at` falls inside `[updated_at_from,
updated_at_to]`. Use this for periodic syncs instead of polling each
`order_id` individually.

| Param | Type | Notes |
|-------|------|-------|
| `updated_at_from` | string | **Required.** ISO datetime |
| `updated_at_to` | string | **Required.** ISO datetime |
| `placer` | string | Optional — filter by customer username |

**Two constraints, both empirically verified:**
- **Min age**: each timestamp must be **at least 60 seconds in the past**.
  Recent timestamps return:
  ```
  validation_errors: { updated_at_from: ["updated_at_from too recent"] }
  ```
- **Max span**: `updated_at_to - updated_at_from` must be **≤ 70 minutes**.
  Wider returns:
  ```
  validation_errors: { non_field_errors: ["The date range cannot exceed 70 minutes"] }
  ```

For longer syncs, page through successive 70-minute windows.

---

## 14. `GET /v2/orders/position/` — P&L position

Calculates the customer's overall P&L position across orders matching the
filter (same query parameters as `GET /v2/orders/`). Returns a payoff grid
(sport-dependent layout) showing how the position pays under each event
outcome.

```json
{
  "status": "ok",
  "data": {
    "payoff_grid": [],
    "totals": {},
    "placers": [],
    "unknown_bets_num": 0,
    "unknown_grid": []
  }
}
```

`unknown_bets_num` counts bets the position calculator couldn't resolve
into the grid — usually because the underlying market hasn't been quoted
recently. `unknown_grid` mirrors `payoff_grid`'s shape but is filled with
the unresolved component.

---

## 15. `POST /v2/orders/close_all/` — Cancel all open orders

Idempotent cancellation. Body is optional.

| Field | Type | Notes |
|-------|------|-------|
| `sport` | string | Optional — close only orders on this sport |
| `event_id` | string | Optional — close only orders on this event (requires `sport`) |

```bash
curl -X POST -H "X-Api-Key: $MM_API_KEY" -H "Content-Type: application/json" \
  -d '{}'                                       # close everything
  -d '{"sport":"fb"}'                           # close all soccer
  -d '{"sport":"fb","event_id":"2026-..."}'     # close one event
```

Response: `{ "data": [[order_id1, order_id2, …]], "status": "ok" }` — a
nested array of the closed order IDs. Returns `[[]]` if nothing was open.

---

## 16. `POST /v2/orders/close_many/` — Close specific orders

```json
{ "order_ids": [5001, 5002, 5003] }
```

Up to **500 IDs per request**. Synchronous: returns once all are closed.

---

## 17. Heartbeats — deadman's switch

Heartbeats auto-close all your open orders if you don't refresh in time.
Use this so a crashed bot doesn't leave orders hanging.

### `POST /v2/heartbeats/` — open a heartbeat

Request:
```json
{ "timeout": 60 }
```

| Field | Type | Range | Notes |
|-------|------|-------|-------|
| `timeout` | integer | 10–300 | Seconds before this heartbeat expires |

Response — `HeartbeatResponse`:
```json
{
  "data": {
    "heartbeat_id": "932622157ad244b9a28598b01793104d",
    "expiry_time": "2026-04-28T12:05:13.295905Z"
  },
  "status": "ok"
}
```

Empirically: requesting `timeout: 30` produced an `expiry_time` ~31 seconds
in the future. Use that delta as your refresh budget.

### `POST /v2/heartbeats/{heartbeat_id}/refresh/` — extend

Resets the expiry to fresh `timeout` seconds from now. Call this on a
cadence shorter than your timeout. Returns `{ "data": null, "status": "ok" }`
— you must `GET` the heartbeat to see the new `expiry_time`.

### `GET /v2/heartbeats/` — list active

Note the response wraps the array under a `heartbeats` key:
```json
{
  "data": {
    "heartbeats": [
      { "heartbeat_id": "...", "expiry_time": "..." }
    ]
  },
  "status": "ok"
}
```

### `GET /v2/heartbeats/{heartbeat_id}/` — get one

Returns a single `HeartbeatResponse`.

### `DELETE /v2/heartbeats/{heartbeat_id}/` — cancel

Returns `{ "data": null, "status": "ok" }`. Removes the heartbeat without
closing orders. Use this on graceful shutdown.

---

## 18. Status codes & error envelopes

### Order `status`
| Code | Meaning |
|------|---------|
| `open` | Live and trying to fill |
| `pending` | Submitted, waiting for confirmation |
| `done` | All bets filled or settled, P&L not yet reconciled |
| `reconciled` | Settled and P&L finalized — terminal happy state |
| `failed` | Could not be placed |
| `full_void` | Settled but voided (event cancelled, runner non-runner) |

`closed: true` is set once the order is finished. Read `close_reason` for
the why.

### Bet `status.code`
`success` / `done` / `pending` / `failed`. May include `response_pmm` with
effective price/min/max details.

### Error envelope (all errors)

```json
{ "status": "error", "code": "<error_code>", "data": <details> }
```

| HTTP | `code` | `data` shape |
|------|--------|--------------|
| 400 | `validation_error` | `{ "validation_errors": { <field>: [<msg>, …] } }` |
| 401 | `auth_error` | `{ "detail": "Authentication credentials were not provided." }` |
| 403 | `forbidden` | Varies by reason — see below |
| 404 | `not_found` | `null` |
| 409 | `order_already_created` | `{ "order_id": <int> }` — `request_uuid` was already used |
| 409 | `limit_reached` | `{ "detail": "<cap description>" }` — per-customer cap hit |
| 409 | `too_many_open_betslips` | `null` — per-customer cap on simultaneously-open betslips. Wait for existing betslips to expire (~45 s after creation) or stop creating new ones. Common during testing / probing. |
| 429 | `throttle_limit_exceeded` | `{ "message": "…", "retry_after": <seconds> }` + `Retry-After` header |
| 500 | `server_error` | `["An error has occurred, token:", "<token>"]` — quote token to support |
| 503 | *(no envelope)* | `{ "detail": "Service unavailable" }` — upstream unreachable, no JSON envelope |

**403 `forbidden` for order placement** (geo / permission restriction):
```json
{
  "can_place_bets": false,
  "reason": "no_api_place_permission",
  "country": "JP",
  "ip_address": "1.2.3.4",
  "login_country": "JP",
  "login_ip_address": "1.2.3.4"
}
```

**Cross-field validation errors** are keyed under `non_field_errors`:

| Value | Meaning |
|-------|---------|
| `event_not_found` | The `event_id` doesn't exist for the given `sport` |
| `invalid_bet_type` | The `bet_type` string isn't valid for that sport+event |
| `The date range cannot exceed 70 minutes` | `/v2/orders/updates/` window too wide |

Asking for a market the API doesn't support (e.g. `for,ml,*` on a soccer
match where moneyline isn't offered) can trigger a `code: "server_error"`
with a token-style `data` value — treat as "stop, this market/bet_type
isn't supported, don't retry".

### Error decision tree — what to do on each failure

This table tells you whether each error is retryable, and what (if anything)
needs to change before retrying. "Retry budget" is a sane default — adjust
to your latency tolerance.

| HTTP | `code` | Class | What to do | Retry? | Budget |
|------|--------|-------|-----------|--------|--------|
| 400 | `validation_error` | client bug | fix request body — read `data.validation_errors` | **no** | — |
| 401 | `auth_error` | config | check `X-Api-Key` header is set and the key is current | no | — |
| 403 | `forbidden` (`no_api_place_permission`) | geo / permission | non-recoverable from this IP / key scope | no | — |
| 403 | `forbidden` (other reasons) | permission | check key scope, customer status | no | — |
| 404 | `not_found` | client bug | the resource (order_id, betslip_id, heartbeat_id) doesn't exist | no | — |
| 409 | `order_already_created` | duplicate | **not an error** — the existing `order_id` is in `data` | no | — |
| 409 | `limit_reached` | quota | per-customer cap — back off, possibly delete an existing resource | yes (sparingly) | hours |
| 409 | `too_many_open_betslips` | quota | wait ~45 s for existing betslips to expire; stop probing | yes | 1 attempt after 60 s |
| 429 | `throttle_limit_exceeded` | rate limit | wait `data.retry_after` seconds (also in `Retry-After` header), then retry with the **same** `request_uuid` | **yes** | 5 attempts, exponential |
| 500 | `server_error` | server bug | log the token from `data` for support; stop unless you know it's transient | conditional | 1 retry, then escalate |
| 502/504 | *(no envelope)* | infra | upstream blip; retry with backoff | yes | 3 attempts |
| 503 | *(no envelope, body `{"detail":"..."}`)* | overload | server queue full or upstream down; retry with jittered backoff | yes | 3 attempts, 2–10s jitter |
| WS close 1006 | — | transport | reconnect, re-watch all events from scratch (no resume protocol) | yes | infinite with backoff |

**Critical idempotency rule**: when retrying `POST /v2/orders/` after a
network error, **always reuse the same `request_uuid`**. The server returns
either the original order (if it was accepted) or `409 order_already_created`
(safe — extract `data.order_id`). Generating a fresh UUID on each retry is the
classic way to accidentally place duplicate orders.

For order placement specifically, the **idempotent retry pattern** is:

```python
def place_with_retry(req_uuid, payload, max_retries=5):
    for attempt in range(max_retries):
        try:
            r = api("POST", "/orders/", {**payload, "request_uuid": req_uuid})
        except TransientError as e:
            time.sleep(2 ** attempt + random.uniform(0, 1))
            continue
        if r.get("status") == "ok":
            return r["data"]
        if r.get("code") == "order_already_created":
            # Server has the order; look it up
            return api("GET", f"/orders/tracked/{req_uuid}/")["data"]
        if r.get("code") == "throttle_limit_exceeded":
            time.sleep(r["data"].get("retry_after", 1))
            continue
        if r.get("code") == "validation_error":
            raise PermanentError(r)   # do not retry
        time.sleep(2 ** attempt)
    raise TimeoutError(f"order placement failed after {max_retries} retries")
```

### Order `close_reason` interpretation

| `close_reason` | Terminal? | Caused by | Implication |
|----------------|-----------|-----------|-------------|
| `order_filled` | yes | full or partial match completed | check `bet_bar_values` for matched amount |
| `expired` | yes | `duration` ran out before fill | normal for unmatched limit orders; place a new one if needed |
| `cancelled_by_user` | yes | `close_all` / `close_many` | you initiated this |
| `cancelled_by_heartbeat` | yes | heartbeat expired | bot was offline — investigate why heartbeat wasn't refreshed |
| `event_started` | yes | live event began before fill (and `keep_open_ir: false`) | place a new order with `keep_open_ir: true` if you want to trade in-play |
| `market_suspended` | yes | bookmaker suspended this market | wait until market resumes; price/depth changed |
| `event_void` | yes | event cancelled or voided | stake returned; no P&L |
| `betslip_expired` | yes | the betslip used was no longer fresh enough at fill time | refresh the betslip or create a new one |
| `partial_fill_only` | yes | `accept_partial_fill: true` and partial fill achieved before duration end | check `got_stake` vs `want_stake` |
| `failed` | yes | engine could not place (rare) | check `data.bets[].status` for per-bet detail |

If you see a `close_reason` not in this table, treat it as terminal and log
it — the enum is occasionally extended. Do not block on unknown values.

---

## 19. End-to-end example (Python)

```python
import os, time, uuid
import subprocess, json

BASE = "https://pro.magicmarkets.com/v2"
KEY  = os.environ["MM_API_KEY"]

def api(method, path, body=None):
    """curl-based helper (avoids Cloudflare 403 on urllib/requests)."""
    cmd = ["curl", "-s", "-X", method,
           "-H", f"X-Api-Key: {KEY}",
           "-H", "Content-Type: application/json"]
    if body:
        cmd += ["-d", json.dumps(body)]
    cmd.append(f"{BASE}{path}")
    return json.loads(subprocess.check_output(cmd))

# 1. Open a heartbeat — auto-closes all orders if we crash
hb = api("POST", "/heartbeats/", {"timeout": 60})["data"]
hb_id = hb["heartbeat_id"]
print(f"heartbeat {hb_id} expires {hb['expiry_time']}")

# 2. Validate the bet type
info = api("GET", "/sports/basket/bet_types/for,ml,a/")["data"]
print(f"bet_type: {info['bet_type_description']}")

# 3. Create betslip — price_list may be empty even when the market is liquid;
#    orders can fill against hidden depth. Use offerhist for a price reference.
betslip = api("POST", "/betslips/", {
    "sport": "basket",
    "event_id": "2026-04-28,29119,40897",
    "bet_type": "for,ml,a",
})["data"]
print(f"betslip {betslip['betslip_id']} — {len(betslip['price_list'])} visible price levels")

# If price_list is populated, use it; otherwise place at a reasonable reference price.
if betslip["price_list"]:
    target_price = betslip["price_list"][0]["effective"]["price"]
else:
    # Fall back to offerhist for a market reference
    hist = api("GET", "/offerhist/basket/2026-04-28,29119,40897/for,ml,a/")["data"]["prices"]
    latest = sorted((v[-1][1] for v in hist.values() if v and v[-1][1]), reverse=True)
    target_price = round(latest[0] * 0.99, 2) if latest else 1.80  # slight discount to fill

print(f"targeting price {target_price}")

# 4. Place order (idempotent via request_uuid)
req_uuid = str(uuid.uuid4())
order = api("POST", "/orders/", {
    "betslip_id": betslip["betslip_id"],
    "price": target_price,
    "stake": ["USDT", 5.0],
    "duration": 300,          # seconds
    "exchange_mode": "make_and_take",
    "request_uuid": req_uuid,
})["data"]
print(f"order {order['order_id']} placed, status={order['status']}")

# 5. Poll until closed, refreshing heartbeat each loop
while True:
    api("POST", f"/heartbeats/{hb_id}/refresh/")   # returns null — that's expected
    o = api("GET", f"/orders/tracked/{req_uuid}/")["data"]
    print(f"  status={o['status']} closed={o['closed']}")
    if o["closed"]:
        break
    time.sleep(5)

# 6. Cancel heartbeat on clean exit (DELETE returns null — that's expected)
api("DELETE", f"/heartbeats/{hb_id}/")
print(f"done: close_reason={o['close_reason']}, got={o.get('price')}@{o.get('stake')}")
```
