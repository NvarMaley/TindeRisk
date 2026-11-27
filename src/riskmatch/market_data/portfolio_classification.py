"""Dated direct-equity classification and optional mandate exclusions."""
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import re

import duckdb

SECTORS = frozenset("11 21 22 23 31 42 44 48 51 52 53 54 55 56 61 62 71 72 81 92".split())
TICKER = re.compile(r"[A-Z0-9][A-Z0-9.\-]{0,11}\Z")


def optional_preferences(constraints):
    """Validate optional settings without changing the meaning of older saves."""
    companies = constraints.get("excluded_companies", [])
    sectors = constraints.get("excluded_sectors", [])
    diversified = constraints.get("prefer_diversification", False)
    for key, values, check in (
        ("excluded_companies", companies, lambda v: bool(TICKER.fullmatch(v))),
        ("excluded_sectors", sectors, SECTORS.__contains__),
    ):
        if (not isinstance(values, list) or len(values) > 20
                or any(not isinstance(v, str) or not check(v) for v in values)
                or len(set(values)) != len(values)):
            raise ValueError(f"invalid_field:{key}")
    if type(diversified) is not bool:
        raise ValueError("invalid_field:prefer_diversification")
    return companies, sectors, diversified


def sector_code(naics):
    if not naics or len(naics) < 2 or not naics[:2].isdigit():
        return None
    prefix = naics[:2]
    group = {"32": "31", "33": "31", "45": "44", "49": "48"}.get(prefix, prefix)
    return group if group in SECTORS else None


@lru_cache(maxsize=4)
def dated_classification(root, dates, instruments):
    """Use delivered CRSP names intervals, never the current sector retroactively."""
    data = Path(root) / "data"
    try:
        base = data / "processed/universe"
        entry = json.loads((base / "wrds_delivery.json").read_text())["tables"]["names_history"]
        pit = json.loads((data / "processed/pit/report.json").read_text())
        expected = next(item["source_hash"] for item in pit["datasets"] if item["dataset"] == "wrds_names")
        if Path(entry["file"]).name != entry["file"]:
            return {}
        paths = list(data.glob("telecharger */" + entry["file"]))
        if len(paths) != 1:
            return {}
        source = paths[0]
        with source.open("rb") as stream:
            if hashlib.file_digest(stream, "sha256").hexdigest() != expected:
                return {}
    except (OSError, ValueError, KeyError, StopIteration):
        return {}
    with duckdb.connect() as db:
        rows = db.execute(
            """with names as (
                select permno, permco, upper(trim(ticker)) ticker, trim(naics) naics,
                       try_cast(secinfostartdt as date) since, try_cast(secinfoenddt as date) until
                from read_csv(?, all_varchar=true)
            )
            select d, permno, permco, ticker, naics
            from names join (select unnest(?)::date d) on since <= d and (until is null or d <= until)
            where permno in (select unnest(?))""", [str(source), list(dates), list(instruments)]).fetchall()
    grouped = {}
    for day, instrument, issuer, ticker, naics in rows:
        grouped.setdefault(day, {}).setdefault(instrument, set()).add(
            (issuer if issuer and issuer.isdigit() and int(issuer) else None,
             ticker if ticker and TICKER.fullmatch(ticker) else None, sector_code(naics)))
    return {day: {key: tuple(next(iter(values)) if len(values) == 1 else None
                            for values in map(set, zip(*records)))
                  for key, records in instruments.items()}
            for day, instruments in grouped.items()}


def exclusion_rule(mandate, classification, origin, label_by_instrument):
    companies, sectors, _ = optional_preferences(mandate["constraints"])
    if not companies and not sectors:
        return None
    latest = classification.get(origin)
    if not latest:
        raise ValueError("Dated company and industry data unavailable for exclusions")
    issuers = set()
    for symbol in companies:
        matches = {issuer for instrument, (issuer, ticker, _) in latest.items()
                   if issuer and (ticker == symbol or label_by_instrument.get(instrument) == symbol)}
        if len(matches) != 1:
            raise ValueError(f"Unknown or ambiguous exclusion ticker: {symbol}")
        issuers.update(matches)

    def allowed(asset, day):
        if asset["category"] == "equity_etf":
            return False
        if asset["category"] != "stock":
            return True
        issuer, _, sector = classification.get(day, {}).get(asset["instrument"], (None, None, None))
        return (not issuers or issuer is not None and issuer not in issuers) and (
            not sectors or sector is not None and sector not in sectors)

    return allowed
