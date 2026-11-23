"""Independent issuer and share-class evidence used only to identify historical prices."""

import json
import re
from collections import defaultdict
from pathlib import Path

import pandas as pd
from openpyxl import load_workbook

from .fetch import RAW, atomic, get

SEC = "https://www.sec.gov/files/company_tickers_exchange.json"
SPTM = "https://www.ssga.com/library-content/products/fund-data/etfs/us/holdings-daily-us-en-sptm.xlsx"


def symbol(value):
    return re.sub(r"[./ ]", "-", str(value).strip().upper())


def issuer_key(value):
    words = re.findall("[A-Z0-9]+", str(value).upper())
    ignored = set(
        "THE INC INCORPORATED CORP CORPORATION CO COMPANY PLC LTD LIMITED CLASS CL COMMON STOCK NEW DE DELAWARE MD".split()
    )
    return " ".join(w for w in words if w not in ignored)


def references(rows, download=False):
    for name, url in [("SEC.json", SEC), ("SPTM.xlsx", SPTM)]:
        if download and not (RAW / name).is_file():
            atomic(RAW / name, get(url))
    directory = pd.read_csv(RAW / "nasdaqtraded.txt", sep="|")
    usable = directory[(directory["Test Issue"] == "N") & (directory["ETF"] == "N")]
    derivative = usable["Security Name"].str.contains(
        r"warrants?|preferred|depositary shares|senior notes|debentures|purchase rights|subscription rights|units,? each",
        case=False,
        na=False,
    )
    common = {symbol(v) for v in usable.loc[~derivative, "Symbol"]}
    filing = json.loads((RAW / "SEC.json").read_bytes())
    company = defaultdict(set)
    for cik, name, code, exchange in filing["data"]:
        if (
            exchange in ("NYSE", "Nasdaq", "NYSE American", "Cboe")
            and symbol(code) in common
        ):
            company[issuer_key(name)].add(symbol(code))
    book = load_workbook(RAW / "SPTM.xlsx", read_only=True, data_only=True)
    values = list(book.active.values)
    holding_date = str(values[2][1])
    by_id = defaultdict(set)
    for row in values[5:]:
        code, cusip = symbol(row[1]), str(row[2]).strip()
        if re.fullmatch(r"[A-Z0-9]{9}", cusip) and re.fullmatch(
            r"[A-Z][A-Z0-9-]{0,9}", code
        ):
            by_id[cusip].add(code)
    book.close()
    events = json.loads(Path("config/actions-2026-evenements.json").read_bytes())
    choices = {}
    for row in rows.itertuples():
        matches = company.get(issuer_key(row.issuer), set())
        # Cross-check candidates later using price overlap, avoiding broad group name matches.
        choices[row.permno] = sorted(
            by_id.get(row.cusip, set()) | (matches if len(matches) <= 4 else set())
        )
        event = events.get(row.ticker, {})
        if event.get("issuer") == row.issuer and event.get("type") == "rename":
            choices[row.permno].append(event["symbol"])
    return choices, by_id, holding_date
