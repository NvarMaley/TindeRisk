"""Compare monthly-average prices in USD and report actual GLD holdings in CHF."""

import hashlib

import numpy as np
import pandas as pd


def source_tables(raw, cfg):
    archive = pd.read_excel(
        raw / "GLD-archive.xlsx",
        sheet_name="US GLD Historical Archive",
        usecols=[
            "Date",
            "Closing Price",
            "NAV/Share at 10:30am NYT",
            "Ounces of Gold per Share",
        ],
    )
    archive = archive.rename(
        columns={
            "Date": "date",
            "Closing Price": "close",
            "Ounces of Gold per Share": "ounces",
            "NAV/Share at 10:30am NYT": "nav",
        }
    )[["date", "close", "ounces", "nav"]]
    archive = archive.set_index(
        pd.to_datetime(archive.pop("date"), format="%d-%b-%Y")
    ).apply(pd.to_numeric, errors="coerce")
    archive = archive.sort_index().loc[cfg["gold_start"] : cfg["as_of"]]
    world = pd.read_excel(
        raw / "Pink-Sheet.xlsx", sheet_name="Monthly Prices", header=4
    )
    month = world.iloc[:, 0].astype(str)
    ok = month.str.fullmatch(r"\d{4}M\d{2}")
    spot = pd.Series(
        pd.to_numeric(world.loc[ok, "Gold"], errors="raise").to_numpy(),
        index=pd.PeriodIndex(month[ok].str.replace("M", "-"), freq="M"),
        name="spot",
    ).sort_index()
    spot = spot.loc[cfg["gold_start"][:7] : cfg["as_of"][:7]]
    if not archive.index.is_unique or not spot.index.is_unique:
        raise ValueError("Duplicate dates in gold inputs")

    def digest(frame):
        return hashlib.sha256(
            frame.to_csv(float_format="%.10f", lineterminator="\n").encode()
        ).hexdigest()

    return (
        archive,
        spot,
        {"GLD-archive.xlsx": digest(archive), "Pink-Sheet.xlsx": digest(spot)},
    )


def compare(raw, prices, fx, cfg):
    issuer, spot, digests = source_tables(raw, cfg)
    frame = (
        prices[prices.id.str.endswith("-GLD")]
        .set_index("day")
        .sort_index()
        .loc[cfg["gold_start"] : cfg["as_of"]]
        .copy()
    )
    frame.index = pd.to_datetime(frame.index)
    daily = frame[["adjusted", "close"]].join(issuer, rsuffix="_issuer")
    matched = daily[["close", "close_issuer"]].dropna()
    gap = (matched.close / matched.close_issuer - 1).abs()
    if gap.median() > 0.001:
        raise ValueError("Issuer and catalogue prices disagree")
    grouped = daily.adjusted.groupby(daily.index.to_period("M"))
    monthly = pd.concat(
        [grouped.mean().where(grouped.count() == grouped.size()).rename("fund"), spot],
        axis=1,
    )
    changes = monthly.pct_change(fill_method=None)

    def metrics(pair, label):
        clean = pair.dropna()
        diff = clean.fund - clean.spot
        return {
            "period": label,
            "months": len(clean),
            "pearson": clean.fund.corr(clean.spot),
            "mean_gap_bp_month": 10000 * diff.mean(),
            "tracking_error_annual": np.sqrt(12) * diff.std(),
        }

    windows = []
    for years in (1, 3, 5, 10):
        block = changes.iloc[-12 * years :]
        result = metrics(block, f"{years} year" + ("s" if years > 1 else ""))
        i = -12 * years - 1
        start = monthly.index[i]
        ends = daily.groupby(daily.index.to_period("M")).tail(1)
        a = ends[ends.index.to_period("M") == start].iloc[0]
        z = ends.iloc[-1]
        result["start"] = str(a.name.date())
        result["end"] = str(z.name.date())
        result["gld_close_total_usd"] = z.adjusted / a.adjusted - 1
        fxpair = fx.reindex([result["start"], result["end"]])
        result["gld_close_total_chf"] = (
            z.adjusted / a.adjusted * fxpair.iloc[-1] / fxpair.iloc[0] - 1
            if fxpair.notna().all()
            else None
        )
        for k in ("fund", "spot"):
            result[k + "_avg_price_change"] = (
                monthly[k].iloc[-1] / monthly[k].iloc[i] - 1
            )
        windows.append(result)
    # Exclude the change straddling the World Bank's June 2025 change of source.
    regimes = [
        metrics(changes.loc[:"2025-05"], "Through May 2025"),
        metrics(changes.loc["2025-07":], "From July 2025"),
    ]
    ounces = issuer.ounces.dropna()
    last = issuer.iloc[-1]
    return {
        "common_months": int(monthly.dropna().shape[0]),
        "common_changes": int(changes.dropna().shape[0]),
        "first_month": str(monthly.index[0]),
        "last_month": str(monthly.index[-1]),
        "validated_closes": len(matched),
        "median_close_gap_bp": 10000 * gap.median(),
        "p99_close_gap_bp": 10000 * gap.quantile(0.99),
        "expense_ratio": cfg["gld_annual_expense_ratio"],
        "ounces_per_share_change": ounces.iloc[-1] / ounces.iloc[0] - 1,
        "last_close_nav_gap": last.close / last.nav - 1,
        "windows": windows,
        "regimes": regimes,
        "bounded_hashes": digests,
    }, monthly
