"""Local, consented fictional portfolios and append-only as-received valuations."""

from contextlib import contextmanager
from datetime import date, datetime
import hashlib
import json
import math
import os
from pathlib import Path
import secrets
import sqlite3

from .catalogue import approved
from .universe import ASSETS, REFERENCE

ROOT = Path(__file__).resolve().parents[2]
FEED = json.loads((ROOT / "data/demo/monitor_feed.json").read_text())
UPDATES = FEED["updates"]
COST = 0.001


if tuple(FEED["assets"]) != ASSETS:
    raise ValueError("Unexpected feed asset order")


def account_quote(update, size):
    if size == len(ASSETS):
        return update
    if size != len(REFERENCE):
        raise ValueError("Unknown account universe")
    if update.get("close"):
        return dict(update, close=update["close"][:size])
    return update


def quote_status(update):
    if update["day"] not in FEED["sessions"]:
        return "market closed"
    if (
        not update.get("close")
        or len(update["close"]) not in (len(ASSETS), len(REFERENCE))
        or not all(math.isfinite(v) and v > 0 for v in update["close"])
    ):
        return "missing close"
    if not update.get("fx") or not math.isfinite(update["fx"]) or update["fx"] <= 0:
        return "missing FX"
    for k in ["observed", "fx_observed"]:
        if (
            not update.get(k)
            or update[k][:10] != update["day"]
            or update[k] > update["asof"]
        ):
            return "stale " + ("FX" if k == "fx_observed" else "close")
    return "fresh"


def price(q):
    return [x * q["fx"] for x in q["close"]]


def dot(a, b):
    return sum(x * y for x, y in zip(a, b, strict=True))


def snapshot(s):
    q = s["quote"]
    values = [a * b for a, b in zip(s["units"], price(q), strict=True)]
    sleeve = s["cash"] + sum(values)
    return dict(
        sleeve=sleeve,
        wealth=sleeve + s["reserve"],
        weights=[x / sleeve if sleeve else 0 for x in values],
        reserve=s["reserve"],
        cash=s["cash"],
        last_reliable=q["asof"],
    )


@contextmanager
def db(path=None):
    path = Path(
        path
        or os.environ.get(
            "RISKMATCH_STORE", Path.home() / ".riskmatch-local" / "monitor.sqlite3"
        )
    )
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    conn = sqlite3.connect(path, timeout=10)
    os.chmod(path, 0o600)
    try:
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA secure_delete=ON")
        conn.execute(
            "CREATE TABLE IF NOT EXISTS accounts (id TEXT PRIMARY KEY,state TEXT NOT NULL)"
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS events (account TEXT REFERENCES accounts(id) ON DELETE CASCADE,seq INTEGER,kind TEXT,data TEXT,PRIMARY KEY(account,seq))"
        )
        conn.execute("BEGIN IMMEDIATE")
        yield conn
        conn.commit()
    finally:
        conn.close()


def identity(token):
    return hashlib.sha256(token.encode()).hexdigest()


def get(conn, token):
    row = conn.execute(
        "SELECT state FROM accounts WHERE id=?", (identity(token),)
    ).fetchone()
    if not row:
        raise ValueError("Unknown demo recovery key")
    return json.loads(row[0])


def write(conn, token, s, kind, record):
    s["seq"] += 1
    conn.execute(
        "UPDATE accounts SET state=? WHERE id=?",
        (json.dumps(s, allow_nan=False), identity(token)),
    )
    conn.execute(
        "INSERT INTO events VALUES(?,?,?,?)",
        (identity(token), s["seq"], kind, json.dumps(record, allow_nan=False)),
    )


def create(weights, cap, arm, consent, path=None, profile="unresolved", token=None):
    if not consent:
        raise ValueError("Explicit local storage consent required")
    if (
        len(weights) not in (len(ASSETS), len(REFERENCE))
        or not all(math.isfinite(x) and 0 <= x <= 0.600001 for x in weights)
        or sum(weights) > 0.900001
    ):
        raise ValueError("Invalid demo allocation")
    if cap not in [0.04, 0.08]:
        raise ValueError("Unknown mandate")
    if not approved(
        "demo/manual/v1",
        date.fromisoformat(UPDATES[0]["day"]),
        "CHF",
        "illustrative CHF 50000",
        "synthetic local demonstration",
    ):
        raise ValueError("Catalogue entry unavailable")
    token = token or secrets.token_urlsafe(32)
    opening = account_quote(UPDATES[0], len(weights))
    units = [35000 * w / p for w, p in zip(weights, price(opening), strict=True)]
    traded = 35000 * sum(weights)
    fee = traded * COST
    s = dict(
        cap=cap,
        arm=arm,
        weights=list(weights),
        units=units,
        cash=35000 - traded - fee,
        reserve=15000.0,
        bill=15000.0,
        due="2027-11-23",
        goal=65000.0,
        inflation=0.02,
        years=8,
        version=1,
        model="demo/manual/v1",
        consent="fictional-local-v1",
        selected=UPDATES[0]["asof"],
        profile=profile,
        feed=FEED["id"],
        assets=list(ASSETS[: len(weights)]),
        quote=opening,
        cursor=0,
        seq=0,
        index=(50000 - fee) / 50000,
        peak=1.0,
        settling=[],
        revision=None,
    )
    with db(path) as conn:
        if conn.execute(
            "SELECT 1 FROM accounts WHERE id=?", (identity(token),)
        ).fetchone():
            return token
        conn.execute("INSERT INTO accounts VALUES(?,?)", (identity(token), "{}"))
        write(
            conn,
            token,
            s,
            "selection",
            dict(
                time=s["selected"],
                mandate_version=1,
                **snapshot(s),
                units=units,
                target=weights,
                fee=fee,
                market_pnl=0,
                fx_pnl=0,
                flow=0,
                index=s["index"],
                drawdown=s["index"] - 1,
                status="fresh",
                feed_id="open",
            ),
        )
    return token


def history(token, path=None):
    with db(path) as conn:
        s = get(conn, token)
        rows = [
            dict(seq=n, kind=k, **json.loads(d))
            for n, k, d in conn.execute(
                "SELECT seq,kind,data FROM events WHERE account=? ORDER BY seq",
                (identity(token),),
            )
        ]
    return s, rows


def advance(token, expected, path=None):
    with db(path) as conn:
        s = get(conn, token)
        if expected != s["cursor"] or expected + 1 >= len(UPDATES):
            return False
        old = snapshot(s)
        prev = s["quote"]
        s["cursor"] += 1
        q = account_quote(UPDATES[s["cursor"]], len(s["units"]))
        status = quote_status(q)
        pnl = fxp = 0.0
        if status == "fresh":
            pnl = dot(
                s["units"],
                [
                    (b - a) * prev["fx"]
                    for a, b in zip(prev["close"], q["close"], strict=True)
                ],
            )
            fxp = dot(s["units"], q["close"]) * (q["fx"] - prev["fx"])
            s["quote"] = q
        deposit = q.get("deposit", 0)
        s["cash"] += deposit
        # Pending sale proceeds are already included in cash, but cannot fund an early bill.
        s["settling"] = [p for p in s["settling"] if p["available"] > q["day"]]
        paid = 0.0
        short = 0.0
        if s["bill"] and q["day"] >= s["due"]:
            available = (
                s["reserve"] + s["cash"] - sum(p["amount"] for p in s["settling"])
            )
            paid = min(s["bill"], max(0, available))
            used = min(s["reserve"], paid)
            s["reserve"] -= used
            s["cash"] -= paid - used
            s["bill"] -= paid
            short = s["bill"]
        flow = deposit - paid
        now = snapshot(s)
        if abs(now["wealth"] - old["wealth"] - flow - pnl - fxp) > 1e-6:
            raise ValueError("Valuation reconciliation failed")
        s["index"] *= ((now["wealth"] - flow) / old["wealth"]) if old["wealth"] else 1.0
        s["peak"] = max(s["peak"], s["index"])
        write(
            conn,
            token,
            s,
            "mark",
            dict(
                time=q["asof"],
                status=status,
                feed_id=q["id"],
                supersedes=q.get("supersedes"),
                **now,
                units=s["units"],
                flow=flow,
                fee=0.0,
                market_pnl=pnl,
                fx_pnl=fxp,
                shortfall=short,
                index=s["index"],
                drawdown=s["index"] / s["peak"] - 1,
                quote_age_hours=(
                    datetime.fromisoformat(q["asof"])
                    - datetime.fromisoformat(s["quote"]["observed"])
                ).total_seconds()
                / 3600,
            ),
        )
        return True


def erase(token, path=None):
    with db(path) as conn:
        get(conn, token)
        conn.execute("DELETE FROM accounts WHERE id=?", (identity(token),))
