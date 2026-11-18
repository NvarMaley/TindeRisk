"""Deterministic, entirely synthetic offline fixtures (never market evidence).

Generate the committed fixture with ``python -m src.demo_data``. This module
does not read production data or access the network.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pandas_market_calendars as mcal

from .data_loader import next_market_session
from .paths import DATA


DEMO_PATH = DATA / "demo" / "market_bundle.json"
NOTICE = "SYNTHETIC DEMO ONLY — not historical prices, investment evidence or validated signals."
TICKERS = ["XLK", "XLF", "XLE", "XLV", "XLY", "XLP", "XLI", "XLB", "XLU", "IEF", "TLT", "GLD", "SPY"]
MACRO = ["T10Y2Y", "BAA10Y", "VIXCLS", "CPIAUCSL", "UNRATE", "INDPRO"]


def _encode(frame):
    # pandas JSON uses null for intentionally undefined sentiment, not NaN JSON.
    values = json.loads(frame.to_json(orient="values", double_precision=12))
    return {"dates": [str(date.date()) for date in frame.index],
            "columns": list(frame.columns), "values": values}


def make_demo(seed=42):
    """Return small synthetic tables with production-compatible numerical schemas."""
    rng = np.random.default_rng(seed)
    dates = mcal.get_calendar("NYSE").valid_days("2024-01-02", "2024-04-03", tz=None)
    dates.name = "date"
    shocks = rng.normal(0.0001, 0.003, (len(dates)-1, len(TICKERS)))
    # One explicit synthetic stress day exercises downside displays.
    shocks[20, :9] -= 0.035
    prices = pd.DataFrame(
        np.vstack([np.full(len(TICKERS), 100.), 100 * np.cumprod(1 + shocks, axis=0)]),
        index=dates, columns=TICKERS,
    )
    returns = prices.pct_change(fill_method=None).iloc[1:]
    rf = pd.DataFrame({"rf_daily": np.full(len(returns), 0.03/252)}, index=returns.index)
    macro = pd.DataFrame(rng.normal(0, 1, (len(returns), len(MACRO))),
                         index=returns.index, columns=MACRO)
    frames = {"prices": prices, "returns": returns,
              "log_returns": np.log(prices).diff().iloc[1:], "rf_daily": rf,
              "excess_returns": returns.sub(rf.rf_daily, axis=0), "macro": macro}
    records = []
    following = next_market_session(dates)
    for i, date in enumerate(dates):
        for j, ticker in enumerate(TICKERS):
            if (i+j) % 11 == 0:
                continue  # Missing observation is not neutral sentiment.
            bull, bear = map(int, rng.integers(0, 20, size=2))
            if i == 2 and j == 0:
                bull = bear = 0  # Explicit undefined polarity despite messages.
            records.append({"asset": "MARKET" if ticker == "SPY" else ticker,
                            "date": str(date.date()),
                            "available_date": str(following[i].date()),
                            "Nbullish": bull, "Nbearish": bear, "N": bull+bear+3,
                            "polarity": (bull-bear)/(bull+bear) if bull+bear else None})
    return {"schema_version": 1, "synthetic": True, "notice": NOTICE,
            "seed": seed, "source": "generated independently; no external source observations",
            "units": {"currency_label": "USD (fictional)", "returns": "daily decimal",
                      "rf_daily": "synthetic flat 3% annual proxy / 252",
                      "macro": "arbitrary synthetic feature values, not actual economic levels"},
            "limitations": ["Insufficient history for the production 756-session warm-up",
                            "No real portfolio performance, GICS mapping or validated BL views",
                            "Calendar dates and ticker names are labels, not source data"],
            "frames": {name: _encode(frame) for name, frame in frames.items()},
            "sentiment": records}


def load_demo(path: Path = DEMO_PATH):
    """Explicit opt-in loader; never falls back to or overwrites production inputs."""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("synthetic") is not True or payload.get("schema_version") != 1:
        raise ValueError("expected a clearly labelled synthetic demo fixture")
    frames = {}
    for name, table in payload["frames"].items():
        index = pd.DatetimeIndex(pd.to_datetime(table["dates"]), name="date")
        frames[name] = pd.DataFrame(table["values"], index=index, columns=table["columns"])
    sentiment = pd.DataFrame(payload["sentiment"])
    for column in ["date", "available_date"]:
        sentiment[column] = pd.to_datetime(sentiment[column])
    return payload, frames, sentiment


def main():
    DEMO_PATH.parent.mkdir(parents=True, exist_ok=True)
    DEMO_PATH.write_text(json.dumps(make_demo(), separators=(",", ":"),
                                    ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    print(NOTICE)
    print(f"Generated {DEMO_PATH.relative_to(DATA.parent)} ({DEMO_PATH.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
