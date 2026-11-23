"""Assess the provider's documented IBM samples without saving or publishing prices."""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from time import perf_counter
from zoneinfo import ZoneInfo

import exchange_calendars as xcals
import pandas as pd
import requests

OUT = Path(__file__).with_name("intraday.json")
URL = "https://www.alphavantage.co/query"


def inspect_sample(historical=False):
    params = {"function": "TIME_SERIES_INTRADAY", "symbol": "IBM", "interval": "5min"}
    if historical:
        params.update(month="2009-01", outputsize="full")
    params["apikey"] = "demo"
    started = perf_counter()
    response = requests.get(URL, params=params, timeout=20)
    received = datetime.now(UTC)
    receipt = {
        "http_status": response.status_code,
        "received_utc": received.isoformat(),
        "http_seconds": round(perf_counter() - started, 3),
    }
    response.raise_for_status()
    payload = response.json()
    if "Time Series (5min)" not in payload:
        return receipt | {"status": "No sample bars returned"}
    bars = payload["Time Series (5min)"]
    zone = ZoneInfo(payload["Meta Data"]["6. Time Zone"])
    times = {datetime.fromisoformat(k).replace(tzinfo=zone): v for k, v in bars.items()}
    newest = max(times)
    receipt.update(
        rows=len(times),
        latest_bar_stamp=newest.isoformat(),
        seconds_since_sample_stamp=round((received - newest).total_seconds(), 1),
    )
    if historical:
        days = sorted({t.date() for t in times}, reverse=True)
        cal = xcals.get_calendar(
            "XNYS",
            start=min(days) - timedelta(days=7),
            end=max(days) + timedelta(days=7),
        )
        for d in days:
            if not cal.is_session(pd.Timestamp(d)):
                continue
            start = cal.session_open(pd.Timestamp(d)).to_pydatetime().astimezone(zone)
            end = cal.session_close(pd.Timestamp(d)).to_pydatetime().astimezone(zone)
            slots = [
                start + timedelta(minutes=5 * i)
                for i in range(int((end - start).total_seconds() / 300))
            ]
            if not all(t in times for t in slots):
                continue
            for t in slots:
                row = times[t]
                low, high = float(row["3. low"]), float(row["2. high"])
                assert 0 < low <= float(row["1. open"]) <= high
                assert (
                    low <= float(row["4. close"]) <= high and int(row["5. volume"]) >= 0
                )
            receipt["session_replay"] = {
                "session": str(d),
                "exchange": "XNYS",
                "first_slot": slots[0].isoformat(),
                "last_slot": slots[-1].isoformat(),
                "expected_5min_slots": len(slots),
                "observed_slots": len(slots),
                "missing_slots": 0,
                "ohlcv_checks": "passed",
            }
            break
    return receipt | {"status": "Historical sample"}


if __name__ == "__main__":
    sample = inspect_sample()
    archive = inspect_sample(historical=True)
    result = {
        "provider": "Alpha Vantage",
        "symbol": "IBM",
        "currency": "USD",
        "compact": sample,
        "historical": archive,
        "account_live_enabled": False,
        "validated_intraday_chf_pairs": 0,
        "portfolio_live_display_rights_verified": False,
        "published_payload": "Timing and coverage diagnostics only",
    }
    OUT.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps(result, indent=2))
