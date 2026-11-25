"""Point-in-time contracts. Unknown publication times never qualify for historical joins."""

from dataclasses import dataclass
from datetime import date, datetime, timezone
from math import isfinite
from zoneinfo import ZoneInfo
import hashlib
import json


def utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Explicit timezone required")
    return value.astimezone(timezone.utc)


def session_close(day: date, sessions: dict[date, datetime]) -> datetime:
    """Use an explicit exchange calendar, including early closes and holidays."""
    return utc(sessions[day])


def equity_close(day: date, hour: int, minute: int = 0) -> datetime:
    return utc(datetime(day.year, day.month, day.day, hour, minute,
                        tzinfo=ZoneInfo("America/New_York")))


@dataclass(frozen=True)
class Observation:
    instrument: str
    field: str
    day: date
    available: datetime | None
    version: str
    value: float
    unit: str

    def __post_init__(self):
        if self.available is not None:
            utc(self.available)
        if not self.instrument or not self.field or not self.version or not self.unit:
            raise ValueError("Missing identity, version or unit")
        if not isfinite(self.value):
            raise ValueError("Nonfinite value")


def as_of_rows(rows, decision: datetime):
    """Select revisions known at the decision, reject simultaneous conflicting values."""
    decision = utc(decision)
    chosen = {}
    for row in rows:
        if row.available is None or utc(row.available) > decision or row.day > decision.date():
            continue
        key = (row.instrument, row.field, row.day)
        candidates = chosen.get(key)
        if candidates is None or utc(candidates[0].available) < utc(row.available):
            chosen[key] = [row]
        elif utc(candidates[0].available) == utc(row.available):
            candidates.append(row)
    result = []
    for key in sorted(chosen):
        candidates = chosen[key]
        if len({(r.value, r.unit) for r in candidates}) != 1:
            raise ValueError("Conflicting simultaneous revisions")
        result.append(min(candidates, key=lambda r: r.version))
    return tuple(result)


def lagged_feature(rows, decision, *, instrument, field, session_days, lag, lookback, unit):
    """A lag of one excludes the decision's current session. Gaps invalidate features."""
    if lag < 1 or lookback < 1:
        raise ValueError("Positive lag and lookback required")
    decision = utc(decision)
    days = sorted(set(day for day in session_days if day <= decision.date()))
    end = len(days) - lag
    if end < lookback:
        raise ValueError("Insufficient calendar history")
    required = days[end-lookback:end]
    actual = {r.day: r for r in as_of_rows(rows, decision)
              if r.instrument == instrument and r.field == field}
    if any(day not in actual or actual[day].unit != unit for day in required):
        raise ValueError("Missing observation or incompatible unit")
    selected = [actual[day] for day in required]
    payload = [(r.day.isoformat(), r.version, r.value, utc(r.available).isoformat()) for r in selected]
    return {"instrument": instrument, "field": field, "as_of": decision.isoformat(),
            "lag": lag, "lookback": lookback, "unit": unit,
            "value": sum(r.value for r in selected)/lookback,
            "dataset_hash": hashlib.sha256(json.dumps(payload).encode()).hexdigest()}


def session_status(day, sessions, observed):
    if day not in sessions:
        return "closed"
    return "observed" if day in observed else "missing"


@dataclass(frozen=True)
class DatedIdentity:
    instrument: str
    ticker: str
    valid_from: date
    valid_until: date | None
    available: datetime | None


def identity_at(records, ticker: str, decision: datetime):
    """Dated ticker links and membership revisions must be known at decision time."""
    decision = utc(decision)
    day = decision.date()
    eligible = {r.instrument for r in records if r.ticker == ticker
                and r.available is not None and utc(r.available) <= decision
                and r.valid_from <= day and (r.valid_until is None or day < r.valid_until)}
    if len(eligible) != 1:
        raise ValueError("Unknown or ambiguous dated identity")
    return eligible.pop()


def store_feature(database, feature):
    """Persist a versioned feature; identical requests are idempotent."""
    import duckdb
    with duckdb.connect(str(database)) as db:
        db.execute("""create table if not exists features (
            instrument varchar, field varchar, as_of timestamptz, lag int,
            lookback int, unit varchar, value double, dataset_hash varchar,
            primary key(instrument,field,as_of,lag,lookback,unit,dataset_hash))""")
        db.execute("insert into features values (?,?,?,?,?,?,?,?) on conflict do nothing",
                   [feature[k] for k in ("instrument","field","as_of","lag","lookback",
                                        "unit","value","dataset_hash")])


def require_snapshot(report, required_datasets):
    """All future financial entry points must use this gate."""
    datasets = {row["dataset"]: row for row in report.get("datasets", [])}
    if not report.get("approved") or any(
        not datasets.get(name, {}).get("pit_eligible") for name in required_datasets
    ):
        raise ValueError("market_snapshot_unavailable")


def snapshot_report(root, as_of: date):
    """Expose only local aggregate metadata; fail closed with missing or altered partitions."""
    from pathlib import Path
    base = Path(root) / "data/processed/pit"
    unavailable = {"schema": "pit-v1", "approved": False, "datasets": [],
                   "reason": "snapshot_unavailable"}
    try:
        report = json.loads((base / "report.json").read_text())
        if datetime.fromisoformat(report["built_at"]).date() > as_of:
            return unavailable
        key = report["snapshot_id"]
        if len(key) != 64 or any(c not in "0123456789abcdef" for c in key):
            return unavailable
        if hashlib.sha256(json.dumps(report["datasets"], sort_keys=True).encode()).hexdigest() != key:
            return unavailable | {"reason": "snapshot_integrity_failure"}
        for row in report["datasets"]:
            name = row["dataset"]
            if not name or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789_-" for c in name):
                return unavailable
            with (base / key / f"{name}.parquet").open("rb") as stream:
                if hashlib.file_digest(stream, "sha256").hexdigest() != row["file_hash"]:
                    return unavailable | {"reason": "snapshot_integrity_failure"}
        return report | {"approved": False}
    except (OSError, ValueError, TypeError, KeyError):
        return unavailable


def market_snapshot(report, decision: datetime, universe_version, instruments):
    """Adapt the quality evidence to the shared MarketSnapshot contract."""
    from riskmatch.contracts import MarketSnapshot, RunMetadata, Status
    decision = utc(decision)
    datasets = report.get("datasets", [])
    if not datasets:
        raise ValueError("market_snapshot_unavailable")
    return MarketSnapshot(
        meta=RunMetadata(as_of=decision, run_id=report["snapshot_id"],
                         model_version="pit-v1", units=(("frequency", "daily reference"),),
                         provenance=tuple(row["source_hash"] for row in datasets),
                         status=Status.EXPERIMENTAL,
                         warnings=(report["reason"],)),
        universe_version=universe_version, dataset_hash=report["snapshot_id"],
        instrument_ids=tuple(instruments), frequency="daily",
        completeness=tuple((row["dataset"], row["rows"], row["input_rows"]) for row in datasets),
        rejection_reasons=tuple(sorted({row["reason"] for row in datasets})),
        latest_observation=max(date.fromisoformat(row["last"]) for row in datasets if row["rows"]),
    )
