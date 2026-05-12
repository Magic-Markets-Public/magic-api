# MagicMarkets API — Claude Skill

A drop-in Claude skill for the **MagicMarkets** P2P sports markets exchange
— **zero fees, zero commission**, USDT-denominated, REST + WebSocket. Built
so an LLM can write a working trading bot against the API the first time you
ask.

```
                ┌────────────────────────────────────┐
                │  pro.magicmarkets.com              │
                │                                    │
   REST   ──▶ │  /v2/betslips/   (quote prices)    │
   REST   ──▶ │  /v2/orders/     (place trades)    │
   REST   ──▶ │  /v2/heartbeats/ (deadman switch)  │
   wss:// ──▶ │  /magic-cpricefeed/v2  (live book) │
                └────────────────────────────────────┘
```

The skill teaches Claude the full surface area: bet-type grammar,
WebSocket↔REST translation, idempotent retries, lay-fill pricing,
market-making patterns, and the error decision tree.

## What the skill enables Claude to do

- **Place orders** — back or lay any market, with idempotency via `request_uuid`.
- **Stream live prices** — connect to the WebSocket, subscribe to events, and
  maintain a local price book from snapshot + delta updates.
- **Translate WS → REST** — turn an `offers_event` price into a
  `POST /v2/betslips/` + `POST /v2/orders/` call.
- **Run heartbeat-protected bots** — open a deadman's switch so unfinished
  orders auto-close if the bot crashes.
- **Build market-making strategies** — resting lays at a spread, auto-refresh
  every 80% of timeout, monitor `balance` and `open_stake` from the WS `api`
  channel.
- **Cancel & reconcile** — `close_all` filtered by sport / event, or `close_many`
  by ID.
- **Read the lay-pricing complement** — MagicMarkets fills lays at
  `P_back / (P_back − 1)`, not at the back price (not the Betfair convention).

## Install

Clone directly into your Claude skills directory (the destination folder name
must match the `name:` field inside `SKILL.md`, which is `magicmarkets-magic-api`):

```bash
mkdir -p ~/.claude/skills
git clone https://github.com/Magic-Markets-Public/magic-api.git \
  ~/.claude/skills/magicmarkets-magic-api
```

The skill auto-loads in **Claude Code** (from `~/.claude/skills/` user-wide,
or `.claude/skills/` per-project — no restart needed) and in any other
host that follows the same skill layout. For **Claude Desktop**, drop the
folder into the skills directory shown by Settings → Skills.

### Verify

```bash
# 1. Confirm the skill is in place:
ls ~/.claude/skills/magicmarkets-magic-api/SKILL.md

# 2. Smoke-test your API key (should return JSON of exchange rates):
curl -H "X-Api-Key: $MM_API_KEY" https://pro.magicmarkets.com/v2/xrates/
```

Then in a fresh Claude session, ask something like *"using the MagicMarkets
API, what are the current exchange rates?"* — Claude should pick up the skill
and reply with curl-grounded output.

## Trigger phrases

The skill activates when Claude detects you're working with MagicMarkets. Any
of these phrases will trigger it:

- "MagicMarkets API" / "Magic API" / "pro.magicmarkets.com"
- "place a back order" / "place a lay" / "create a betslip"
- "watch event prices" / "price feed" / "watch_event"
- "heartbeat" / "request_uuid" / "USDT stake"
- A `betslip_id`, `order_id`, or `bet_type` in conversation

You can also force-trigger it by saying "*using the MagicMarkets skill, …*".

## Repository layout

```
.
├── README.md                          ← this file
├── LICENSE                            ← MIT
├── SKILL.md                           ← Claude's main reference
└── references/
    ├── rest-reference.md              ← full REST schema, error tree, examples
    └── pricefeed-reference.md         ← full WebSocket protocol & message grammar
```

## API reference

The skill is grounded in the live API. For machine-readable specs, see:

- OpenAPI (JSON): https://pro.magicmarkets.com/v2/openapi.json
- OpenAPI (YAML): https://pro.magicmarkets.com/v2/openapi.yaml

If anything in the skill drifts from the live API, the live spec wins —
please open an issue against this repo.

## Getting an API key

Any MagicMarkets account can mint API keys self-service:

1. Sign up or log in at <https://magicmarkets.com>.
2. Open **Account Settings → API Keys**.
3. Create a key, copy it, and store it in an environment variable:

```bash
export MM_API_KEY="..."
```

Treat keys like passwords — don't commit them, don't log them, don't echo
them in scripts. The skill teaches Claude to read `$MM_API_KEY` from the
environment in every example.

## License

MIT — see [LICENSE](LICENSE).
