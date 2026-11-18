"""Shrink the raw StockTwits pickles (~21 GB, 90M tweets) to daily counts per firm.

Run once from the project root, with other heavy programs closed:

    python -m src.build_sentiment

Each pickle is loaded ONE AT A TIME (pickles cannot be streamed), reduced to
(ticker, day) -> Nbullish / Nbearish / N, written to data/processed/, then freed.
Output: data/processed/sentiment_firm_daily.parquet (a few hundred MB at most).
"""

import gc
import sys

import pandas as pd

from .paths import PROCESSED_DATA, RAW_DATA

RAW_FILES = [
    "df_withcorona_clean_1_with_proba_opti_and_hour.pkl",
    "df_withcorona_clean_2_with_proba_opti_and_hour.pkl",
]
# sent_merged = user label when given, otherwise the NLP-classified label (LN7).
SENT_COL = "sent_merged"
KEEP = ["ticker", "date", SENT_COL]
OUTPUT = PROCESSED_DATA / "sentiment_firm_daily.parquet"


def aggregate_file(path) -> pd.DataFrame:
    print(f"Loading {path.name} (this can take several minutes and lots of RAM)...", flush=True)
    df = pd.read_pickle(path)
    missing = [c for c in KEEP if c not in df.columns]
    if missing:
        sys.exit(f"Missing columns {missing}. Available: {list(df.columns)}")

    # Free the heavy text columns immediately.
    df.drop(columns=[c for c in df.columns if c not in KEEP], inplace=True)
    gc.collect()
    print(f"  {len(df):,} tweets", flush=True)

    df["date"] = pd.to_datetime(df["date"]).dt.normalize()
    df["bull"] = (df[SENT_COL] == 1).astype("int8")
    df["bear"] = (df[SENT_COL] == -1).astype("int8")

    daily = (
        df.groupby(["ticker", "date"], observed=True)
        .agg(Nbullish=("bull", "sum"), Nbearish=("bear", "sum"), N=("bull", "size"))
        .reset_index()
    )
    del df
    gc.collect()
    return daily


def main() -> None:
    PROCESSED_DATA.mkdir(parents=True, exist_ok=True)
    parts = []
    for name in RAW_FILES:
        part = aggregate_file(RAW_DATA / name)
        part.to_parquet(PROCESSED_DATA / f"{name}.daily.parquet")  # checkpoint
        parts.append(part)
        print(f"  -> {len(part):,} ticker-days", flush=True)

    # A (ticker, day) can straddle both files, so sum again.
    daily = (
        pd.concat(parts)
        .groupby(["ticker", "date"], as_index=False)[["Nbullish", "Nbearish", "N"]]
        .sum()
    )
    daily["polarity"] = (daily["Nbullish"] - daily["Nbearish"]) / (
        daily["Nbullish"] + daily["Nbearish"]
    ).replace(0, float("nan"))
    daily.to_parquet(OUTPUT)
    print(f"Saved {OUTPUT} ({len(daily):,} rows, {daily['ticker'].nunique():,} tickers)")


if __name__ == "__main__":
    main()
