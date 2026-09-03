# MagicMarkets: Runnable Examples

Python scripts for the most common MagicMarkets workflows, written against
the live API: REST at `https://magicmarkets.com/v2/`, stream at
`wss://magicmarkets.com/v2/stream`.

## Setup

```bash
pip install websockets requests
export MAGIC_API_KEY="your-api-key"     # Settings -> API on magicmarkets.com
```

Run them from this directory so `_common.py` is importable:

```bash
cd examples && python 01-discover.py
```

Tested on Python 3.10+.

## Scripts

| # | Script | What it does |
|---|--------|--------------|
| - | [`_common.py`](_common.py) | Shared helpers: envelope-aware frame parsing, sync, REST wrapper |
| 01 | [`01-discover.py`](01-discover.py) | List everything currently priced, via the stream's sync snapshot |
| 02 | [`02-price-book.py`](02-price-book.py) | Maintain a correct live price book from `offer` / `remove_offer` / `clear_events` |
| 03 | [`03-market-making.py`](03-market-making.py) | Full betslip → quote → order flow under heartbeat protection |
| 04 | [`04-bulk-close.py`](04-bulk-close.py) | Inspect and bulk-close open orders |
| 06 | [`06-multi-stream.py`](06-multi-stream.py) | Many events on one socket, with reconnect and re-registration |

`01-find-and-bet.py` and `05-arb-detector.py` are removal stubs: see the
docstring in each.

## Safety

**03 and 04 are dry-run by default.** They print what they would do and exit.
Pass `--live` to actually place or close, which commits real USDT. Read the
output of the dry run first.

`04 --all --live` calls `POST /v2/orders/close_all/`, which takes no filter
and is irreversible. Without `--all` the script enumerates and uses
`close_many/` so you can see exactly what will close.

## Things these examples exist to demonstrate

- **Every frame is a batch envelope** `{"ts": …, "data": [...]}`. Iterate
  `data[]` and dispatch on `entry[0]`. Never assume one message per frame.
- **Discovery is the stream**, not REST. There is no endpoint listing events.
- **`offer` is a full replacement**, not a delta; `remove_offer` means delete;
  `clear_events` means drop everything you hold.
- **Betslip creation returns no prices.** The quote arrives as a `pmm` message
  on the socket.
- **Registrations do not survive a reconnect.** Re-register every time.
- **A silent close looks like a clean EOF.** Always reconnect with backoff.
- **Always send `request_uuid`** when placing orders, so a retry cannot
  double-place.
