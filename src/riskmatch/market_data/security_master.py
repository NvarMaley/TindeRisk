"""Point-in-time security master and candidate universe, not execution authorization."""

from dataclasses import dataclass, asdict
from datetime import date
from math import isfinite
from pathlib import Path
import csv
import json

from .universe import Holding, treasury_etf_eligible, treasury_eligible
from .local_sources import membership_summary, local_market_paths, monthly_audit, daily_audit, audit_available_for_as_of, treasury_identity_summary, issuer_holdings_summary

ROOT = Path(__file__).resolve().parents[3]
CATALOG_PATH = ROOT / "configs/universe_catalog.json"
ETF_CLASSES = {"equity_etf", "reit_etf", "treasury_etf", "commodity_etp"}
MIN_ADV_USD = 1_000_000  # provisional screening threshold; not a liquidity guarantee
MIN_AUM_USD = 100_000_000


@dataclass(frozen=True)
class Instrument:
    security_id: str
    ticker: str
    name: str
    asset_class: str
    sector: str
    sponsor: str
    inception: date
    domicile: str
    currency: str
    benchmark: str
    source: str
    listing_date: date | None = None
    multiplier: float = 1.0

    def __post_init__(self):
        if not self.security_id or not self.ticker or self.multiplier <= 0:
            raise ValueError("invalid_instrument")
        if self.listing_date and self.listing_date < self.inception:
            raise ValueError("listing_before_inception")


@dataclass(frozen=True)
class TickerAlias:
    security_id: str
    ticker: str
    valid_from: date
    valid_to: date | None  # exclusive
    available_on: date
    source: str

    def __post_init__(self):
        if not self.security_id or not self.ticker or not self.source or (self.valid_to and self.valid_to <= self.valid_from):
            raise ValueError("invalid_alias")


def resolve_ticker(aliases, ticker, as_of):
    matches = [a for a in aliases if a.ticker == ticker and a.available_on <= as_of
               and a.valid_from <= as_of and (a.valid_to is None or as_of < a.valid_to)]
    if len(matches) > 1:
        raise ValueError("ambiguous_ticker_history")
    return matches[0].security_id if matches else None


@dataclass(frozen=True)
class InvestabilityRecord:
    security_id: str
    observed_on: date
    available_on: date
    valid_until: date  # inclusive, explicit validity supported by source
    listing_date: date
    delisting_date: date | None
    listed: bool
    adv_usd: float | None
    expense_ratio: float | None  # annual decimal
    aum_usd: float | None
    restrictions: tuple[str, ...]
    source: str

    def __post_init__(self):
        if not self.source or self.available_on < self.observed_on or self.valid_until < self.available_on:
            raise ValueError("invalid_investability_dates")
        if self.delisting_date and self.delisting_date <= self.listing_date:
            raise ValueError("invalid_delisting")
        for v in (self.adv_usd, self.expense_ratio, self.aum_usd):
            if v is not None and (not isfinite(v) or v < 0):
                raise ValueError("invalid_investability_value")
        if self.expense_ratio is not None and self.expense_ratio > 1:
            raise ValueError("invalid_expense_ratio")


@dataclass(frozen=True)
class HoldingSnapshot:
    security_id: str
    observed_on: date
    available_on: date
    valid_until: date
    holdings: tuple[Holding, ...]
    complete_verified: bool
    source: str

    def __post_init__(self):
        if not self.source or self.available_on < self.observed_on or self.valid_until < self.available_on:
            raise ValueError("invalid_holdings_dates")


def _dated_record(records, security_id, as_of):
    available = [r for r in records if r.security_id == security_id and r.observed_on <= as_of
                 and r.available_on <= as_of <= r.valid_until]
    if not available:
        return None
    latest = max((r.observed_on, r.available_on) for r in available)
    matches = [r for r in available if (r.observed_on, r.available_on) == latest]
    if len(matches) != 1:
        raise ValueError("ambiguous_dated_record")
    return matches[0]


def load_catalog(path=CATALOG_PATH):
    payload = json.loads(Path(path).read_text())
    items = [Instrument(**(r | {"inception": date.fromisoformat(r["inception"]),
                                "listing_date": date.fromisoformat(r["listing_date"]) if r["listing_date"] else None}))
             for r in payload["instruments"]]
    if len({r.security_id for r in items}) != len(items) or len({r.ticker for r in items}) != len(items):
        raise ValueError("duplicate_catalog_identity")
    return payload, items


def assess_etf(instrument, as_of, investability=(), holdings=(), *, data_validated=False,
               min_adv=MIN_ADV_USD, min_aum=MIN_AUM_USD):
    """Do not turn public product metadata or adjusted close coverage into investability."""
    reasons = []
    if instrument.asset_class not in ETF_CLASSES or instrument.currency != "USD" or instrument.domicile != "US":
        reasons.append("outside_universe")
    if as_of < instrument.inception or (instrument.listing_date and as_of < instrument.listing_date):
        reasons.append("before_inception_or_listing")
    rec = _dated_record(investability, instrument.security_id, as_of)
    if rec is None:
        reasons.append("investability_unverified")
    else:
        if not rec.listed or as_of < rec.listing_date or (rec.delisting_date and as_of >= rec.delisting_date):
            reasons.append("not_listed")
        if rec.adv_usd is None or rec.aum_usd is None or rec.expense_ratio is None:
            reasons.append("liquidity_cost_metadata_missing")
        elif rec.adv_usd < min_adv or rec.aum_usd < min_aum:
            reasons.append("liquidity_below_screen")
        if rec.restrictions:
            reasons.append("restriction_present")
    if instrument.asset_class == "treasury_etf":
        snapshot = _dated_record(holdings, instrument.security_id, as_of)
        if snapshot is None or not snapshot.complete_verified:
            reasons.append("treasury_holdings_unverified")
        elif not treasury_etf_eligible(snapshot.holdings, verified_as_of=True):
            reasons.append("treasury_only_violation")
    if not data_validated:
        reasons.append("market_data_not_validated")
    return {"eligible": not reasons, "reasons": reasons}


def coverage_matrix(instruments, observations, *, source, as_of, frequency="daily"):
    """Observations are (date, ticker) pairs with valid values, source-grid only.

    Missingness is relative to observed union of source dates after inception,
    never a substitute for the exchange calendar or PIT availability.
    """
    grid = set()
    by_ticker = {}
    for when, ticker in observations:
        if when > as_of:
            continue
        dates = by_ticker.setdefault(ticker, set())
        if when in dates:
            raise ValueError("duplicate_observation")
        dates.add(when)
        grid.add(when)
    result = {}
    for item in instruments:
        boundary = max(item.inception, item.listing_date or item.inception)
        raw = by_ticker.get(item.ticker, set())
        valid = {d for d in raw if d >= boundary}
        eligible_grid = {d for d in grid if d >= boundary}
        expected = len(eligible_grid)
        result[item.ticker] = dict(source=source, frequency=frequency, basis="source_grid_not_exchange_calendar",
                                  status="observed" if valid else "not_observed", observed=len(valid),
                                  first=min(valid).isoformat() if valid else None,
                                  last=max(valid).isoformat() if valid else None,
                                  source_grid_sessions=expected, missing=expected-len(valid),
                                  missing_fraction=(expected-len(valid))/expected if expected else None,
                                  prelaunch_rejected=len(raw-valid), liquidity_usd=None)
    return result


def read_adjusted_csv(path):
    """Read local adjusted prices only; supports a wide or long CSV, no imputation."""
    path = Path(path)
    if path.stat().st_size > 25_000_000:
        raise ValueError("coverage_file_too_large")
    observations = []
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames:
            raise ValueError("local_source_unreadable")
        fields = {n.strip().lower(): n for n in reader.fieldnames}
        date_key = next((fields[k] for k in ("date", "observation_date", "trade_date", "timestamp") if k in fields), None)
        if date_key is None and reader.fieldnames[0].strip().lower() in {"", "unnamed: 0"}:
            date_key = reader.fieldnames[0]
        if date_key is None:
            raise ValueError("unknown_coverage_schema")
        symbol = next((fields[k] for k in ("ticker", "symbol") if k in fields), None)
        price = next((fields[k] for k in ("adjusted_close", "adj_close", "adj close", "price", "close") if k in fields), None)
        if symbol and price is None:
            raise ValueError("unknown_coverage_schema")
        for row in reader:
            if not row.get(date_key) or None in row:
                raise ValueError("unknown_coverage_schema")
            when = date.fromisoformat(row[date_key][:10])
            pairs = [(row[symbol], row[price])] if symbol else [(k,v) for k,v in row.items() if k != date_key]
            for ticker, val in pairs:
                if val is None or val.strip() in {"", ".", "NA", "NaN", "nan", "null"}:
                    continue
                x = float(val)
                if isfinite(x) and x > 0:
                    if not ticker or not ticker.strip():
                        raise ValueError("unknown_coverage_schema")
                    observations.append((when, ticker.strip().upper()))
    if not observations:
        raise ValueError("local_source_unreadable")
    return observations


def rate_coverage(as_of, path=None):
    """FRED DTB3 is a discount-yield observation, not the return on a cash holding."""
    path = Path(path or ROOT / "data/data/raw/DTB3.csv")
    dates, observed = set(), set()
    try:
        with path.open(encoding="utf-8-sig", newline="") as f:
            rows = csv.DictReader(f)
            if not rows.fieldnames or not {"observation_date", "DTB3"} <= set(rows.fieldnames):
                raise ValueError("unknown_rate_schema")
            for row in rows:
                d = date.fromisoformat(row["observation_date"])
                if d > as_of:
                    continue
                if d in dates:
                    raise ValueError("duplicate_rate_date")
                dates.add(d)
                if row["DTB3"] and row["DTB3"] != "." and isfinite(float(row["DTB3"])):
                    observed.add(d)
    except (OSError, ValueError, TypeError, KeyError):
        return {"status": "local_source_unavailable", "reference": "FRED:DTB3", "kind": "nontradable_discount_yield"}
    return {"status": "observed_local_unvalidated" if observed else "not_observed", "reference": "FRED:DTB3",
            "kind": "nontradable_discount_yield", "observed": len(observed), "missing": len(dates)-len(observed),
            "first": min(observed).isoformat() if observed else None, "last": max(observed).isoformat() if observed else None}


def load_dated_records(directory):
    """Read explicit local verified-record contracts; raw vendor exports are not accepted implicitly."""
    directory = Path(directory)
    result = {"investability": [], "holdings": [], "status": "missing"}
    for name, cls in (("investability", InvestabilityRecord), ("holdings", HoldingSnapshot)):
        path = directory / f"{name}.json"
        if not path.exists():
            continue
        try:
            if path.stat().st_size > 25_000_000:
                raise ValueError("record_file_too_large")
            records = json.loads(path.read_text())
            if not isinstance(records, list):
                raise ValueError("invalid_records")
            parsed = []
            for r in records:
                r = dict(r)
                for key in ("observed_on", "available_on", "valid_until", "listing_date", "delisting_date"):
                    if key in r and r[key] is not None:
                        r[key] = date.fromisoformat(r[key])
                if name == "holdings":
                    if type(r.get("complete_verified")) is not bool:
                        raise ValueError("invalid_verification")
                    r["holdings"] = tuple(Holding(**h) for h in r["holdings"])
                else:
                    if type(r.get("listed")) is not bool or not isinstance(r.get("restrictions"), list):
                        raise ValueError("invalid_investability")
                    r["restrictions"] = tuple(r["restrictions"])
                parsed.append(cls(**r))
            result[name] = parsed
            if result["status"] != "invalid":
                result["status"] = "present"
        except (OSError, ValueError, TypeError, KeyError):
            result["status"] = "invalid"
            result[name] = []
    return result


def reported_coverage(instruments, path, as_of, *, available_on=date(2026, 11, 22)):
    """Earlier local receipt summary, never relabel as newly observed raw coverage.

    Counts are usable as descriptive metadata only after the documented receipt
    and full interval; never truncate them retrospectively or infer missing prices.
    """
    if as_of < available_on:
        return {}
    by_ticker = {i.ticker: i for i in instruments}
    results = {}
    try:
        with Path(path).open(encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            required = {"series", "frequency", "first_observation", "last_observation", "observed", "missing_on_source_grid"}
            if not reader.fieldnames or not required <= set(reader.fieldnames):
                return {}
            for row in reader:
                ticker = row["series"]
                if ticker not in by_ticker:
                    continue
                first, last = date.fromisoformat(row["first_observation"][:10]), date.fromisoformat(row["last_observation"][:10])
                item = by_ticker[ticker]
                if first < max(item.inception, item.listing_date or item.inception) or first > last or last > as_of:
                    continue
                n, missing = int(row["observed"]), int(row["missing_on_source_grid"])
                if n < 0 or missing < 0 or ticker in results:
                    raise ValueError("invalid_reported_summary")
                total = n + missing
                results[ticker] = {"source": "local_prior_receipt_summary", "frequency": row["frequency"],
                                   "basis": "reported_unreconciled_summary", "status": "reported_unvalidated",
                                   "observed": n, "first": first.isoformat(), "last": last.isoformat(),
                                   "source_grid_sessions": total, "missing": missing,
                                   "missing_fraction": missing/total if total else None,
                                   "prelaunch_rejected": None, "liquidity_usd": None}
    except (OSError, ValueError, TypeError, KeyError):
        return {}
    return results


def universe_report(as_of, *, price_path=None, rate_path=None, records_dir=None, summary_path=None):
    payload, instruments = load_catalog()
    default_sources = price_path is None
    paths = [(name, path / "etf_prices_adjusted.csv") for name, path in local_market_paths()] if default_sources else [("explicit", price_path)]
    coverage = {}
    source_status = "local_source_unavailable"
    for name, path in paths:
        try:
            coverage = coverage_matrix(instruments, read_adjusted_csv(path), source=f"{name}_adjusted_etf_csv", as_of=as_of)
            source_status = "observed_local_unvalidated"
            break
        except (OSError, ValueError, TypeError, KeyError):
            continue
    if not coverage:
        coverage = reported_coverage(instruments, summary_path or ROOT / "data/data/processed/series_catalogue.csv", as_of)
        source_status = "local_summary_only" if coverage else "local_source_unavailable"
    audit = audit_available_for_as_of(monthly_audit(), as_of) if default_sources else None
    daily = audit_available_for_as_of(daily_audit(), as_of) if default_sources else None
    issuer_snapshots=issuer_holdings_summary(as_of) if default_sources else {}
    treasury_summary=treasury_identity_summary(as_of) if default_sources else None
    if rate_path is None and default_sources:
        rate = {"status": "local_source_unavailable", "reference": "FRED:DTB3", "kind": "nontradable_discount_yield"}
        for name, path in local_market_paths():
            rate = rate_coverage(as_of, path / "DTB3.csv")
            if rate["status"] != "local_source_unavailable":
                rate["source"] = name
                break
    else:
        rate = rate_coverage(as_of, rate_path)
    records = load_dated_records(records_dir or ROOT / "data/raw/universe")
    rows = []
    for item in instruments:
        row = asdict(item)
        row["inception"] = item.inception.isoformat()
        row["listing_date"] = item.listing_date.isoformat() if item.listing_date else None
        try:
            row.update(assess_etf(item, as_of, records["investability"], records["holdings"]))
            record = _dated_record(records["investability"], item.security_id, as_of)
        except ValueError:
            row.update({"eligible": False, "reasons": ["ambiguous_dated_record"]})
            record = None
        row["investability"] = ({"observed_on": record.observed_on.isoformat(), "adv_usd": record.adv_usd,
                                 "aum_usd": record.aum_usd, "expense_ratio": record.expense_ratio}
                                if record else None)
        row["coverage"] = coverage.get(item.ticker)
        monthly = audit.get("etf", {}).get(item.ticker) if audit else None
        row["monthly_coverage"] = {k:v for k,v in monthly.items() if k!="permno"} if monthly else None
        row["crsp_daily_coverage"] = daily.get("etf", {}).get(item.ticker) if daily else None
        row["issuer_snapshot"] = issuer_snapshots.get(item.ticker)
        if row["issuer_snapshot"] and not row["issuer_snapshot"]["strict_direct_treasury_snapshot_pass"]:
            row["reasons"].append("current_treasury_snapshot_blocked")
        rows.append(row)
    return {"version": payload["version"], "as_of": as_of.isoformat(),
            "metadata_reviewed_on": payload["metadata_reviewed_on"], "source_status": source_status,
            "record_status": records["status"],
            "rows": rows, "cash": payload["cash"], "risk_free": rate,
            "monthly_audit": ({"observed_etfs": audit["observed_etfs"], "snapshot_date": audit["snapshot_date"],
                               "stock_candidate_count": audit["stock_candidate_count"], "selected_count": audit["selected_count"],
                               "status": "local_unvalidated"} if audit else None),
            "daily_audit": ({"observed_etfs":daily["observed_etfs"],"snapshot_date":daily["snapshot_date"],
                             "stock_snapshot_count_with_return":daily["stock_snapshot_count_with_return"],"status":"local_unvalidated"} if daily else None),
            "treasury_identity":treasury_summary,
            "membership_review":membership_summary(as_of) if default_sources else None,
            "futures_roots":ARCHIVED_FUTURES_ROOTS,
            "active_futures_roots":FUTURES_ROOTS,
            "eligible_count": sum(r["eligible"] for r in rows),
            "mode": "research_candidates_not_allocations"}


@dataclass(frozen=True)
class StockMembership:
    permno: str
    observed_on: date
    available_on: date
    valid_until: date
    market_cap_usd: float
    us_common_stock: bool
    listed: bool
    delisting_date: date | None = None


def select_stock_universe(records, as_of, n=1000):
    """Future expansion: PIT rank by supplied historical market cap, never today's constituents."""
    if not 300 <= n <= 3000:
        raise ValueError("stock_count_outside_range")
    latest = {}
    for r in records:
        if r.observed_on <= r.available_on <= as_of <= r.valid_until:
            previous = latest.get(r.permno)
            if previous is None or (r.observed_on, r.available_on) > (previous.observed_on, previous.available_on):
                latest[r.permno] = r
            elif (r.observed_on, r.available_on) == (previous.observed_on, previous.available_on) and r != previous:
                raise ValueError("ambiguous_stock_record")
    eligible = [r for r in latest.values() if r.us_common_stock and r.listed and
                (r.delisting_date is None or as_of < r.delisting_date) and isfinite(r.market_cap_usd) and r.market_cap_usd > 0]
    ranked = sorted(eligible, key=lambda r: (-r.market_cap_usd, r.permno))[:n]
    return {"requested": n, "count": len(ranked), "complete": len(ranked) == n,
            "security_ids": [f"CRSP-PERMNO:{r.permno}" for r in ranked]}


@dataclass(frozen=True)
class TreasurySecurity:
    cusip: str
    holding: Holding
    issue_date: date
    maturity: date
    coupon_rate: float
    source: str

    def eligible(self, as_of):
        return bool(self.cusip and self.source and self.issue_date <= as_of < self.maturity and
                    isfinite(self.coupon_rate) and self.coupon_rate >= 0 and treasury_eligible(self.holding))


ARCHIVED_FUTURES_ROOTS = {"ES": "equity", "NQ": "equity", "RTY": "equity", "ZT": "rates", "ZF": "rates",
                 "ZN": "rates", "ZB": "rates", "CL": "commodity", "GC": "commodity", "6S": "fx"}
FUTURES_ROOTS: dict[str, str] = {}
HEDGE_MAP: dict[str, tuple[str, ...]] = {"USD_CHF": (), "US_EQUITY": (), "US_RATES": ()}


@dataclass(frozen=True)
class FuturesContract:
    root: str
    contract_id: str
    expiry: date
    last_trade_date: date
    multiplier: float
    tick_size: float
    currency: str
    settlement: str
    spec_available_on: date
    source: str

    def eligible(self, as_of):
        return self.root in FUTURES_ROOTS and self.valid_specification(as_of)

    def valid_specification(self, as_of):
        return bool(self.root in ARCHIVED_FUTURES_ROOTS and self.contract_id and self.source and
                    self.spec_available_on <= as_of <= self.last_trade_date <= self.expiry and
                    self.currency == "USD" and self.settlement in {"cash", "physical"} and
                    isfinite(self.multiplier) and self.multiplier > 0 and isfinite(self.tick_size) and self.tick_size > 0)


BENCHMARKS = {
    "equity_market": {"reference": "SP500_TR", "kind": "nontradable_index", "fund_proxy": "SPY"},
    "small_cap": {"reference": "RUSSELL2000_TR", "kind": "nontradable_index", "fund_proxy": "IWM"},
    "treasury": {"reference": "TREASURY_MATCHED_TR", "kind": "nontradable_index", "fund_proxy": "IEF"},
    "cash": {"reference": "FRED:DTB3", "kind": "nontradable_discount_yield", "fund_proxy": "BIL"},
    "balanced": {"reference": "60_SPY_40_IEF", "kind": "synthetic_rebalanced_benchmark", "fund_proxy": None},
    "mandate": {"reference": "MANDATE_BENCHMARK", "kind": "requires_mandate_definition", "fund_proxy": None},
}

STRATEGY_BENCHMARK = {
    **{f"STR{i:02}": "mandate" for i in range(1,20)},
    **{f"STR{i:02}": "equity_market" for i in (2,9,10,12)},
    **{f"STR{i:02}": "cash" for i in (3,4,6,8,11,13)},
    **{f"STR{i:02}": "balanced" for i in (7,14,15,16,17,18,19)},
}
