"""Capability-scoped SQLite ledger for fictional close-of-session portfolios.

Deposits and withdrawals take effect at the start of their session. Market marks
and simulated trades follow at the close. Execution prices are immutable; mark
corrections append a new edition and revalue the historical unit balances.
"""

import json
import math
import os
import re
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import UTC, date, datetime
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

_SCHEMA = """
CREATE TABLE state (
    singleton INTEGER PRIMARY KEY CHECK(singleton=1), revision INTEGER NOT NULL,
    mandate INTEGER, deleted INTEGER NOT NULL DEFAULT 0
);
INSERT INTO state VALUES (1,0,NULL,0);
CREATE TABLE mandates (
    version INTEGER PRIMARY KEY, payload TEXT NOT NULL, recorded_at TEXT NOT NULL
);
CREATE TABLE quotes (
    edition INTEGER PRIMARY KEY, day TEXT NOT NULL, asset TEXT NOT NULL,
    price REAL NOT NULL, fx REAL NOT NULL, price_at TEXT NOT NULL, fx_at TEXT NOT NULL,
    tradable INTEGER NOT NULL, recorded_at TEXT NOT NULL
);
CREATE INDEX quotes_day ON quotes(asset, day DESC, edition DESC);
CREATE TABLE flows (
    event_id TEXT PRIMARY KEY, day TEXT NOT NULL, amount REAL NOT NULL, recorded_at TEXT NOT NULL
);
CREATE TABLE proposals (
    id TEXT PRIMARY KEY, day TEXT NOT NULL, mandate INTEGER NOT NULL REFERENCES mandates(version),
    revision INTEGER NOT NULL, targets TEXT NOT NULL, parts TEXT NOT NULL, metadata TEXT NOT NULL,
    fee_rate REAL NOT NULL, settlement_day TEXT NOT NULL, snapshot TEXT NOT NULL,
    status TEXT NOT NULL, recorded_at TEXT NOT NULL
);
CREATE TABLE portfolios (
    version INTEGER PRIMARY KEY, proposal_id TEXT NOT NULL UNIQUE REFERENCES proposals(id),
    day TEXT NOT NULL, mandate INTEGER NOT NULL REFERENCES mandates(version),
    targets TEXT NOT NULL, parts TEXT NOT NULL, metadata TEXT NOT NULL, weights TEXT NOT NULL,
    recorded_at TEXT NOT NULL
);
CREATE TABLE trades (
    id INTEGER PRIMARY KEY, version INTEGER NOT NULL REFERENCES portfolios(version),
    day TEXT NOT NULL, asset TEXT NOT NULL, units INTEGER NOT NULL, price REAL NOT NULL,
    fx REAL NOT NULL, fee REAL NOT NULL, settlement_day TEXT NOT NULL
);
"""

_TABLES = ("mandates", "quotes", "flows", "proposals", "portfolios", "trades")
_JSON_FIELDS = {"payload", "targets", "parts", "metadata", "weights", "snapshot"}
_CENT_TOL = 1e-7


def _now():
    return datetime.now(UTC).isoformat()


def _day(value):
    try:
        return date.fromisoformat(str(value)).isoformat()
    except ValueError as exc:
        raise ValueError("A session date in YYYY-MM-DD format is required.") from exc


def _at_close(value, day):
    try:
        instant = datetime.fromisoformat(str(value))
    except ValueError as exc:
        raise ValueError("Invalid quote timestamp.") from exc
    if instant.tzinfo is None:
        raise ValueError("Price and FX timestamps need explicit UTC offsets.")
    instant = instant.astimezone(UTC)
    if instant.date().isoformat() > day:
        raise ValueError("A future observation cannot value this session.")
    return instant.isoformat()


def _number(value, label):
    if isinstance(value, bool) or value is None:
        raise ValueError(f"{label} must be finite.")
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{label} must be finite.") from exc
    if not math.isfinite(result):
        raise ValueError(f"{label} must be finite.")
    return result


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _decode(row):
    return {k: json.loads(v) if k in _JSON_FIELDS else v for k, v in dict(row).items()}


def _bump(conn):
    conn.execute("UPDATE state SET revision=revision+1 WHERE singleton=1")
    conn.execute("UPDATE proposals SET status='obsolete' WHERE status='draft'")


def _latest_day(conn):
    return conn.execute(
        "SELECT MAX(day) FROM (SELECT day FROM quotes UNION ALL SELECT day FROM flows UNION ALL SELECT day FROM portfolios)"
    ).fetchone()[0]


def _quotes(conn, day):
    rows = conn.execute(
        """SELECT * FROM (
             SELECT *,ROW_NUMBER() OVER(PARTITION BY asset ORDER BY day DESC,edition DESC) AS n
             FROM quotes WHERE day<=?
           ) WHERE n=1 ORDER BY asset""",
        (day,),
    )
    return {
        r["asset"]: {
            k: r[k] for k in ("day", "price", "fx", "price_at", "fx_at", "tradable")
        }
        for r in rows
    }


def _fresh(q, day):
    return q["price_at"][:10] == day and q["fx_at"][:10] == day


def _account(conn, day, marks=None):
    marks = _quotes(conn, day) if marks is None else marks
    cash = conn.execute(
        "SELECT COALESCE(SUM(amount),0) FROM flows WHERE day<=?", (day,)
    ).fetchone()[0]
    reserved = 0.0
    holdings = {}
    for r in conn.execute("SELECT * FROM trades WHERE day<=? ORDER BY id", (day,)):
        units = r["units"]
        holdings[r["asset"]] = holdings.get(r["asset"], 0) + units
        movement = -units * r["price"] * r["fx"] - r["fee"]
        cash += movement
        if units < 0 and r["settlement_day"] > day:
            reserved += movement
    holdings = {k: v for k, v in holdings.items() if v}
    prices = {k: q["price"] * q["fx"] for k, q in marks.items()}
    amounts = {k: v * prices[k] for k, v in holdings.items()}
    value = cash + sum(amounts.values())
    weights = (
        {k: v / value for k, v in {**amounts, "CHF": cash}.items()}
        if value > _CENT_TOL
        else {}
    )
    version = conn.execute(
        "SELECT * FROM portfolios WHERE day<=? ORDER BY version DESC LIMIT 1", (day,)
    ).fetchone()
    target = json.loads(version["weights"]) if version else {}
    drift = (
        {
            k: weights.get(k, 0) - target.get(k, 0)
            for k in sorted(weights.keys() | target.keys())
        }
        if target and weights
        else {}
    )
    state = conn.execute("SELECT mandate,revision FROM state").fetchone()
    return {
        "day": day,
        "holdings": holdings,
        "cash": cash,
        "settled_cash": cash - reserved,
        "unsettled_proceeds": reserved,
        "value": value,
        "weights": weights,
        "prices_chf": prices,
        "stale_symbols": sorted(k for k in holdings if not _fresh(marks[k], day)),
        "quotes": marks,
        "mandate_version": state["mandate"] or 0,
        "portfolio_version": version["version"] if version else 0,
        "revision": state["revision"],
        "drift_by_asset": drift,
        "drift_max": max(map(abs, drift.values()), default=0.0),
    }


def _orders(account, targets, fee_rate, settlement_day):
    if not account["mandate_version"]:
        raise ValueError("Confirm the current mandate before preparing a match.")
    day = account["day"]
    rows = []
    available = account["settled_cash"]
    for asset in sorted(account["holdings"].keys() | targets.keys()):
        quote = account["quotes"].get(asset)
        if quote is None or not _fresh(quote, day):
            raise ValueError(f"Missing or stale close or FX for {asset} on {day}.")
        units = targets.get(asset, 0) - account["holdings"].get(asset, 0)
        if not units:
            continue
        if not quote["tradable"]:
            raise ValueError(f"{asset} is unavailable for the simulated trade.")
        notional = units * quote["price"] * quote["fx"]
        fee = abs(notional) * fee_rate
        if units > 0 or settlement_day == day:
            available -= notional + fee
        rows.append((asset, units, quote["price"], quote["fx"], fee))
    if available < -_CENT_TOL:
        raise ValueError("Insufficient settled CHF for purchases and fees.")
    return rows


class Ledger:
    """One private file per random bearer token; the token is held by the caller."""

    def __init__(self, directory, token):
        if not isinstance(token, str) or not re.fullmatch(r"[a-f0-9]{64}", token):
            raise ValueError("Unknown demo dossier.")
        self.directory = Path(directory)
        digest = sha256(bytes.fromhex(token)).hexdigest()
        self._path = self.directory / (digest + ".sqlite3")
        self.token = token
        if not self._path.is_file():
            raise ValueError("Unknown demo dossier.")

    @classmethod
    def create(cls, directory):
        directory = Path(directory)
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        token = secrets.token_hex(32)
        path = directory / (sha256(bytes.fromhex(token)).hexdigest() + ".sqlite3")
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(fd)
        try:
            conn = sqlite3.connect(path)
            try:
                conn.executescript(_SCHEMA)
            finally:
                conn.close()
        except Exception:
            path.unlink(missing_ok=True)
            raise
        return cls(directory, token)

    @contextmanager
    def _connection(self, *, write=False):
        try:
            conn = sqlite3.connect(
                self._path.resolve().as_uri() + "?mode=rw",
                uri=True,
                timeout=15,
                isolation_level=None,
            )
        except sqlite3.OperationalError as exc:
            raise ValueError("Unknown demo dossier.") from exc
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA foreign_keys=ON")
            conn.execute("BEGIN IMMEDIATE" if write else "BEGIN")
            if conn.execute("SELECT deleted FROM state").fetchone()[0]:
                raise ValueError("This demo dossier was deleted.")
            yield conn
            conn.commit()
        except BaseException:
            conn.rollback()
            raise
        finally:
            conn.close()

    def save_mandate(self, payload, *, expected_version=None):
        if not isinstance(payload, dict) or not payload:
            raise ValueError("A confirmed mandate is required.")
        encoded = _json(payload)
        with self._connection(write=True) as c:
            old = c.execute(
                "SELECT m.* FROM mandates m JOIN state s ON s.mandate=m.version"
            ).fetchone()
            if (
                expected_version is not None
                and (old["version"] if old else 0) != expected_version
            ):
                raise ValueError(
                    "The profile changed in another session. Reopen it before saving."
                )
            if old and old["payload"] == encoded:
                return old["version"]
            version = c.execute(
                "INSERT INTO mandates(payload,recorded_at) VALUES (?,?)",
                (encoded, _now()),
            ).lastrowid
            c.execute("UPDATE state SET mandate=?", (version,))
            _bump(c)
            return version

    def current_mandate(self):
        with self._connection() as c:
            row = c.execute(
                "SELECT m.payload FROM mandates m JOIN state s ON s.mandate=m.version"
            ).fetchone()
            return json.loads(row[0]) if row else None

    def latest_mandate(self):
        with self._connection() as c:
            row = c.execute(
                "SELECT version,payload,state.mandate FROM mandates CROSS JOIN state ORDER BY version DESC LIMIT 1"
            ).fetchone()
            if row is None:
                return None
            return {
                "version": row["version"],
                "active": row["mandate"] == row["version"],
                "payload": json.loads(row["payload"]),
            }

    def latest_day(self):
        with self._connection() as c:
            return _latest_day(c)

    def invalidate_mandate(self):
        with self._connection(write=True) as c:
            if c.execute(
                "UPDATE state SET mandate=NULL WHERE mandate IS NOT NULL"
            ).rowcount:
                _bump(c)

    def mark(self, day, quotes):
        day = _day(day)
        with self._connection(write=True) as c:
            changed = False
            for asset, q in quotes.items():
                if not isinstance(asset, str) or not asset or asset == "CHF":
                    raise ValueError("Invalid security identifier.")
                price = _number(q.get("price"), "Local price")
                fx = _number(q.get("fx"), "FX")
                if min(price, fx) <= 0 or not math.isfinite(price * fx):
                    raise ValueError(
                        "A positive local price and CHF exchange rate are required."
                    )
                values = (
                    price,
                    fx,
                    _at_close(q.get("price_at"), day),
                    _at_close(q.get("fx_at"), day),
                    int(bool(q.get("tradable", True))),
                )
                old = c.execute(
                    "SELECT price,fx,price_at,fx_at,tradable FROM quotes WHERE asset=? AND day=? ORDER BY edition DESC LIMIT 1",
                    (asset, day),
                ).fetchone()
                if old is not None and tuple(old) == values:
                    continue
                c.execute(
                    "INSERT INTO quotes(day,asset,price,fx,price_at,fx_at,tradable,recorded_at) VALUES (?,?,?,?,?,?,?,?)",
                    (day, asset, *values, _now()),
                )
                changed = True
            if changed:
                _bump(c)
            return changed

    def flow(self, day, amount_chf, event_id=None):
        day = _day(day)
        amount = _number(amount_chf, "External flow")
        if amount == 0:
            raise ValueError("Enter a nonzero CHF amount.")
        event_id = event_id or uuid4().hex
        with self._connection(write=True) as c:
            old = c.execute(
                "SELECT day,amount FROM flows WHERE event_id=?", (event_id,)
            ).fetchone()
            if old:
                if tuple(old) != (day, amount):
                    raise ValueError(
                        "This flow identifier already belongs to a different flow."
                    )
                return event_id
            if (_latest_day(c) or day) > day:
                raise ValueError("This cash flow predates the current ledger session.")
            if amount < 0:
                account = _account(c, day)
                # Sale proceeds from this close cannot fund an opening withdrawal.
                same_day_settled = c.execute(
                    "SELECT COALESCE(SUM(-units*price*fx-fee),0) FROM trades "
                    "WHERE day=? AND (units>0 OR settlement_day<=?)",
                    (day, day),
                ).fetchone()[0]
                opening_cash = account["settled_cash"] - same_day_settled
                if min(opening_cash, account["settled_cash"]) + amount < -_CENT_TOL:
                    raise ValueError("The withdrawal exceeds available settled CHF.")
            c.execute(
                "INSERT INTO flows VALUES (?,?,?,?)", (event_id, day, amount, _now())
            )
            _bump(c)
        return event_id

    def account(self, day):
        with self._connection() as c:
            return _account(c, _day(day))

    def propose(
        self,
        day,
        targets,
        parts,
        *,
        fee_rate=0.001,
        metadata=None,
        settlement_day=None,
        expected_revision=None,
        expected_mandate=None,
        fund_on_confirmation=False,
    ):
        day = _day(day)
        settlement = _day(settlement_day or day)
        fee_rate = _number(fee_rate, "Fee rate")
        if settlement < day or not 0 <= fee_rate < 1:
            raise ValueError("Invalid settlement date or fee rate.")
        valid = {}
        for name, units in targets.items():
            n = _number(units, "Target units")
            if (
                not isinstance(name, str)
                or not name
                or name == "CHF"
                or n < 0
                or not n.is_integer()
            ):
                raise ValueError(
                    "Target positions must contain nonnegative whole units."
                )
            if n:
                valid[name] = int(n)
        shares = {k: _number(v, "Option share") for k, v in parts.items()}
        if any(v < 0 for v in shares.values()) or not math.isclose(
            sum(shares.values()), 1.0, abs_tol=1e-8
        ):
            raise ValueError("Option shares must sum to 100%.")
        with self._connection(write=True) as c:
            if (_latest_day(c) or day) > day:
                raise ValueError(
                    "The requested close predates the current ledger session."
                )
            acct = _account(c, day)
            if (
                expected_revision is not None and expected_revision != acct["revision"]
            ) or (
                expected_mandate is not None
                and expected_mandate != acct["mandate_version"]
            ):
                raise ValueError(
                    "The account or mandate changed during the calculation. Refresh the comparison."
                )
            mandate = c.execute(
                "SELECT payload FROM mandates WHERE version=?",
                (acct["mandate_version"],),
            ).fetchone()
            policy = json.loads(mandate[0]) if mandate else {}
            if reason := policy.get("blocked_reason"):
                raise ValueError(str(reason))
            metadata = dict(metadata or {})
            metadata.pop("pending_opening_chf", None)
            if fund_on_confirmation:
                if (
                    acct["portfolio_version"]
                    or acct["value"]
                    or c.execute("SELECT 1 FROM flows LIMIT 1").fetchone()
                ):
                    raise ValueError("The simulated account has already been funded.")
                opening = _number(
                    policy.get("capital_chf"), "Simulated opening balance"
                )
                if opening <= _CENT_TOL:
                    raise ValueError("A positive opening balance is required.")
                metadata["pending_opening_chf"] = opening
                acct.update(cash=opening, settled_cash=opening, value=opening)
            if acct["value"] <= _CENT_TOL:
                raise ValueError("Fund the simulated account before matching.")
            _orders(acct, valid, fee_rate, settlement)
            ident = uuid4().hex
            snapshot = {
                a: acct["quotes"][a]
                for a in sorted(valid.keys() | acct["holdings"].keys())
            }
            c.execute(
                "INSERT INTO proposals VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    ident,
                    day,
                    acct["mandate_version"],
                    acct["revision"],
                    _json(valid),
                    _json(shares),
                    _json(metadata or {}),
                    fee_rate,
                    settlement,
                    _json(snapshot),
                    "draft",
                    _now(),
                ),
            )
            return ident

    def proposal(self, proposal_id):
        with self._connection() as c:
            row = c.execute(
                "SELECT * FROM proposals WHERE id=?", (proposal_id,)
            ).fetchone()
            if not row:
                raise ValueError("Unknown proposal.")
            return _decode(row)

    def cancel(self, proposal_id):
        with self._connection(write=True) as c:
            if not c.execute(
                "UPDATE proposals SET status='cancelled' WHERE id=? AND status IN ('draft','cancelled')",
                (proposal_id,),
            ).rowcount:
                raise ValueError("Only a draft proposal can be cancelled.")

    def confirm(self, proposal_id, day):
        day = _day(day)
        with self._connection(write=True) as c:
            row = c.execute(
                "SELECT * FROM proposals WHERE id=?", (proposal_id,)
            ).fetchone()
            if not row:
                raise ValueError("Unknown proposal.")
            if row["status"] == "confirmed":
                return c.execute(
                    "SELECT version FROM portfolios WHERE proposal_id=?", (proposal_id,)
                ).fetchone()[0]
            acct = _account(c, day)
            if (
                row["day"] != day
                or row["status"] != "draft"
                or row["mandate"] != acct["mandate_version"]
                or row["revision"] != acct["revision"]
            ):
                raise ValueError(
                    "Proposal is no longer current. Rebuild it from the latest mandate, close and holdings."
                )
            opening = json.loads(row["metadata"]).get("pending_opening_chf")
            if opening is not None:
                if acct["value"] or acct["portfolio_version"]:
                    raise ValueError("The simulated opening balance changed.")
                c.execute(
                    "INSERT INTO flows VALUES (?,?,?,?)",
                    ("opening", day, opening, _now()),
                )
                acct = _account(c, day)
            targets = json.loads(row["targets"])
            orders = _orders(acct, targets, row["fee_rate"], row["settlement_day"])
            wealth = acct["value"] - sum(o[-1] for o in orders)
            if wealth <= _CENT_TOL:
                raise ValueError("Fees exhaust the simulated balance.")
            weights = {
                k: v * acct["prices_chf"][k] / wealth for k, v in targets.items()
            }
            weights["CHF"] = 1 - sum(weights.values())
            version = c.execute(
                "INSERT INTO portfolios(proposal_id,day,mandate,targets,parts,metadata,weights,recorded_at) VALUES (?,?,?,?,?,?,?,?)",
                (
                    proposal_id,
                    day,
                    row["mandate"],
                    row["targets"],
                    row["parts"],
                    row["metadata"],
                    _json(weights),
                    _now(),
                ),
            ).lastrowid
            c.executemany(
                "INSERT INTO trades(version,day,asset,units,price,fx,fee,settlement_day) VALUES (?,?,?,?,?,?,?,?)",
                [
                    (version, day, *o, row["settlement_day"] if o[1] < 0 else day)
                    for o in orders
                ],
            )
            c.execute(
                "UPDATE proposals SET status='confirmed' WHERE id=?", (proposal_id,)
            )
            _bump(c)
            return version

    def history(self):
        with self._connection() as c:
            days = [
                r[0]
                for r in c.execute(
                    "SELECT day FROM quotes UNION SELECT day FROM flows UNION SELECT day FROM portfolios ORDER BY day"
                )
            ]
            flows = dict(c.execute("SELECT day,SUM(amount) FROM flows GROUP BY day"))
            history = []
            previous = 0.0
            index = peak = 1.0
            for day in days:
                acct = _account(c, day)
                flow = flows.get(day, 0.0)
                opening = previous + flow
                gross = acct["value"] / opening if opening > _CENT_TOL else 1.0
                index *= gross
                peak = max(peak, index)
                history.append(
                    {
                        k: acct[k]
                        for k in (
                            "day",
                            "value",
                            "cash",
                            "settled_cash",
                            "portfolio_version",
                            "drift_max",
                            "stale_symbols",
                        )
                    }
                    | {
                        "flow_chf": flow,
                        "session_return": gross - 1,
                        "twr": index - 1,
                        "drawdown": index / peak - 1,
                    }
                )
                previous = acct["value"]
            return history

    def export(self):
        with self._connection() as c:
            data = {
                table: [
                    _decode(r)
                    for r in c.execute(f"SELECT * FROM {table} ORDER BY rowid")
                ]
                for table in _TABLES
            }
            data["active_mandate"] = c.execute("SELECT mandate FROM state").fetchone()[
                0
            ]
            return data

    def delete(self):
        with self._connection(write=True) as c:
            c.execute("UPDATE state SET deleted=1")
        self._path.unlink(missing_ok=True)


def replay_evidence(directory=None, *, release_paths=()):
    """Run the accounting, privacy and transaction controls on disposable fictional ledgers."""
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    def quote(day, price, fx=1.0):
        return {
            "price": price,
            "fx": fx,
            "price_at": day + "T20:00:00+00:00",
            "fx_at": day + "T19:00:00+00:00",
        }

    def rejected(action):
        try:
            action()
        except ValueError:
            return True
        return False

    with TemporaryDirectory(dir=directory) as tmp:
        ledger = Ledger.create(tmp)
        other = Ledger.create(tmp)
        marker = secrets.token_hex(24)
        first, second, third, fourth = (
            "2026-10-26",
            "2026-10-27",
            "2026-10-28",
            "2026-10-29",
        )
        ledger.save_mandate({"fictional_profile": marker, "ceiling": 0.12})
        ledger.flow(first, 1000, "initial")
        ledger.mark(first, {"A": quote(first, 50, 0.8), "B": quote(first, 25, 1)})
        initial = ledger.propose(
            first,
            {"A": 10, "B": 8},
            {"Equities": 0.6, "Balanced": 0.4},
            metadata={"mode": "manual blend; allow drift"},
        )
        cross_account = rejected(lambda: other.confirm(initial, first))
        ledger.confirm(initial, first)
        ledger.mark(second, {"A": quote(second, 55, 0.8), "B": quote(second, 25, 1)})
        ledger.flow(second, -100, "withdrawal")
        ledger.mark(third, {"A": quote(third, 55, 0.8), "B": quote(third, 25, 1)})
        ledger.flow(third, 200, "deposit")
        old_history = ledger.history()
        # A corrected close supersedes the earlier mark; no fill price is rewritten.
        ledger.mark(second, {"A": quote(second, 60, 0.8)})
        history = ledger.history()
        expected_values = [999.4, 979.4, 1139.4]
        expected_twr = 999.4 / 1000 * 979.4 / 899.4 * 1139.4 / 1179.4 - 1
        if (
            not all(
                abs(r["value"] - v) < 1e-8 for r, v in zip(history, expected_values)
            )
            or abs(history[-1]["twr"] - expected_twr) > 1e-10
        ):
            raise AssertionError("Hand-ledger reconciliation failed.")
        initial_fee = sum(t["fee"] for t in ledger.export()["trades"])
        draft = ledger.propose(third, {"B": 30}, {"Hedge": 1})
        ledger.invalidate_mandate()
        obsolete = rejected(lambda: ledger.confirm(draft, third))
        if Ledger(tmp, ledger.token).latest_mandate()["active"]:
            raise AssertionError("An edited mandate remained active after reopening.")
        ledger.save_mandate({"fictional_profile": marker, "ceiling": 0.1})
        delayed = rejected(
            lambda: ledger.propose(
                third, {"B": 40}, {"Hedge": 1}, settlement_day=fourth
            )
        )
        bad_sale = rejected(lambda: ledger.propose(third, {"A": -1}, {"Hedge": 1}))
        ledger.mark(fourth, {"A": quote(third, 55, 0.8), "B": quote(fourth, 25)})
        stale = rejected(lambda: ledger.propose(fourth, {"B": 30}, {"Hedge": 1}))
        ledger.mark(fourth, {"A": quote(fourth, 55, 0.8), "B": quote(fourth, 25)})
        blocked = quote(fourth, 55, 0.8) | {"tradable": False}
        ledger.mark(fourth, {"A": blocked})
        closed_listing = rejected(
            lambda: ledger.propose(fourth, {"B": 30}, {"Hedge": 1})
        )
        ledger.mark(fourth, {"A": quote(fourth, 55, 0.8)})
        draft = ledger.propose(fourth, {"B": 30}, {"Hedge": 1})
        ledger.cancel(draft)
        cancelled = rejected(lambda: Ledger(tmp, ledger.token).confirm(draft, fourth))
        proposal = ledger.propose(fourth, {"B": 30}, {"Hedge": 1})
        before = ledger.export()
        with ledger._connection(write=True) as c:
            c.execute("""CREATE TRIGGER interrupt_simulated_write BEFORE INSERT ON trades
                       WHEN NEW.asset='B' BEGIN SELECT RAISE(ABORT, 'injected interruption'); END""")
        try:
            ledger.confirm(proposal, fourth)
        except sqlite3.IntegrityError:
            pass
        with ledger._connection(write=True) as c:
            c.execute("DROP TRIGGER interrupt_simulated_write")
        after = ledger.export()
        rollback = before == after
        barrier = Barrier(2)

        def submit():
            independent = Ledger(tmp, ledger.token)
            barrier.wait(timeout=10)
            return independent.confirm(proposal, fourth)

        with ThreadPoolExecutor(max_workers=2) as pool:
            requests = [pool.submit(submit) for _ in range(2)]
            receipts = [request.result(timeout=15) for request in requests]
        final = ledger.export()
        versions = len(final["portfolios"])
        moves = sum(t["version"] == receipts[0] for t in final["trades"])
        isolated = (
            cross_account
            and marker not in _json(other.export())
            and len(other.export()["trades"]) == 0
        )
        markers = [marker, ledger.token, other.token]
        private_export = Path(tmp) / "private-export.json"
        private_export.write_text(_json(final))
        positive_control = rejected(lambda: audit_release([private_export], markers))
        release_scan = audit_release(release_paths, markers)
        ledger.delete()
        removed = rejected(lambda: Ledger(tmp, ledger.token)) and list(
            Path(tmp).glob("*.sqlite3")
        ) == [other._path]
        other.delete()
        safety = {
            "different_account_rejected": isolated,
            "private_marker_detector_positive_control": positive_control,
            "amended_mandate_rejected": obsolete,
            "delayed_settlement_rejected": delayed,
            "impossible_sale_rejected": bad_sale,
            "stale_mark_rejected": stale,
            "closed_listing_rejected": closed_listing,
            "cancellation_survived_restart": cancelled,
            "write_interruption_rolled_back": rollback,
            "same_receipt_for_two_confirmations": receipts == [2, 2]
            and versions == 2
            and moves == 2,
            "dossier_and_versions_deleted": removed,
        }
        if not all(safety.values()):
            raise AssertionError(str(safety))
        return {
            "hand_ledger": history,
            "uncorrected_day_two_value_chf": old_history[1]["value"],
            "hand_values_chf": expected_values,
            "hand_twr": expected_twr,
            "entry_fee_chf": initial_fee,
            "release_scan": release_scan,
            "original_parts": final["portfolios"][0]["parts"],
            "confirmation_versions": receipts,
            "revision_movements": moves,
            "controls": safety,
        }


def audit_release(paths, markers):
    """Scan supplied release files/logs for private fixture markers or bearer keys."""
    needles = [s.encode("utf-8") for s in markers if s]
    if not needles:
        raise ValueError("At least one private fixture marker is required.")
    files = sorted(set(map(Path, paths)))
    hits = []
    for path in files:
        data = path.read_bytes()
        if any(needle in data for needle in needles):
            hits.append(path)
    if hits:
        raise ValueError(
            "Private fixture material appeared in the selected release files."
        )
    return {"files_checked": len(files), "markers_checked": len(needles), "matches": 0}
