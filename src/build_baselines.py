"""Build the step 2.5 monthly benchmark diagnostics from verified local data."""

import json

import pandas as pd
import pandas_market_calendars as mcal
import yaml

from .baselines import apply_monthly_targets, minimum_variance_weights
from .descriptive import descriptive_statistics
from .estimation import ledoit_wolf_constant_corr, validate_returns
from .paths import PROCESSED_DATA, RESULTS, ROOT
from .provenance import sha256_file


def main():
    config_path = ROOT / "config.yaml"
    config = yaml.safe_load(config_path.read_text())
    source_path = PROCESSED_DATA / "common_sample_manifest.json"
    source = json.loads(source_path.read_text())
    assets = config["tickers"]["sectors"] + config["tickers"]["diversifiers"]
    benchmark = config["benchmark"]
    universe = assets + [benchmark]
    window = 252 * config["portfolio"]["estimation_window_years"]
    cap = config["portfolio"]["max_weight_per_asset"]
    manifest = {"common_sample_manifest_sha256": sha256_file(source_path),
                "config_sha256": sha256_file(config_path), "window_sessions": window,
                "gmv_weight_cap": cap, "files": {}, "periods": {},
                "scope": "gross historical baseline diagnostics; DTB3 descriptive proxy"}
    RESULTS.mkdir(exist_ok=True)
    calendar = mcal.get_calendar("NYSE")
    summaries = []

    for period in config["validation"]["periods"]:
        frames = {}
        for key in ("returns", "warmup_returns", "rf_daily"):
            path = PROCESSED_DATA / f"common_{period}_{key}.parquet"
            if sha256_file(path) != source["files"][path.name]["sha256"]:
                raise ValueError(f"common sample checksum mismatch: {path.name}")
            frames[key] = pd.read_parquet(path)
        returns = frames["returns"]
        history = pd.concat([frames["warmup_returns"], returns])
        validate_returns(history)
        if list(returns.columns) != universe or list(frames["warmup_returns"].columns) != universe:
            raise ValueError("common return universe differs from config")
        first, last = returns.index[[0, -1]]
        prev_month = first.replace(day=1) - pd.offsets.MonthBegin()
        schedule = calendar.valid_days(prev_month, last + pd.offsets.MonthEnd(0), tz=None)
        month_ends = schedule[~schedule.to_period("M").duplicated(keep="last")]
        initial = month_ends[month_ends < first][-1]
        dates = month_ends[(month_ends >= initial) & (month_ends < last)]
        if not dates.isin(history.index).all():
            raise ValueError("required NYSE month-end close is missing from the sample")
        history_sessions = calendar.valid_days(history.index[0], last, tz=None)
        if not history.index.equals(history_sessions):
            raise ValueError("return history has missing or unexpected NYSE sessions")

        equal = pd.DataFrame(1 / len(assets), index=dates, columns=assets)
        blend = pd.DataFrame({benchmark: .6, "IEF": .4}, index=dates)
        gmv_rows = []
        for date in dates:
            panel = history.loc[:date, assets].tail(window)
            if len(panel) != window:
                raise ValueError(f"insufficient history for GMV at {date.date()}")
            covariance, _ = ledoit_wolf_constant_corr(panel, annualize=1)
            gmv_rows.append(minimum_variance_weights(covariance, cap))
        gmv = pd.DataFrame(gmv_rows, index=dates, columns=assets)

        targets = {"Equal weight": equal, "GMV": gmv, "60/40": blend}
        daily = {name: apply_monthly_targets(returns[weights.columns], weights)
                 for name, weights in targets.items()}
        summary = descriptive_statistics(
            pd.DataFrame({name: table["gross_return"] for name, table in daily.items()}),
            frames["rf_daily"]["rf_daily"],
        )[["ann_return", "ann_vol", "sharpe", "max_drawdown"]].rename_axis("baseline")
        summaries.append(summary.reset_index().assign(period=period))
        tables = {
            f"2_5_{period}_returns.csv": pd.concat(daily, axis=1).rename_axis("date"),
            f"2_5_{period}_targets.csv": pd.concat(
                {name: weights.reindex(columns=universe, fill_value=0)
                 for name, weights in targets.items()}, names=["baseline", "decision_close"]),
        }
        for name, table in tables.items():
            table.to_csv(RESULTS / name)
            manifest["files"][name] = sha256_file(RESULTS / name)
        manifest["periods"][period] = {"start": str(first.date()), "end": str(last.date()),
                                      "sessions": len(returns), "target_dates": len(dates)}

    summary_path = RESULTS / "2_5_summary.csv"
    pd.concat(summaries, ignore_index=True).to_csv(summary_path, index=False)
    manifest["files"][summary_path.name] = sha256_file(summary_path)
    (RESULTS / "2_5_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
