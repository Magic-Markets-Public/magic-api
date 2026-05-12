---
name: magicmarkets-magic-api
description: >
  MagicMarkets API assistant — peer-to-peer sports markets exchange with
  zero fees and zero commission. Covers the REST API at
  pro.magicmarkets.com/v2/ for placing orders, listing/refreshing betslips,
  monitoring orders, calculating positions, managing heartbeats, and the
  WebSocket Price Feed at pro.magicmarkets.com/magic-cpricefeed/v2 for
  real-time prices. Use this skill when the user mentions MagicMarkets, the
  Magic API, pro.magicmarkets.com, P2P sports exchange, betslips, placing
  orders, back/lay/parlay, heartbeats, price feed, watch_event, USDT stakes,
  X-Api-Key auth, betslip_id, order_id, request_uuid, or building trading
  tools against MagicMarkets.
allowed-tools: Bash(curl:*), Bash(python3:*)
---

# MagicMarkets API

You are helping a developer build against the **MagicMarkets API** —
a peer-to-peer sports markets exchange with **zero fees and zero commission**.
Users back and lay against each other; all stakes are denominated in USDT.

| Detail | Value |
|--------|-------|
| **REST base URL** | `https://pro.magicmarkets.com/v2/` |
| **Price feed (WebSocket)** | `wss://pro.magicmarkets.com/magic-cpricefeed/v2?api_key=<api_key>` |
| **Auth (REST)** | `X-Api-Key: <token>` header |
| **Auth (WebSocket)** | `?api_key=<api_key>` query parameter |
| **Stake format** | `["USDT", <amount>]` tuples in every request and response |
| **Price format** | Decimal odds (e.g. `1.85`, `2.40`) |
| **Model** | P2P exchange — back, lay, or stack into parlays |

For deep schema reference, read [`references/rest-reference.md`](references/rest-reference.md).
For the WebSocket protocol, read [`references/pricefeed-reference.md`](references/pricefeed-reference.md).

The two are complementary:
- **Price feed (WebSocket)** is where you get real-time market depth — best
  prices, stakes, and updates every 2 seconds.
- **REST `/v2/betslips/` and `/v2/orders/`** is where you commit to a price
  and place orders.

You typically watch prices on the WebSocket, then create a betslip and place
an order via REST when you want to trade.

---

## Authentication

Every REST request needs the `X-Api-Key` header:

```bash
curl -H "X-Api-Key: $MM_API_KEY" https://pro.magicmarkets.com/v2/xrates/
```

WebSocket auth is via query parameter:
```
wss://pro.magicmarkets.com/magic-cpricefeed/v2?api_key=<api_key>
```

If the key starts with `m-`, an additional `&jwt=<firebase_jwt>` is
required. Plain API keys (the kind you mint from your account dashboard)
don't need a JWT.

Tell the developer to store the key in an environment variable
(`export MM_API_KEY=...`) rather than hard-coding it.

---

## Glossary

A short conceptual reference. The terms below appear throughout the skill;
read this first if you're new to MagicMarkets.

**Betslip** — A *quote*. You ask "what prices are available for this market?"
and the API returns a `betslip_id` plus a `price_list` of currently-available
price/stake levels. A betslip expires ~45 seconds after creation; refresh it
or create a fresh one.

**Order** — A *commitment*. You take a `betslip_id` and a `price`/`stake` and
ask the engine to fill it. An order can be `open` (still trying), `done`
(filled), `expired` (timed out), or `failed` (rejected).

**Bet** — A *fill*. Inside an order, each individual match against a counterparty
is a `bet`. A single order may produce multiple bets (e.g. partially filled at
several price levels). Bets have their own `bet_id` and `profit_loss` once
the underlying event settles.

**Lifecycle:**
```
betslip (quote) ──POST /v2/orders/──▶ order (commitment)
                                       │
                                       ├─ matches ─▶ bet (fill) ──▶ event settles ──▶ profit_loss
                                       └─ expires / cancelled / failed
```

**Back vs lay** — *Back* means you win if the selection happens; *lay* means
you win if it doesn't. The API uses `betslip_type: "normal"` for back and
`betslip_type: "lay"` for lay. Both work on the same `bet_type` string —
e.g. `for,h` with `normal` is "back home"; `for,h` with `lay` is "lay home".

**`for` vs `against`** — Independent of back/lay: `for,h` picks the selection
*home wins*, while `against,h` picks the selection *home does not win*. In
practice you usually want `for,X` with either `normal` or `lay` — the
`against,*` book has thinner liquidity (see Common mistakes).

**Parlay (acca)** — Stack 2–10 back legs into one bet that pays only if every
leg wins. `betslip_type: "parlay"` with a `legs[]` array.

**Heartbeat** — A deadman's switch. Open one with a `timeout` (10–300s) and
all your open orders auto-close if you don't refresh before it expires.

**Settlement** — A bet is "reconciled" when the event ends and `profit_loss`
becomes non-null. For pre-match orders this is usually within a few minutes
of full-time. In-running orders settle when the period or match ends.

---

## Lay pricing quick reference

**MagicMarkets lays fill at the complement price, not the back price** —
this is **not** the Betfair convention. If a back is sitting at 2.38 in the
book, your lay fills at 1.73, not 2.38.

| Back price in book | Lay-fill price | Liability per 1 USDT lay |
|--------------------|---------------|---------------------------|
| 1.25 | 5.00 | 4.00 |
| 1.50 | 3.00 | 2.00 |
| 2.00 | 2.00 | 1.00 |
| 2.50 | 1.67 | 0.67 |
| 3.00 | 1.50 | 0.50 |
| 4.00 | 1.33 | 0.33 |
| 5.00 | 1.25 | 0.25 |

**Formula**: `P_lay = P_back / (P_back − 1)`. Equivalently, this is the price
at which backing the *opposite* outcome would have the same payoff.

For the full payoff structure, force-price gotchas, and the `against,X` vs
`for,X lay` distinction, see the "Lay order pricing" section in
[`references/rest-reference.md`](references/rest-reference.md).

---

## Key concepts

### Sport codes

| Code | Sport | Typical markets |
|------|-------|------------------|
| `fb` | Football (soccer) 90 min | `wdw`, `ah`, `ahou`, `cs`, `gr`, `oe`, `wm`, `score,both`, `tahou,h/a`, `proposition,*` |
| `fb_ht` | Football 1st half | `wdw`, `ah`, `ahou`, `cs`, `score,both` |
| `fb_2h` | Football 2nd half | as `fb_ht` |
| `fb_et` | Football extra time | reduced market set |
| `fb_corn` / `fb_corn_ht` | Football corners | `ahou` (corner totals), `wdw` (most corners) |
| `fb_book` | Football yellow cards | `ahou` (booking points) |
| `fb_htft` | Football HT/FT result | `wdw`-style 9-way |
| `basket` | Basketball full | `ml`, `ah`, `ahou` |
| `basket_ht` / `basket_2h` / `basket_q1`–`q4` | Basketball segments | `ml`, `ah`, `ahou` |
| `tennis` | Tennis | `tennis_match,all`, `tennis_ah,set,all`, `tennis_ahou,game,all` |
| `tt` | Table tennis | similar to tennis |
| `ih` | Ice hockey | `time_win,tp,reg,wdw`, `time_win,tp,all,ml`, `time_ah,tp,*`, `time_ahou,tp,*` |
| `af` | American football | `ml`, `ah`, `ahou` per quarter/half |
| `rl` / `ru` | Rugby league / union | `wdw`, `ah`, `ahou` |
| `arf` | Australian rules football | `wdw`, `ah`, `ahou`; also outright `win` |
| `hand` | Handball | `wdw`, `ah`, `ahou` |
| `volley` | Volleyball | `ml`, `ah` (set-based) |
| `baseball` | Baseball | `ml`, `ah` (run line), `ahou` (totals) |
| `cricket` | Cricket | mostly outright `win`; some `ml` for limited-overs |
| `darts` | Darts | mostly outright `win`; `ml` for matches |
| `snooker` | Snooker | `ml`, `ahou` (frame totals) |
| `boxing` | Boxing | `ml` (no draw on most fights) |
| `mma` | Mixed martial arts | `ml`, `ahou` (round totals) |
| `golf` | Golf | outright `win` (multirunner) |
| `cycling` | Cycling | outright `win` |
| `moto` | Motorsport | outright `win` |
| `horse` | Horse racing | outright `win`, sometimes `top` |
| `dog` | Greyhound racing | outright `win` |
| `esports` | Esports | `ml`, map-based markets via `tmap,n` |
| `politics` | Political markets | outright `win` |
| `specials` | Specials / novelty | varies |

This list is **not a closed enum** — new sports are added over time. Don't
hard-fail on unknown codes. On parlay betslips/orders, `sport` is the literal
string `parlay`; per-leg sport sits inside each `legs[]` entry.

The "typical markets" column is empirically observed — individual events may
expose more or fewer markets. Read the WS `offers_event` columns or
`POST /v2/betslips/` response to see what's actually available for a given
event.

**Important**: the `/v2/sports/{sport}/bet_types/{bet_type}/` endpoint does **not**
validate sport codes — it accepts any string including made-up ones. Only
`POST /v2/betslips/` with a real sport+event_id combination will reject an
invalid sport. Always read `event_info.sport` from real orders or the price feed;
do not rely on this endpoint for sport validation.

### Where event IDs come from

There is **no REST endpoint that lists available events**. The designed
mechanism is the **price feed WebSocket**, which sends one
`["event", [sport, event_id], {…}]` message per live event during initial
sync, then `["synced"]`. Connect, collect those messages, then subscribe to
the markets you want.

**If the WebSocket is unavailable**, practical fallbacks:

1. **Betslip probing** — if you know team IDs (from past orders, an external
   sports data source, or a team ID table you maintain), probe with
   `POST /v2/betslips/`. Returns `event_not_found` for unknown events; success
   for known ones. Useful for confirming a specific match you expect to exist.

2. **Offer history** — `GET /web/offerhist/{sport}/{event_id}/{bet_type}/`
   returns non-empty if that event has been priced. Zero sources = event
   unknown or not yet active.

3. **Order history** — `GET /v2/orders/` returns `event_info` with team IDs
   for every past order. A natural way to build up a local team-ID cache over
   time.

Without the WebSocket, you cannot enumerate all live events. For production
bots, treat the WebSocket as a hard dependency.

### Event ID format
For two-team versus events: `YYYY-MM-DD,entity1_id,entity2_id` (date plus IDs).
The IDs are integers — football team IDs, basketball franchise IDs, tennis
player IDs, etc. IDs are stable across time; the same team always has the
same ID. Player IDs in individual sports (tennis, golf) can be 5–8 digits.

Examples:
- `2026-05-02,1059,200` — Hoffenheim (1059) vs Stuttgart (200)
- `2026-04-24,11177,87843` — Lajovic (11177) vs Rinderknech (87843, tennis)

Multirunner events (tournament winner, race) use a different shape —
always read `event_info.event_id` from the API rather than constructing.

### Bet type strings

A bet type is a **comma-separated string**. The first token is the direction:
`for` (back — you win if it happens) or `against` (lay — you win if it doesn't).

**Handicaps always refer to the home team. Asian handicap lines are integers
equal to 4 × the actual line** — this keeps the wire format integer-only across
0.25-step lines:

| Wire integer | Real line | Wire integer | Real line |
|---|---|---|---|
| `0` | 0.0 | `2` | 0.5 |
| `7` | 1.75 | `8` | 2.0 |
| `-4` | -1.0 | `-21` | -5.25 |

#### Common football markets

| Bet type | Meaning |
|----------|---------|
| `for,h` / `for,d` / `for,a` | Home / Draw / Away |
| `for,sd` | Score draw (any non-0–0 draw) |
| `for,dnb,h` | Home win, void if draw |
| `for,ml,h` | Moneyline home (draw = void) |
| `for,dc,h,d` | Double chance: home or draw |
| `for,over,2.5` / `for,under,2.5` | Over/under non-integer total |
| `for,overeq,3` / `for,undereq,3` | Over/under integer total, inclusive |
| `for,exact_total,3` | Exactly 3 goals |
| `for,gr,1,3` | Goal range 1–3 inclusive |
| `for,ah,h,-4` | Asian handicap home −1.0 (wire: −4) |
| `for,ahover,7` / `for,ahunder,7` | Asian totals over/under 1.75 goals |
| `for,cs,2,1` | Correct score 2–1 |
| `for,score,both,yes` / `for,score,both,no` | Both teams score / don't |
| `for,clean,h` | Home clean sheet |
| `for,qualify,h` | Home team to qualify |

#### Multirunner (outrights, racing)
| Bet type | Meaning |
|----------|---------|
| `for,win,<team_id>` | Runner to win outright |
| `for,top,<n>,<team_id>` | Runner to finish in top N |

#### Time-period tokens (prepend before market)
| Token | Meaning |
|-------|---------|
| `tp,all` / `tp,1` / `tp,2` | All / specific period |
| `thalf,1` / `thalf,2` | 1st / 2nd half |
| `tquarter,<n>` | Quarter (basket, NFL) |
| `tinnings,<n>` | Inning (baseball) |
| `tmap,<n>` | Map (esports, n=1–5) |

Examples: `for,thalf,1,ah,h,0` (1st half AH home 0.0) · `for,tquarter,2,wdw,h` (Q2 home win)

#### Tennis
`for,tset,<period>,<void_rule>,<unit>[,<market>,<args>]`
- period: `1`–`5` (a set) or `all` (whole match)
- void_rule: `vwhole` / `vset1` / `vgame1` (when voided if player retires)
- unit: `set` or `game` (optionally followed by a market)

Examples: `for,tset,all,vset1,p1` (player 1 wins match) · `for,tset,1,vwhole,p1` (wins set 1) · `for,tset,all,vwhole,game,ahover,62` (total games over 15.5)

**To get a bet_type's display description and win/loss grid**, use the
bet-type info endpoint:
```bash
curl -H "X-Api-Key: $MM_API_KEY" \
  "https://pro.magicmarkets.com/v2/sports/fb/bet_types/for,h/?home_team=Arsenal&away_team=Chelsea"
```
Returns the `bet_type_description` and a 20×20 `winloss_grid` mapping every
home/away score combination to `"w"` / `"l"` / `"p"` / `"v"` (push, void).
**Caveat**: this endpoint does not validate the sport code — it accepts any
string. Real sport+bet_type validation happens at `POST /v2/betslips/`.

See the "Bet type grammar" section in
[`references/rest-reference.md`](references/rest-reference.md) for the full
bet type grammar covering all markets, periods, and sports.

If you don't know the right bet_type for a market, copy it from an existing
order's `bet_type` field or from the price feed's `offers_event` messages —
don't construct unfamiliar formats by hand.

### From WebSocket prices to REST orders — translation table

You see prices on the WebSocket as `["offers_event", [comp_id, sport, event_id], { <column>: [[<line>, [outcomes...]]] }]`.
To **place an order** at one of those prices, you need to translate the
WebSocket column key + outcome_id into a REST `bet_type` string.

| WS column | WS outcome_id | `betslip_type: "normal"` (back) | `betslip_type: "lay"` (lay) | Notes |
|-----------|---------------|--------------------------------|----------------------------|-------|
| `wdw` | `h` / `d` / `a` | `for,h` / `for,d` / `for,a` | same with `betslip_type: "lay"` | 1X2 — handicap_line is `null` |
| `ah` | `h` / `a` | `for,ah,h,<line>` | same | line = wire integer (= 4× actual) |
| `ahou` | `h` (over) / `a` (under) | `for,ahover,<line>` / `for,ahunder,<line>` | same | line = wire integer |
| `tahou,h` | `h` (over) / `a` (under) | `for,tahover,h,<line>` / `for,tahunder,h,<line>` | same | home team total |
| `tahou,a` | `h` (over) / `a` (under) | `for,tahover,a,<line>` / `for,tahunder,a,<line>` | same | away team total |
| `cs` | `h` / `d` / `a` | `for,cs,<home>,<away>` | same | line = `[home, away]` |
| `gr` | `h` (in) / `a` (out) | `for,gr,<low>,<high>` / inverse for `a` | same | line = `[low, high]` |
| `oe` | `h` (odd) / `a` (even) | `for,odd` / `for,even` | same | line is `null` |
| `score,both` | `h` (yes) / `a` (no) | `for,score,both,yes` / `for,score,both,no` | same | line is `null` |
| `wm` (win margin) | `h` / `a` | `for,wm,h,<n>,<n>` | same | line = exact margin |
| `proposition,<Group>,<Name>` | varies | passed through — bet_type embedded in column key | varies | use as-is |
| `ml` (basket/MMA) | `h` / `a` | `for,ml,h` / `for,ml,a` | same | moneyline (no draw) |
| `time_win,tp,reg,wdw` (ih) | `h` / `d` / `a` | `for,tp,reg,wdw,h` etc. | same | regulation 3-way |
| `time_win,tp,all,ml` (ih) | `h` / `a` | `for,tp,all,ml,h` etc. | same | match moneyline |
| `time_ah,tp,reg` (ih) | `h` / `a` | `for,tp,reg,ah,h,<line>` | same | regulation AH |
| `time_ahou,tp,reg` (ih) | `h` / `a` | `for,tp,reg,ahover,<line>` / `…ahunder,…` | same | regulation totals |
| `tennis_match,all` | `p1` / `p2` | `for,tset,all,vset1,p1` / `…,p2` | same | match winner |
| `tennis_ah,set,all` | `p1` / `p2` | `for,tset,all,vset1,set,ah,p1,<line>` | same | match-set AH |
| `tennis_ahou,game,all` | `p1` (over) / `p2` (under) | `for,tset,all,vwhole,game,ahover,<line>` / `…ahunder,…` | same | total games |
| `win` (multirunner) | integer `team_id` | `for,win,<team_id>` | same | horse, dog, moto, outrights |

**To place an order against a price you saw on the WS**:
1. Look up the WS column + outcome_id in the table above → REST `bet_type` string.
2. `POST /v2/betslips/` with `{ sport, event_id, bet_type, betslip_type }`.
3. `POST /v2/orders/` with the `betslip_id` and the price you saw.

If you're unsure, query `GET /v2/sports/{sport}/bet_types/{bet_type}/` first
to confirm the bet_type validates and see its `bet_type_description`.

### Handicap line cheat sheet — wire ↔ decimal ↔ REST

Both the WebSocket wire format **and** the REST `bet_type` use the same
**4× integer encoding** for Asian handicap lines. There is no conversion to
do — the wire integer goes straight into the bet_type string:

| WS wire | Decimal line | REST bet_type fragment |
|---------|--------------|------------------------|
| `0`  | 0.0  (pick'em) | `for,ah,h,0` |
| `2`  | +0.5 | `for,ah,h,2` |
| `-2` | −0.5 | `for,ah,h,-2` |
| `7`  | +1.75 (quarter-ball) | `for,ah,h,7` |
| `-6` | −1.5 | `for,ah,h,-6` |
| `10` | 2.5 (totals over/under) | `for,ahover,10` |
| `-21`| −5.25 | `for,ah,h,-21` |

The 4× encoding lets quarter-ball lines (e.g. ±0.25, ±0.75, ±1.25) be
expressed as integers without floating point. Divide by 4 only when displaying
to a human — never when constructing a bet_type string.

### Stakes are tuples
Every stake — request and response — is `["USDT", <amount>]`:

```json
{ "stake": ["USDT", 25.0] }
```

---

## Two dimensions of an order

Every order has **two independent dimensions**:

**Dimension 1 — Selection side** (encoded in `bet_type`):
- `for,...` — pick the outcome to happen
- `against,...` — pick the outcome not to happen

**Dimension 2 — Order type** (separate field `betslip_type` / `order_type`):

| Value | Meaning | When to use |
|-------|---------|-------------|
| `normal` | **Back** the selection | Win if the selection happens |
| `lay` | **Lay** the selection | Win if the selection does *not* happen |
| `parlay` | **Accumulator** of 2–10 legs | Stack multiple back bets, all must win |

Economically `normal+for` ≈ `lay+against`, but they route through different
liquidity on the exchange.

A **back at 2.00 for 10 USDT** pays 20 USDT if the selection wins (profit +10).
A **lay at 2.00 for 10 USDT** wins 10 USDT if the selection loses; loses
10 USDT if it wins.

---

## Core workflow (REST trading)

```
1. Watch prices       WebSocket  → ["watch_event", [comp_id, sport, event_id]]
2. Create betslip     POST /v2/betslips/                  → betslip_id + price_list
3. (Optional refresh) POST /v2/betslips/{id}/refresh/     → extends expiry
4. Place order        POST /v2/orders/                    → order_id, status=open
5. Monitor            GET  /v2/orders/{id}/               (poll every few seconds)
                      GET  /v2/orders/updates/            (window across all orders)
                      GET  /v2/orders/tracked/{uuid}/     (if you have request_uuid)
6. Cancel if needed   POST /v2/orders/close_all/          (or close_many)
```

A **betslip** is a quote — it tells you what prices/stakes are currently
available for a given market. Betslips expire (check `expiry_ts` and
`is_open`). Use `POST /v2/betslips/{betslip_id}/refresh/` to extend.

An **order** is a commitment — once placed it tries to fill at your
`want_price` within `duration` minutes. `accept_partial_fill: true` (default)
takes whatever liquidity is available rather than insisting on the full stake.

---

## Heartbeats — automatic safety net

Heartbeats are a deadman's switch: open a heartbeat with a `timeout` (in
seconds, 10–300), and if you don't refresh it before it expires, **all your
open orders are auto-closed**. Use this to make sure your bot doesn't leave
orders hanging if it crashes or loses connectivity.

```bash
curl -X POST -H "X-Api-Key: $MM_API_KEY" -H "Content-Type: application/json" \
  -d '{"timeout": 60}' \
  https://pro.magicmarkets.com/v2/heartbeats/
# Then refresh every <timeout-buffer> seconds:
curl -X POST -H "X-Api-Key: $MM_API_KEY" \
  https://pro.magicmarkets.com/v2/heartbeats/{heartbeat_id}/refresh/
```

---

## Market-making patterns

Practical guidance for bots that post resting liquidity.

### Heartbeat duration

Pick the smallest timeout your bot can reliably refresh. Shorter = faster
auto-close on failure = less exposure.

| Timeout | Refresh budget | Best for |
|---------|----------------|----------|
| 10s | ~8s | Tight risk windows; you must refresh every loop iteration |
| 30s | ~24s | **Recommended default** — comfortable cadence + fast detection |
| 60s | ~48s | Slower-tempo bots; tolerates one slow tick |
| 300s (max) | ~240s | Long-poll architectures (riskier — bot can wedge silently) |

The `expiry_time` returned by `POST /v2/heartbeats/` is approximately
`now + timeout`. Always refresh **before** that time, not after. A safe budget
is 80% of `timeout`.

### Idempotent retry pattern

Always reuse the same `request_uuid` when retrying `POST /v2/orders/` after a
network error. The server returns either the original order or
`409 order_already_created` (with `data.order_id`). Generating a new UUID per
retry is the classic way to accidentally place duplicate orders.

```python
def place_with_retry(req_uuid, payload, max_retries=5):
    for attempt in range(max_retries):
        try:
            r = api("POST", "/v2/orders/", {**payload, "request_uuid": req_uuid})
        except TransientError:
            time.sleep(2 ** attempt + random.uniform(0, 1))
            continue
        if r.get("status") == "ok":
            return r["data"]
        if r.get("code") == "order_already_created":
            return api("GET", f"/v2/orders/tracked/{req_uuid}/")["data"]
        if r.get("code") == "throttle_limit_exceeded":
            time.sleep(r["data"].get("retry_after", 1))
            continue
        if r.get("code") == "validation_error":
            raise PermanentError(r)   # do not retry
        time.sleep(2 ** attempt)
    raise TimeoutError("retry budget exhausted")
```

### Monitor balance and open exposure in realtime

The WS `api` channel pushes `balance` and `order` updates without polling.
Subscribe once, react on every change:

```python
async for raw in ws:
    for msg in parse_frame(raw):
        if msg[0] != "api":
            continue
        for kind, payload in msg[1].get("data", []):
            if kind == "balance":
                balance       = payload["balance"][1]
                open_stake    = payload["open_stake"][1]
                smart_credit  = payload["smart_credit"][1]
                # gate new placements on balance / open_stake budget
            elif kind == "order":
                # react to fills, expirations, cancellations
                pass
```

This is **the** way to track open exposure without hammering REST — the
`api` channel pushes a fresh `balance` snapshot whenever your stake changes.

### Quoting against your own book

When you re-quote (e.g. price moves), close existing orders before placing
new ones to avoid stacking exposure:

```python
# Cancel the prior wave of resting orders for this event:
api("POST", "/v2/orders/close_all/", {"sport": sport, "event_id": event_id})
# Then place the new wave:
for px in new_prices:
    place_with_retry(str(uuid.uuid4()), {..., "price": px})
```

`close_all` is idempotent and cheap. Polling the open-orders list before
re-quoting is unnecessary if you funnel everything through `close_all` first.

---

## Endpoint reference

### REST

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/v2/xrates/` | Exchange rates (any → USDT) |
| `GET` | `/v2/sports/{sport}/bet_types/{bet_type}/` | Bet-type info + 20×20 win/loss grid |
| `GET` | `/v2/betslips/` | List the customer's open betslips |
| `POST` | `/v2/betslips/` | Create a betslip for a market |
| `GET` | `/v2/betslips/{betslip_id}/` | Get a single betslip |
| `POST` | `/v2/betslips/{betslip_id}/refresh/` | Extend betslip expiry |
| `GET` | `/v2/orders/` | List orders (paginated, filterable) |
| `POST` | `/v2/orders/` | Place an order on a betslip |
| `GET` | `/v2/orders/{order_id}/` | Get a single order |
| `GET` | `/v2/orders/tracked/{uuid}/` | Get order by `request_uuid` (6-hour window) |
| `GET` | `/v2/orders/updates/` | Orders updated within a time window |
| `GET` | `/v2/orders/position/` | P&L position for filtered orders |
| `POST` | `/v2/orders/close_all/` | Close all open orders (optionally filtered) |
| `POST` | `/v2/orders/close_many/` | Close up to 500 specific orders |
| `POST` | `/v2/heartbeats/` | Open a heartbeat (auto-close if not refreshed) |
| `GET` | `/v2/heartbeats/` | List active heartbeats |
| `GET` | `/v2/heartbeats/{heartbeat_id}/` | Get a single heartbeat |
| `POST` | `/v2/heartbeats/{heartbeat_id}/refresh/` | Extend a heartbeat |
| `DELETE` | `/v2/heartbeats/{heartbeat_id}/` | Cancel a heartbeat |
| `GET` | `/web/offerhist/{sport}/{event_id}/{bet_type}/` | External market price history time series |
| `GET` | `/v2/openapi.json` | Live OpenAPI spec (JSON) |
| `GET` | `/v2/openapi.yaml` | Live OpenAPI spec (YAML) |

### WebSocket

| URL | Purpose |
|-----|---------|
| `wss://pro.magicmarkets.com/magic-cpricefeed/v2?api_key=<api_key>` | Real-time prices + account updates (full protocol in [`references/pricefeed-reference.md`](references/pricefeed-reference.md)) |

---

## Worked examples

### Health-style probe — exchange rates
```bash
curl -s -H "X-Api-Key: $MM_API_KEY" \
  https://pro.magicmarkets.com/v2/xrates/
```

### Look up a bet type
```bash
curl -s -H "X-Api-Key: $MM_API_KEY" \
  "https://pro.magicmarkets.com/v2/sports/fb/bet_types/for,h/?home_team=Arsenal&away_team=Chelsea"
```

### Create a betslip (back the home team)
```bash
curl -s -X POST -H "X-Api-Key: $MM_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "sport": "fb",
    "event_id": "2026-04-28,328,198",
    "bet_type": "for,h",
    "betslip_type": "normal"
  }' \
  https://pro.magicmarkets.com/v2/betslips/
```

Response includes a `price_list` sorted best-price-first. Each entry has
`effective.price`, `effective.min`, and `effective.max` stakes.

### Refresh the betslip (extend expiry)
```bash
curl -s -X POST -H "X-Api-Key: $MM_API_KEY" \
  https://pro.magicmarkets.com/v2/betslips/{betslip_id}/refresh/
```

### Place an order on that betslip
```bash
curl -s -X POST -H "X-Api-Key: $MM_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "betslip_id": "<id-from-previous-call>",
    "price": 1.85,
    "stake": ["USDT", 25.0],
    "duration": 300,
    "exchange_mode": "make_and_take",
    "request_uuid": "'"$(uuidgen)"'"
  }' \
  https://pro.magicmarkets.com/v2/orders/
```

`request_uuid` is the idempotency key — sending the same UUID twice will not
create two orders. `duration` is in **seconds** (e.g. `300` = 5 minutes).

### Get an order by UUID (no need to remember order_id)
```bash
curl -s -H "X-Api-Key: $MM_API_KEY" \
  https://pro.magicmarkets.com/v2/orders/tracked/<request_uuid>/
```
Available up to 6 hours after order placement.

### Calculate P&L position
```bash
curl -s -H "X-Api-Key: $MM_API_KEY" \
  "https://pro.magicmarkets.com/v2/orders/position/?sport=fb&event_id=2026-04-28,328,198"
```
Returns a `payoff_grid` (20×20 matrix of home_goals × away_goals P&L values in USDT),
`totals` (combined net position per `bet_type`), and `cashout_info`.

### Check external market pricing (price reference)
```bash
curl -s -H "X-Api-Key: $MM_API_KEY" \
  "https://pro.magicmarkets.com/web/offerhist/fb/2026-05-02,1059,200/for,h/"
```
Returns price history from external reference sources (Betfair, Pinnacle, etc.):
```json
{ "data": { "prices": { "pin": [[1746000000.0, 2.37], …], "bf": [[…], …] } }, "status": "ok" }
```
Useful when `price_list` on a betslip is empty — use `offerhist` to get a market reference
price, then place a `make_and_take` order at or near that price.

### Close orders
```bash
# Close everything
curl -s -X POST -H "X-Api-Key: $MM_API_KEY" -H "Content-Type: application/json" \
  -d '{}' \
  https://pro.magicmarkets.com/v2/orders/close_all/

# Close all soccer orders
curl -s -X POST -H "X-Api-Key: $MM_API_KEY" -H "Content-Type: application/json" \
  -d '{"sport":"fb"}' \
  https://pro.magicmarkets.com/v2/orders/close_all/

# Close specific orders (max 500 per call)
curl -s -X POST -H "X-Api-Key: $MM_API_KEY" -H "Content-Type: application/json" \
  -d '{"order_ids": [5001, 5002, 5003]}' \
  https://pro.magicmarkets.com/v2/orders/close_many/
```

### Poll order updates across the account
```bash
# Both timestamps must be ≥60s in the past, and the span must be ≤70 minutes
FROM=$(python3 -c "import datetime; t=datetime.datetime.now(datetime.UTC)-datetime.timedelta(seconds=120); print(t.strftime('%Y-%m-%dT%H:%M:%SZ'))")
TO=$(python3   -c "import datetime; t=datetime.datetime.now(datetime.UTC)-datetime.timedelta(seconds=70);  print(t.strftime('%Y-%m-%dT%H:%M:%SZ'))")
curl -s -H "X-Api-Key: $MM_API_KEY" \
  "https://pro.magicmarkets.com/v2/orders/updates/?updated_at_from=$FROM&updated_at_to=$TO"
```

For longer syncs, page through successive 70-minute windows.

### Place a parlay (2–10 legs)
```bash
curl -s -X POST -H "X-Api-Key: $MM_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "betslip_type": "parlay",
    "legs": [
      { "sport": "fb",     "event_id": "2026-05-10,1234,5678",   "bet_type": "for,h" },
      { "sport": "basket", "event_id": "2026-05-10,29119,40897", "bet_type": "for,ml,h" }
    ]
  }' \
  https://pro.magicmarkets.com/v2/betslips/
```

For parlay betslips, supply `legs` instead of `sport`/`event_id`/`bet_type`.

### Basketball moneyline betslip + order
```bash
# Moneyline home — use "for,ml,h" not "for,h" for basket
curl -s -X POST -H "X-Api-Key: $MM_API_KEY" -H "Content-Type: application/json" \
  -d '{"sport": "basket", "event_id": "2026-04-30,40897,29119", "bet_type": "for,ml,h"}' \
  https://pro.magicmarkets.com/v2/betslips/

# Note: "for,h" also validates for basket — same semantics as "for,ml,h".
# The 20×20 winloss_grid uses "v" (void) for impossible scores like 0-0.
```

### Watch live prices (WebSocket)
```python
import asyncio, json, websockets

def parse(raw):
    d = json.loads(raw)
    return d if d and isinstance(d[0], list) else [d]

async def go():
    async with websockets.connect(
        f"wss://pro.magicmarkets.com/magic-cpricefeed/v2?api_key={KEY}",
        max_size=2**26
    ) as ws:
        events = {}

        # 1. Read initial sync (~3,400 events in ~1s, ended by ["synced"])
        synced = False
        async for raw in ws:
            for msg in parse(raw):
                if msg[0] == "synced":
                    synced = True
                    break
                if msg[0] == "event" and len(msg) >= 3 and msg[2]:
                    events[tuple(msg[1])] = msg[2]
            if synced:
                break

        # 2. Subscribe to one event
        sport, eid = "fb", "2026-05-05,1383,1384"
        comp_id = events[(sport, eid)]["competition_id"]
        await ws.send(json.dumps(["watch_event", [comp_id, sport, eid]]))

        # 3. Stream offers
        async for raw in ws:
            for msg in parse(raw):
                if msg[0] == "offers_event":
                    print("prices for", msg[1], msg[2])

asyncio.run(go())
```

See [`references/pricefeed-reference.md`](references/pricefeed-reference.md)
for the full message protocol.

---

## Common mistakes to flag

- **Forgetting `request_uuid`** when retrying a failed order POST → can create
  duplicate orders. Always pass an idempotency key for retries. Sending the
  same UUID twice returns the same order (confirmed: idempotent).
- **Stale betslip** — betslips expire ~45 seconds after creation. Refresh with
  `POST /v2/betslips/{id}/refresh/` which resets the clock to ~45 seconds from
  that call. The refresh response returns `null` data — call `GET` on the
  betslip to confirm the new `expiry_ts`.
- **Wrong stake format** — must be `["USDT", 25.0]`, not `25.0`.
- **`updated_at_from/to`** — both must be ≥60s in the past, and the span
  must be ≤70 minutes. The error messages are explicit when you violate
  either rule.
- **Hard-coding event_id format** for non-versus markets — multirunners use
  a different shape; always read it from the API or price feed.
- **Confusing `for` vs `lay`** — `against` flips the *selection*, `lay` flips
  the *order type*. They are different dimensions. Economically `against,h`
  (normal) and `for,h` (lay) both profit when home doesn't win — but they
  access **different liquidity pools**. In practice `for,h lay` fills reliably;
  `against,h` normal typically times out because no one explicitly lays "not
  home" in the normal book. **Use `betslip_type: "lay"` to offset back
  positions, not `against,X`.**
- **Empty `price_list`** does not mean the market is illiquid. The betslip
  `price_list` reflects depth visible to your account; the order engine can
  match against liquidity not exposed there. Empirically, orders have filled
  with price improvement at prices aligned with external market references even
  when `price_list` was empty. Use `GET /web/offerhist/{sport}/{event_id}/{bet_type}/`
  to see current market pricing from external sources as a reference point, then
  place a `make_and_take` order at a reasonable price.
- **Constructing unfamiliar bet types by hand** — query
  `/v2/sports/{sport}/bet_types/{bet_type}/` to validate, or copy from an
  existing order/`offers_event` message.
- **Forgetting to refresh heartbeats** — if you opened one with `timeout: 60`
  and don't refresh inside 60 seconds, all your open orders auto-close.
- **Using `accept_better_price: true` (the default) on `lay` orders** is
  surprising: for a layer "better" means *lower* price (less liability), so
  the engine can match you at a much lower price than you asked for, leaving
  you with almost no real exposure. If you're using a lay order to *offset*
  an existing back, set `accept_better_price: false` and/or
  `force_want_price: true` to lock in the price you actually want. Default
  behavior is fine for opening fresh lay positions where any improvement is
  desirable.
- **`exchange_mode`** — only `"make_and_take"` is accepted. The spec mentions
  `"make"` and `"take"` but both return a `validation_error` ("not a valid
  choice") when submitted. Always use `"make_and_take"` (or omit the field,
  as it is the default).
- **Lay fill prices are NOT the same as back prices** — lay orders on
  MagicMarkets fill at the complement price: `P_fill = P_back / (P_back - 1)`.
  A back at 2.38 → lay fills at 1.73. A back at 4.10 → lay fills at 1.32.
  This is **not** Betfair-convention where the lay price equals the back price.
  See the "Lay order pricing" section in
  [`references/rest-reference.md`](references/rest-reference.md) for the
  full formula and payoff structure.
- **`force_want_price: true` on lay orders** means the engine waits for a back
  at exactly your price. Since backs rarely sit at a precise decimal, this
  usually times out. Omit it (default) to get the complement-price fill.
- **Verify lay direction with a small probe** — before laying real size,
  fire a $2 lay and confirm the P&L sign matches your mental model after
  settlement.
- **Too many open betslips** — there is a per-customer cap on simultaneously-open
  betslips. Creating many betslips in a tight loop (e.g. probing bet_type
  formats during development) returns `409 too_many_open_betslips`. Betslips
  expire ~45 s after creation; pause and let them clear, or batch fewer
  probes per minute.

---

## Response envelopes

Every REST response — success or error — uses the same envelope:

**Success:**
```json
{ "data": <object or array>, "status": "ok" }
```

**Error:**
```json
{ "status": "error", "code": "<error_code>", "data": <details or null> }
```

Common error codes (HTTP → `code`):

| HTTP | `code` | Notes |
|------|--------|-------|
| 400 | `validation_error` | `data.validation_errors` is `{ field: [reason…] }`. Cross-field errors land in `non_field_errors`. |
| 401 | `auth_error` | Key missing, malformed, or rejected. |
| 403 | `forbidden` | Key valid but action not permitted. For order placement denials: `data` = `{ "can_place_bets": false, "reason": "no_api_place_permission", "country": "JP", "ip_address": "…" }` |
| 404 | `not_found` | `null` |
| 409 | `order_already_created` | `request_uuid` was already used. `data` contains the existing `order_id`. |
| 409 | `limit_reached` | Per-customer cap hit (e.g. max API tokens). `data.detail` describes the cap. |
| 429 | `throttle_limit_exceeded` | Rate limited. `data` = `{ "message": "…", "retry_after": <seconds> }`. A `Retry-After` header is also sent. |
| 500 | `server_error` | `data` = `["An error has occurred, token:", "<token>"]`. Quote the token to support. |
| 503 | *(no envelope)* | Upstream unreachable. Body is `{ "detail": "Service unavailable" }`. |

Common `non_field_errors` values: `event_not_found`, `invalid_bet_type`,
`The date range cannot exceed 70 minutes`.

For deeper schema detail, read
[`references/rest-reference.md`](references/rest-reference.md). For the
WebSocket protocol, read [`references/pricefeed-reference.md`](references/pricefeed-reference.md).
