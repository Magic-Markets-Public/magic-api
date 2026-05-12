# MagicMarkets Price Feed — WebSocket Reference

Real-time price streaming and account-update channel. Read [`../SKILL.md`](../SKILL.md)
first for context. REST endpoints are covered in [`rest-reference.md`](rest-reference.md).

| Detail | Value |
|--------|-------|
| **Endpoint** | `wss://pro.magicmarkets.com/magic-cpricefeed/v2` |
| **Auth** | `?api_key=<api_key>` query parameter |
| **Initial sync** | ~3,400 events delivered in ~1–12 seconds |
| **Update cadence** | Every 2 seconds (differential — only changed handicaps) |
| **Stake currency** | USDT throughout |

The price feed is a **separate service** from the REST API. REST endpoints
let you commit to a price (betslips, orders); the price feed tells you which
prices and stakes are currently available.

---

## 1. Connection

```
wss://pro.magicmarkets.com/magic-cpricefeed/v2?api_key=<api_key>
```

| Param | Required | Notes |
|-------|----------|-------|
| `api_key` | yes | Your API key (the same value used in the `X-Api-Key` REST header) |
| `jwt` | only if key starts with `m-` | Firebase JWT for magic-markets web session tokens |
| `lang` | no | Language for event/competition names: `en` (default), `ko`, `zh` |

Plain API keys (minted from your account dashboard) don't need a JWT.

> **Critical**: The parameter is `api_key`, not `token`. Using `?token=` connects
> successfully (HTTP 101) but the server drops the connection immediately with
> code 1006 before sending any data.

### Python connection example

```python
import asyncio, json, websockets

def parse_frame(raw):
    """Each frame is [[msg1], [msg2], ...] or [msg] — unwrap to list of msgs."""
    data = json.loads(raw)
    return data if data and isinstance(data[0], list) else [data]

URL = f"wss://pro.magicmarkets.com/magic-cpricefeed/v2?api_key={api_key}"
async with websockets.connect(URL, max_size=2**26) as ws:
    async for raw in ws:
        for msg in parse_frame(raw):
            mtype = msg[0]
            ...
```

`max_size=2**26` (64 MB) recommended — the initial sync delivers ~3,400 events
in batched frames that can be large.

### Frame format

The server sends **batched frames**: each WebSocket frame is a JSON array
containing one or more messages:

```json
[
  ["event", ["fb", "2026-05-05,1383,1384"], {...}],
  ["event", ["tennis", "2026-05-05,12345,67890"], {...}],
  ...
]
```

Always iterate over the outer array — never treat the frame as a single message.
Failing to call `parse_frame()` causes a `TypeError: unhashable type: 'list'`
when you try to use `msg[0]` as a string.

---

## 2. Message types

Every frame is a JSON array. The first element is the message type:

```json
["<type>", arg1, arg2, ...]
```

Types you'll see:

| Type | Direction | Purpose |
|------|-----------|---------|
| `event` | server | Event metadata (sent in initial sync and on metadata changes) |
| `synced` | server | End of initial sync |
| `offers_event` | server | Price snapshot or delta for a watched event |
| `offers_acca_event` | server | Same, but for parlay-eligible prices (back only — no lay) |
| `api` | server | Account-side updates (betslip / order / bet / xrate / balance) |
| `watch_event` | client | Subscribe to live prices for an event |
| `watch_acca_event` | client | Subscribe to parlay prices |
| `unwatch_event` / `unwatch_acca_event` | client | Unsubscribe (server replies `["ok"]`) |
| `ok` | server | Acknowledges a subscribe or unsubscribe command |
| `error` | server | Subscription rejected |
| `ping` / `pong` | both | Keepalive |

---

## 3. Initial sync

After connecting, the server pushes an `event` message for every currently
active event, then a `synced` marker. In parallel, `api` messages deliver
your account balance, current exchange rates, and server queue stats.

Typical connect sequence:
1. Multiple `api` messages arrive — balance snapshot, 20–30 xrate updates, info
2. Hundreds of batched `event` frames (3,300–3,500 events total)
3. `["synced"]` — all events delivered

```json
["event", ["fb", "2026-06-15,1001,2002"], {
  "event_type": "normal",
  "event_name": "Arsenal vs. Chelsea",
  "competition_id": 1,
  "competition_name": "England Premier League",
  "start_ts": "2026-06-15T15:00:00Z",
  "country": "XE",
  "home": "Arsenal",
  "away": "Chelsea",
  "available_for_accas": true
}]
…
["synced"]
```

Build an in-memory map keyed by `(sport, event_id)` from these so you can
look up `competition_id` later — you'll need it for `watch_event`.

### Event message shape

`["event", [sport, event_id], info_object_or_null]`

**`info_object` for a normal (two-sided) event:**

| Field | Always present | Notes |
|-------|---------------|-------|
| `event_type` | yes | `"normal"` |
| `event_name` | yes | Full match name, e.g. `"Arsenal vs. Chelsea"` |
| `home` | yes | Home team/player name |
| `away` | yes | Away team/player name |
| `home_display` | no | Override display name for home (omitted when same as `home`) |
| `away_display` | no | Override display name for away |
| `competition_id` | yes | Integer — required for `watch_event` |
| `competition_name` | yes | |
| `country` | yes | ISO 3166-1 alpha-2, or `"XX"` for international |
| `start_ts` | yes | ISO 8601 datetime, UTC |
| `available_for_accas` | yes | `true` if `watch_acca_event` is allowed |
| `ir_status` | no | Present for live in-running events (see §4) |

**`info_object` for a multirunner event** (horse, greyhound, moto, outright/futures):

```json
{
  "event_type": "multirunner",
  "event_name": "2:30 Ascot Handicap Chase",
  "competition_id": 50,
  "competition_name": "Royal Ascot",
  "start_ts": "2026-06-20T14:30:00Z",
  "end_ts": "2026-06-20T14:40:00Z",
  "country": "XE",
  "teams": [
    {"team_id": 101, "name": "Bold Venture", "metadata": null},
    {"team_id": 102, "name": "Green Light",  "metadata": null}
  ],
  "available_for_accas": false
}
```

`end_ts` is present on timed multirunner events (races). For outrights
(season-long futures) it is omitted or null.

**Runner metadata** (horse and greyhound events only):
```json
{"team_id": 7, "name": "Bold Venture", "metadata": {"jockey_name": "F. Dettori", "cloth_number": 5}}
```

For all other multirunner sports the `metadata` field is `null`.

**Event removed:** `["event", ["fb", "2026-06-15,1001,2002"], null]`

---

## 4. In-running status

Live events include an `ir_status` field on their `event` message. The shape
varies by sport. Read all `ir_status` defensively — new sports and new fields
appear without notice.

### Football (`fb`, `fb_ht`)
```json
"ir_status": { "time": ["2h", 45], "score": [2, 1], "rc": [0, 1] }
```
| Field | Notes |
|-------|-------|
| `time` | `[period, elapsed_minutes]` |
| `period` | `"1h"` first half, `"2h"` second half, `"ht"` half-time, `"et"` extra time, `"?"` unknown, `""` not started |
| `score` | `[home_goals, away_goals]` |
| `rc` | `[home_red_cards, away_red_cards]` |

### Tennis (`tennis`)
```json
"ir_status": {
  "has_service": 1,
  "who_retired": null,
  "game_score": ["40", "30"],
  "set_scores": [[6, 3], [5, 4]]
}
```
| Field | Notes |
|-------|-------|
| `has_service` | `1` = player 1 serving, `2` = player 2 serving |
| `who_retired` | `null`, `1`, or `2` — player who retired (match abandoned) |
| `game_score` | `[p1_points, p2_points]` as strings (`"0"`,`"15"`,`"30"`,`"40"`,`"AD"`) |
| `set_scores` | Array of `[p1_games, p2_games]` per completed and current set |

### Basketball (`basket`)
```json
"ir_status": { "time": ["q2", 480], "score": [54, 48] }
```
Period tokens: `"q1"`–`"q4"` (quarters), `"ht"` (half-time), `"ot"` (overtime).
`elapsed` is seconds elapsed in the current period.

### Ice hockey (`ih`)
```json
"ir_status": { "time": ["p2", 720], "score": [2, 1] }
```
Period tokens: `"p1"`–`"p3"` (periods), `"ot"`, `"so"` (shootout).

### Darts (`darts`)
```json
"ir_status": { "score": [3, 2], "leg": [180, 141] }
```
`score` = sets/legs won; `leg` = current leg score (points remaining or thrown — read defensively).

### Esports (`esports`)
```json
"ir_status": { "score": [1, 0] }
```
Maps / games won.

Other sports (cricket, moto, arf, mma, boxing) may include `ir_status` — parse it if present, skip if absent.

---

## 5. Subscribing to prices

```json
["watch_event", [<competition_id>, "<sport>", "<event_id>"]]
```

Server responds with one or more `offers_event` messages (the full snapshot)
followed by `["ok"]`.

The first element of the watch tuple is **`competition_id`** (an integer from
the event's `info_object`). The wrong value silently fails — the server closes
the connection without sending any error frame.

```json
["watch_acca_event",   [comp_id, sport, event_id]]   // parlay back prices only
["unwatch_event",      [comp_id, sport, event_id]]   // → ["ok"]
["unwatch_acca_event", [comp_id, sport, event_id]]   // → ["ok"]
```

Only subscribe to parlay prices for events where `available_for_accas: true`.
Sending `watch_acca_event` for an ineligible event returns an `error` message.

---

## 6. Price messages — `offers_event`

```json
["offers_event", [comp_id, "fb", "2026-06-15,1001,2002"], {
  "wdw": [
    [null, [
      ["h", [[3.25, ["USDT", 800.0]], [3.20, ["USDT", 400.0]]],
              [[3.35, ["USDT", 150.0]]],
              ["USDT", 20000.0]],
      ["d", [[5.90, ["USDT", 200.0]]],
              [[6.20, ["USDT", 120.0]]],
              ["USDT", 15000.0]],
      ["a", [[2.18, ["USDT", 600.0]]],
              [[2.26, ["USDT", 100.0]]],
              ["USDT", 10000.0]]
    ]]
  ],
  "ah": [
    [-6, [
      ["h", [[1.88, ["USDT", 500.0]]], [[2.14, ["USDT", 200.0]]], ["USDT", 5000.0]],
      ["a", [[2.01, ["USDT", 450.0]]], [[1.99, null]],            ["USDT", 4500.0]]
    ]]
  ]
}]
```

### Top-level structure

`["offers_event", event_key, columns]`

- **`event_key`**: `[competition_id, sport, event_id]`
- **`columns`**: object mapping market key → array of handicap entries

### Handicap entry

`[handicap_line, outcomes_or_null]`

| Field | Notes |
|-------|-------|
| `handicap_line` | Market-type dependent (see table below) |
| `outcomes` | Array of outcomes, **or `null` to delete this handicap** (differential update) |

**Handicap line encoding by market type:**

| Market type | `handicap_line` encoding | Example wire value | Actual meaning |
|-------------|-------------------------|--------------------|----------------|
| `wdw`, `score,both`, `oe`, `ml` | always `null` | `null` | no handicap |
| `ah`, `ahou`, `tahou,h`, `tahou,a`, tennis/basket/ih handicaps | **integer × 4** | `-6` | −1.5 goals/points |
| | | `9` | +2.25 (quarter-ball) |
| | | `10` | 2.5 over/under |
| | | `0` | pick'em |
| `cs` (correct score) | `[home_goals, away_goals]` integer tuple | `[2, 1]` | home 2 – away 1 |
| `gr` (goal range) | `[lower_bound, upper_bound]` integer tuple | `[2, 3]` | 2–3 goals |
| `wm` (win margin) | integer (margin value) | `3` | win by 3 |
| multirunner `win` | `null` | `null` | winner market |

> **Asian handicap lines use 4× encoding.** Divide the wire integer by 4 to get
> the actual line: `−6 / 4 = −1.5`, `9 / 4 = 2.25`, `10 / 4 = 2.5`. This
> encoding supports quarter-ball lines without floating point.

### Outcome

`[outcome_id, back_prices, lay_prices, volume]`

| Field | Type | Notes |
|-------|------|-------|
| `outcome_id` | string or integer | See outcome ID table below |
| `back_prices` | `[[price, stake], ...]` \| `null` | Sorted **descending** (best price first); multiple price levels |
| `lay_prices` | `[[price, stake], ...]` \| `null` | Sorted **descending**; `null` in `offers_acca_event` |
| `stake` within a price level | `["USDT", n]` \| `null` | `null` = price visible but not stakeable (no available liquidity at that level) |
| `volume` | `["USDT", n]` | Total settled volume on this outcome |

`null` stake is not the same as zero — the price level exists in the book but
carries no currently available stake. Filter these out before displaying to users.

### Outcome IDs by sport/market

| Sport / market type | Outcome IDs | Notes |
|--------------------|-------------|-------|
| Football 1X2 (`wdw`) | `"h"`, `"d"`, `"a"` | home, draw, away |
| Football AH/OU (`ah`, `ahou`) | `"h"`, `"a"` | home side, away side |
| Football correct score (`cs`) | `"h"`, `"d"`, `"a"` | which team is winning at that scoreline |
| Football goal range (`gr`) | `"h"`, `"a"` | over/under the range |
| Football both score (`score,both`) | `"h"`, `"a"` | yes (h) / no (a) |
| Tennis match winner | `"p1"`, `"p2"` | player 1 (home), player 2 (away) |
| Tennis AH / OU | `"p1"`, `"p2"` | |
| Basketball ML (`ml`) | `"h"`, `"a"` | |
| Basketball AH/OU | `"h"`, `"a"` | |
| Ice hockey (`time_win,*,wdw`) | `"h"`, `"d"`, `"a"` | 3-way (regulation period) |
| Ice hockey (`time_win,*,ml`) | `"h"`, `"a"` | 2-way moneyline |
| Ice hockey AH/OU | `"h"`, `"a"` | |
| MMA / boxing ML | `"h"`, `"a"` | |
| MMA OU (`ahou`) | `"h"`, `"a"` | over (h) / under (a) |
| Multirunner (horse, dog, moto, etc.) `win` | integer `team_id` | from event's `teams` array |

### Differential updates

Only **changed** handicap entries are sent. Unchanged columns are omitted
entirely from the update message. To delete a handicap entry entirely:

```json
[handicap_line, null]
```

Maintain the price book client-side: apply each `offers_event` as a delta on
top of the snapshot received after `watch_event`. On reconnect, always
re-send `watch_event` — there is no way to resume an existing subscription.

### Parlay prices (`offers_acca_event`)

Same schema as `offers_event` but `lay_prices` is always absent (the field is
simply not present in each outcome tuple, which becomes a 3-element array:
`[outcome_id, back_prices, volume]`).

---

## 7. Market column reference

Column keys are strings in the `columns` object. New columns are added without
notice — always read them defensively with `columns.get(key, [])`.

### Football (`fb`, `fb_ht`)

| Column key | Market | Handicap line | Outcomes |
|-----------|--------|---------------|---------|
| `wdw` | 1X2 win/draw/win | `null` | h, d, a |
| `ah` | Asian handicap | int÷4 | h, a |
| `ahou` | Asian totals (goals O/U) | int÷4 | h (over), a (under) |
| `tahou,h` | Home team goals O/U | int÷4 | h, a |
| `tahou,a` | Away team goals O/U | int÷4 | h, a |
| `cs` | Correct score | `[home, away]` | h, d, a |
| `gr` | Goal range | `[low, high]` | h (in range), a (out) |
| `oe` | Odd/even total goals | `null` | h (odd), a (even) |
| `wm` | Win margin | int | h, a |
| `score,both` | Both teams to score | `null` | h (yes), a (no) |
| `proposition,<Group>,<Name>` | Prop market | varies | varies |

Prop market column keys embed the display name directly in the key:
`proposition,Team Props,3-Way Handicap Home +1`. Parse the key as
`"proposition," + group + "," + name`.

### Tennis (`tennis`)

Tennis market keys follow the pattern `tennis_<market>,<unit>,<scope>`:

| Column key | Market | Handicap line | Outcomes |
|-----------|--------|---------------|---------|
| `tennis_match,all` | Match winner | `null` | p1, p2 |
| `tennis_ah,set,all` | Set handicap | int÷4 | p1, p2 |
| `tennis_ahou,game,all` | Total games O/U | int÷4 | p1 (over), p2 (under) |
| `tennis_ahou,game,set,<n>` | Games O/U in set *n* | int÷4 | p1, p2 |

`all` = full match; `set,<n>` = specific set.

### Basketball (`basket`)

| Column key | Market | Handicap line | Outcomes |
|-----------|--------|---------------|---------|
| `ml` | Moneyline | `null` | h, a |
| `ah` | Asian handicap | int÷4 | h, a |
| `ahou` | Totals O/U | int÷4 | h (over), a (under) |

### Ice hockey (`ih`)

Ice hockey market keys encode period and style: `time_<market>,tp,<period>[,<style>]`

| Column key | Market | Period | Outcomes |
|-----------|--------|--------|---------|
| `time_win,tp,reg,wdw` | 3-way (regulation) | reg | h, d, a |
| `time_win,tp,all,ml` | Moneyline (incl. OT/SO) | all | h, a |
| `time_ah,tp,all` | AH full match | all | h, a |
| `time_ah,tp,reg` | AH regulation | reg | h, a |
| `time_ah,tp,1p` | AH 1st period | 1p | h, a |
| `time_ahou,tp,all` | Totals full match | all | h, a |
| `time_ahou,tp,reg` | Totals regulation | reg | h, a |
| `time_ahou,tp,1p` | Totals 1st period | 1p | h, a |

Period tokens: `all` (including OT/SO), `reg` (regulation), `1p`/`2p`/`3p` (individual periods).

### MMA (`mma`) and Boxing (`boxing`)

| Column key | Market |
|-----------|--------|
| `ml` | Moneyline (h/a) |
| `ahou` | Round totals O/U |

### Multirunner sports

Multirunner events (horse racing, greyhound, motorsport outrights, political
outrights, darts outrights, cricket outrights, etc.) always use:

| Column key | Market | Handicap line | Outcomes |
|-----------|--------|---------------|---------|
| `win` | Winner | `null` | integer `team_id` per runner |

The `team_id` values come from the `teams` array on the event's `info_object`.

---

## 8. Account-update messages — `api`

The same WebSocket also delivers updates about your account state:

```json
["api", { "ts": 1586042815.269, "data": [
  ["balance", { "balance": ["USDT", 1500.0], "open_stake": ["USDT", 200.0], "smart_credit": ["USDT", 0.0] }],
  ["xrate",   { "ccy": "EUR", "rate": 1.1347 }],
  ["info",    { "queue_size": 0, "queue_size_max": 100, "registered_events": 0, "max_queue_size": 1000 }],
  ["betslip", { "betslip_id": "abc123", "sport": "fb", "price_list": [...], "total": ["USDT", 381.0], ... }],
  ["pmm",     { "betslip_id": "abc123", "price_list": [...], "total": ["USDT", 381.0], ... }],
  ["order",   { ...OrderResponse... }],
  ["bet",     { ...BetResponse... }]
]}]
```

| Inner type | When sent | Payload |
|------------|-----------|---------|
| `balance` | Once on connect | `{ "balance": ["USDT", n], "open_stake": ["USDT", n], "smart_credit": ["USDT", n] }` |
| `xrate` | On connect (all currencies) + on change | `{ "ccy": "EUR", "rate": 1.1347 }` — ~26 currencies sent on connect |
| `info` | On connect + periodically | `{ "queue_size": n, "queue_size_max": n, "registered_events": n, "max_queue_size": n }` |
| `betslip` | When your betslip changes | Same shape as REST `BetslipResponse` |
| `pmm` | When your resting liquidity changes | Per-market-maker view of the betslip — back fills only |
| `order` | When your order state changes | Same shape as REST `OrderResponse` |
| `bet` | When a bet settles | Same shape as REST `BetResponse` |
| `event` | When event metadata changes | Same shape as the standalone `event` message info_object |

`price_list` stakes are USDT, sorted descending (best price first). `total`
is the sum of max stakes across all levels.

This is the realtime alternative to polling `/v2/orders/updates/` — subscribe
once and receive a push for every state change.

---

## 9. Keepalive

```json
["ping", "any-payload"]
→ ["pong", "any-payload"]
```

Send a `ping` every ~30s if your transport doesn't already send keepalives.
The server echoes your payload back in a `pong`.

---

## 10. Common gotchas

- **Auth param is `api_key` not `token`** — `?token=<key>` connects (HTTP 101)
  but the server drops the connection with code 1006 before sending any data.
  This is the single most common failure mode.

- **Wrong `competition_id` in `watch_event`** — must be the integer from
  `info_object.competition_id`, not a hardcoded `1`. Subscribing with the wrong
  value silently fails (server closes the connection without an error frame).

- **Frame format** — frames are `[[msg1],[msg2],...]` not a single message.
  Always call `parse_frame()` before iterating. Without it you'll get a
  `TypeError: unhashable type: 'list'` when you try to use `msg[0]` as a key.

- **`stake: null` ≠ zero** — `null` stake means the price level exists but has
  no available liquidity right now (not tradeable). Filter these before display.

- **AH lines are 4× encoded** — divide the wire integer by 4 to get the decimal
  line. Wire `-6` = −1.5, wire `9` = +2.25, wire `10` = 2.5 total.

- **Differential updates** — only changed handicap entries are sent after the
  initial snapshot. If you reconnect, you must re-send `watch_event` to get a
  fresh snapshot; there is no resume mechanism.

- **`available_for_accas: false`** events reject `watch_acca_event`. Filter
  by this flag before subscribing.

- **Initial sync size** — ~3,400 events, several MB of JSON. Set
  `max_size=2**26` on your WebSocket client.

- **`api` messages arrive before `synced`** — balance, xrate, and info
  updates are interleaved with the initial event stream. Handle `api` inside
  your sync loop, not just after `synced`.

---

## 11. End-to-end example (Python)

```python
import asyncio, json, websockets

KEY = "..."  # your API key
URL = f"wss://pro.magicmarkets.com/magic-cpricefeed/v2?api_key={KEY}"

def parse_frame(raw):
    """Server sends batched frames: [[msg1],[msg2],...] or single [msg]."""
    data = json.loads(raw)
    return data if data and isinstance(data[0], list) else [data]

async def go():
    async with websockets.connect(URL, max_size=2**26) as ws:
        # ── 1. Initial sync ──────────────────────────────────────────────
        events = {}   # (sport, event_id) -> info_object
        balance = {}
        async for raw in ws:
            done = False
            for msg in parse_frame(raw):
                mtype = msg[0]
                if mtype == "event" and len(msg) >= 3:
                    key = tuple(msg[1])           # ("fb", "2026-06-15,1001,2002")
                    if msg[2] is not None:
                        events[key] = msg[2]
                    else:
                        events.pop(key, None)     # event removed
                elif mtype == "api":
                    for item in msg[1].get("data", []):
                        if item[0] == "balance":
                            balance.update(item[1])
                            print(f"balance: {item[1]}")
                        elif item[0] == "xrate":
                            pass   # build fx map if needed
                elif mtype == "synced":
                    done = True
            if done:
                break
        print(f"synced; {len(events)} events live")

        # ── 2. Pick a live football event and subscribe ──────────────────
        target = next(((s, e) for (s, e) in events if s == "fb"), None)
        if not target:
            return
        sport, eid = target
        info = events[target]
        comp_id = info["competition_id"]
        print(f"watching: {info['event_name']} (comp={comp_id})")
        await ws.send(json.dumps(["watch_event", [comp_id, sport, eid]]))

        # ── 3. Receive snapshot + stream updates ─────────────────────────
        book = {}   # market_key -> {handicap_line: {outcome_id: (backs, lays, vol)}}
        async for raw in ws:
            for msg in parse_frame(raw):
                mtype = msg[0]
                if mtype == "ok":
                    print("subscribed")

                elif mtype == "offers_event":
                    _, key, cols = msg
                    if not cols:
                        continue
                    for col_name, handicaps in cols.items():
                        mkt = book.setdefault(col_name, {})
                        for hline, outcomes in handicaps:
                            if outcomes is None:
                                mkt.pop(hline, None)   # deleted
                                continue
                            mkt[hline] = {}
                            for entry in outcomes:
                                oid, backs, lays, vol = entry
                                best_back = backs[0][0] if backs else None
                                best_lay  = lays[0][0]  if lays  else None
                                mkt[hline][oid] = (best_back, best_lay, vol)
                    # Print WDW snapshot
                    wdw = book.get("wdw", {}).get(None, {})
                    if wdw:
                        for oid, (b, l, v) in wdw.items():
                            print(f"  wdw {oid}: back={b} lay={l} vol={v}")

                elif mtype == "api":
                    ts = msg[1]["ts"]
                    for item in msg[1].get("data", []):
                        print(f"  account [{item[0]}] @ {ts}")

asyncio.run(go())
```

### Multirunner example — reading runner prices

```python
# After receiving offers_event for a horse race:
info = events[("horse", event_id)]
runner_names = {t["team_id"]: t["name"] for t in info["teams"]}

# In the offers_event handler:
win_market = (cols or {}).get("win", [])
for hline, outcomes in win_market:
    for entry in (outcomes or []):
        team_id, backs, lays, vol = entry
        name = runner_names.get(team_id, f"runner_{team_id}")
        best_back = backs[0][0] if backs else None
        print(f"  {name}: back={best_back} vol={vol}")
```
