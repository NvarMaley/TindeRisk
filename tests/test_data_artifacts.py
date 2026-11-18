from pathlib import Path

import pandas as pd

from src.data_loader import load_sentiment_firm_daily


ROOT = Path(__file__).resolve().parents[1]


def test_published_sentiment_artifact_covers_the_investable_universe():
    tickers = ["XLK", "XLF", "XLE", "XLV", "XLY", "XLP", "XLI", "XLB", "XLU", "IEF", "TLT", "GLD", "SPY"]
    sentiment = load_sentiment_firm_daily(
        ROOT / "data" / "processed" / "sentiment_firm_daily.parquet",
        tickers=tickers,
    )

    assert set(sentiment["ticker"].unique()) == set(tickers)
    assert sentiment["date"].min() <= pd.Timestamp("2010-01-01")
    assert sentiment["date"].max() >= pd.Timestamp("2020-03-20")
    assert (sentiment["available_date"] > sentiment["date"]).all()
    assert not sentiment.duplicated(["ticker", "date"]).any()
