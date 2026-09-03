# MagicMarkets API: Claude Skill

A drop-in Claude skill for the **MagicMarkets** P2P sports markets exchange:
**zero fees, zero commission**, USDT-denominated, REST + WebSocket. Built so
an LLM can write a working trading bot against the API the first time you ask.

```
              ┌──────────────────────────────────────────────┐
              │  magicmarkets.com                            │
              │                                              │
  REST   ──▶  │  /v2/betslips/     quote a selection         │
  REST   ──▶  │  /v2/orders/       place / close trades      │
  REST   ──▶  │  /v2/heartbeats/   deadman's switch          │
  REST   ──▶  │  /v2/balance/      balance & open stake      │
  wss:// ──▶  │  /v2/stream        events, offers, fills     │
              └──────────────────────────────────────────────┘
```

## What it enables

- **Discover events**: the stream's initial sync is the discovery mechanism;
  there is no REST endpoint that lists events.
- **Stream live prices**: maintain a correct book from `offer`,
  `remove_offer` and `clear_events`.
- **Place orders**: back, lay or parlay, with idempotency via `request_uuid`.
- **Run protected bots**: heartbeats that auto-close exposure if the bot dies.
- **Handle failure properly**: in-band error codes, silent TCP closes,
  reconnect-and-re-register, rate limits.

## Source of truth

MagicMarkets publishes complete, current documentation. This skill is a
working guide over it, not a replacement: it tells Claude to fetch the real
docs for exact schemas:

| URL | What |
|-----|------|
| [`/llms.txt`](https://magicmarkets.com/llms.txt) | Index |
| [`/llms-full.txt`](https://magicmarkets.com/llms-full.txt) | Full reference (~109 KB Markdown) |
| [`/v2/openapi.yaml`](https://magicmarkets.com/v2/openapi.yaml) | OpenAPI 3.1: 18 paths, 29 schemas |

## Install

Clone into your Claude skills directory (the folder name must match the
`name:` in `SKILL.md`, which is `magicmarkets-magic-api`):

```bash
mkdir -p ~/.claude/skills
git clone https://github.com/Magic-Markets-Public/magic-api.git \
  ~/.claude/skills/magicmarkets-magic-api
```

Auto-loads in **Claude Code** (`~/.claude/skills/` user-wide, or
`.claude/skills/` per-project: no restart needed) and any host using the same
layout. For **Claude Desktop**, drop the folder into the directory shown by
Settings → Skills.

### Verify

```bash
ls ~/.claude/skills/magicmarkets-magic-api/SKILL.md

# smoke-test your key (Settings -> API on magicmarkets.com)
curl -H "X-Api-Key: $MAGIC_API_KEY" https://magicmarkets.com/v2/xrates/
```

Then ask Claude something like *"using the MagicMarkets API, what's tradeable
right now?"*

## Layout

```
SKILL.md                    concepts, flow, gotchas: what Claude reads first
references/streaming.md     WebSocket protocol in full
references/rest.md          REST endpoints, schemas, errors, limits
references/recipes.md       task-shaped patterns
examples/                   runnable Python (03 and 04 dry-run by default)
```

## Breaking changes in this revision

The previous version of this skill was written against infrastructure that has
since been retired, and would not work:

| Previously documented | Actual |
|---|---|
| `pro.magicmarkets.com` | `magicmarkets.com` (the `pro.` host 301s) |
| `wss://…/magic-cpricefeed/v2` | `wss://magicmarkets.com/v2/stream` (the old feed returns **502**) |
| `["watch_event", [comp_id, sport, event_id]]` | `["register_event", sport, event_id]` |
| `["offers_event", …]` messages | `["offer", …]` entries inside a `{"ts", "data"}` envelope |
| `GET /web/offerhist/…` | Does not exist (404) |

`references/pricefeed-reference.md` and `references/rest-reference.md` are now
redirect stubs, as are `examples/01-find-and-bet.py` and
`examples/05-arb-detector.py`.

## Licence

MIT: see [LICENSE](LICENSE).
