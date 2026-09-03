"""Shared helpers for the MagicMarkets examples.

REST  : https://magicmarkets.com/v2/
Stream: wss://magicmarkets.com/v2/stream?api_key=<key>

Requires:  pip install websockets requests
Env:       export MAGIC_API_KEY=...
"""

import json
import os
import sys
import time
import uuid

import requests
from websockets.sync.client import connect

API = os.environ.get("MAGIC_API_URL", "https://magicmarkets.com/v2")
WS = os.environ.get("MAGIC_WS_URL", "wss://magicmarkets.com/v2/stream")


def api_key() -> str:
    key = os.environ.get("MAGIC_API_KEY") or os.environ.get("MM_API_KEY")
    if not key:
        sys.exit("Set MAGIC_API_KEY (Settings -> API on magicmarkets.com)")
    return key


def headers() -> dict:
    return {"X-Api-Key": api_key(), "Content-Type": "application/json"}


def rest(method: str, path: str, **kw):
    """Call the REST API and unwrap the envelope, raising on error."""
    r = requests.request(method, f"{API}{path}", headers=headers(), timeout=30, **kw)
    try:
        body = r.json()
    except ValueError:
        r.raise_for_status()
        raise SystemExit(f"{method} {path}: non-JSON response ({r.status_code})")

    if body.get("status") != "ok":
        code = body.get("code", "unknown")
        detail = json.dumps(body.get("data"), default=str)[:300]
        raise SystemExit(f"{method} {path} failed [{r.status_code} {code}]: {detail}")
    return body.get("data")


def verify_key():
    """Check the key over REST before opening a socket.

    WebSocket auth fails at the HTTP handshake, which surfaces as an opaque
    client error. This turns that into a clear 401 auth_error.
    """
    return rest("GET", "/balance/")


def open_stream(lang: str = "en"):
    return connect(f"{WS}?api_key={api_key()}&lang={lang}", max_size=None)


def frames(ws):
    """Yield individual (tag, payload) messages.

    Every server frame is a batch envelope {"ts": ..., "data": [...]}.
    Batching boundaries are not meaningful, so callers should only ever see
    individual entries.
    """
    while True:
        try:
            raw = ws.recv()
        except Exception:
            return  # silent TCP close is a documented failure mode
        try:
            envelope = json.loads(raw)
        except ValueError:
            continue
        for entry in envelope.get("data", []):
            if not isinstance(entry, list) or not entry:
                continue
            yield entry[0], (entry[1] if len(entry) > 1 else None)


def sync_events(ws, timeout: float = 30.0) -> list:
    """Collect the initial event snapshot, up to and including ["sync", ...].

    This is the only event-discovery mechanism — there is no REST endpoint
    listing events. Returns only events that currently have live prices.
    """
    events, deadline = [], time.time() + timeout
    for tag, payload in frames(ws):
        if tag == "event":
            events.append(payload)
        elif tag == "sync":
            return events
        if time.time() > deadline:
            break
    return events


def register(ws, sport: str, event_id: str):
    ws.send(json.dumps(["register_event", sport, event_id]))


def unregister(ws, sport: str, event_id: str):
    ws.send(json.dumps(["unregister_event", sport, event_id]))


def label(event: dict) -> str:
    """Human-readable name for either event shape."""
    if event.get("event_name"):
        return event["event_name"]
    if event.get("event_type") == "multirunner":
        runners = ", ".join(t["name"] for t in event.get("teams", [])[:3])
        return f"[outright] {runners}…"
    return f"{event.get('home', '?')} v {event.get('away', '?')}"


def best(price_list) -> dict | None:
    """Best available price. price_list is sorted descending already."""
    return price_list[0]["effective"] if price_list else None


def new_request_uuid() -> str:
    """Idempotency key. Always send one when placing orders."""
    return str(uuid.uuid4())
