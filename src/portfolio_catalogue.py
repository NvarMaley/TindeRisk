"""Build the Step 5.6c portfolio catalogue from verified local inputs."""

import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
import pandas as pd
import yaml

from .baselines import benchmark_60_40_weights, monthly_decision_closes
from .classic import fit_classic
from .client_allocation import NoEligibleAssetsError, reoptimize_for_client, resolve_client_exclusions
from .estimation import ledoit_wolf_constant_corr, trailing_returns_at_close
from .optim import tracking_error
from .paths import PROCESSED_DATA, RESULTS, ROOT
from .portfolio_analytics import (
    diversification_ratio, expected_shortfall_loss, risk_breakdown, risky_weight_herfindahl,
    risky_weight_shannon,
)
from .profiling import RiskBand
from .provenance import sha256_file

CATALOGUE_SCHEMA_VERSION = 4
CATALOGUE_FILE = "portfolio_catalogue.parquet"


def _fit_catalogue_sleeves(config, returns, excess_returns, decision, window):
    assets = config["tickers"]["sectors"] + config["tickers"]["diversifiers"]
    cap = config["portfolio"]["max_weight_per_asset"]
    benchmark = benchmark_60_40_weights(config["benchmark"])
    fit = fit_classic(returns[assets], excess_returns[assets], decision_date=decision,
                      window=window, max_weight=max(cap, 1 / len(assets)))
    benchmark_history = trailing_returns_at_close(returns[benchmark.index], decision, window)
    benchmark_covariance, _ = ledoit_wolf_constant_corr(benchmark_history)
    return fit, benchmark_covariance


def build_portfolio_catalogue(config: dict, returns: pd.DataFrame, excess_returns: pd.DataFrame, *,
                              decision_date: pd.Timestamp, comparison_start: str, comparison_end: str,
                              input_hashes: dict[str, str]) -> pd.DataFrame:
    """Build one allocation-only row per configured risk band and core strategy."""
    decision = pd.Timestamp(decision_date)
    settings = config["portfolio"]
    window = 252 * settings["estimation_window_years"]
    cap = settings["max_weight_per_asset"]
    assets = config["tickers"]["sectors"] + config["tickers"]["diversifiers"]
    equity = config["benchmark"]
    universe = assets + [equity]
    fit, benchmark_covariance = _fit_catalogue_sleeves(config, returns, excess_returns, decision, window)
    joint_returns = trailing_returns_at_close(returns[universe], decision, window)
    joint_covariance, _ = ledoit_wolf_constant_corr(joint_returns)
    bands = [RiskBand(key=key, **values) for key, values in config["risk_bands"].items()]
    strategies = config["scope"]["core_strategies"]
    if not strategies or len(strategies) != len(set(strategies)) or not bands:
        raise ValueError("catalogue requires nonempty risk bands and unique strategies")
    records = []
    for band in bands:
        benchmark_result = reoptimize_for_client(
            "benchmark_60_40", benchmark_covariance, band, max_etf_weight=cap, allow_borrowing=False,
            benchmark_equity=equity,
        )
        reference_weights = benchmark_result.allocation.risky_weights.reindex(universe, fill_value=0.)
        for strategy in strategies:
            if strategy == "benchmark_60_40":
                covariance, result = benchmark_covariance, benchmark_result
            else:
                covariance = fit.annual_covariance
                result = reoptimize_for_client(
                    strategy, covariance, band, max_etf_weight=cap, allow_borrowing=False,
                    annual_excess_mean=fit.annual_excess_mean, reference_sharpe=config["reference_sharpe"],
                    benchmark_equity=equity,
                )
            allocation = result.allocation
            achieved = allocation.achieved_volatility
            weights = allocation.risky_weights.reindex(universe, fill_value=0.)
            risk = risk_breakdown(allocation.risky_weights, covariance).reindex(universe, fill_value=0.)
            entropy = risky_weight_shannon(weights)
            records.append({
                "risk_band": band.key, "strategy": strategy, "risk_band_label": band.label,
                "decision_date": decision.date().isoformat(), "estimation_window_sessions": window,
                "estimation_window_start": joint_returns.index[0].date().isoformat(),
                "comparison_start": comparison_start, "comparison_end": comparison_end,
                "reference_volatility": band.reference_volatility,
                "band_min_volatility": band.min_volatility, "band_max_volatility": band.max_volatility,
                "ex_ante_volatility": achieved, "target_shortfall": result.target_shortfall,
                "reference_volatility_gap": result.reference_gap, "risk_band_position": result.band_position,
                "ex_ante_tracking_error": tracking_error(weights, reference_weights, joint_covariance),
                "risky_weight_herfindahl": risky_weight_herfindahl(weights),
                "risky_weight_shannon": entropy,
                "risky_weight_effective_holdings": np.exp(entropy),
                "diversification_ratio": diversification_ratio(allocation.risky_weights, covariance),
                "snapshot_es95_daily_loss": expected_shortfall_loss(joint_returns @ weights),
                "information_ratio": float("nan"),
                "within_risk_band": result.band_position == "within",
                "reference_reached": result.target_shortfall <= 1e-10,
                "allocation_method": result.method, "historical_metrics_status": "pending_backtest",
                "allow_borrowing": False, "max_etf_weight": cap, "cash_weight": max(0., allocation.cash_weight),
                **{f"weight_{asset}": weights[asset] for asset in universe},
                **{f"risk_contribution_{asset}": risk.at[asset, "risk_contribution"] for asset in universe},
                **{f"risk_share_{asset}": risk.at[asset, "risk_share"] for asset in universe},
            })

    catalogue = pd.DataFrame(records)
    catalogue.insert(0, "schema_version", CATALOGUE_SCHEMA_VERSION)
    for name, value in sorted(input_hashes.items()):
        catalogue[f"{name}_sha256"] = value
    for metric in config["client_display"]["summary_metrics"]:
        catalogue[metric] = float("nan")
    contents = catalogue.to_json(orient="records", double_precision=15)
    fingerprint = hashlib.sha256(contents.encode("utf-8")).hexdigest()[:12]
    catalogue.insert(1, "catalogue_version", f"v{CATALOGUE_SCHEMA_VERSION}-{decision:%Y%m%d}-{fingerprint}")
    return catalogue


def profile_volatility_preview(profile: dict, risk_band: str):
    """Re-optimize the chosen band at the prepared, locally verified decision close."""
    config_path = ROOT / "config.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    risk = profile["risk"]
    if not risk["reference_check_passed"] or risk["category"]["id"] != risk_band:
        raise ValueError("profile risk reference is unresolved")
    catalogue = pd.read_parquet(
        RESULTS / CATALOGUE_FILE,
        columns=["risk_band", "decision_date", "schema_version", "config_sha256",
                 "returns_sha256", "excess_returns_sha256"],
        filters=[("risk_band", "==", risk_band)],
    ).drop_duplicates()
    if (len(catalogue) != 1 or catalogue["schema_version"].iat[0] != CATALOGUE_SCHEMA_VERSION
            or catalogue["config_sha256"].iat[0] != sha256_file(config_path)):
        raise ValueError("regenerate the catalogue for the current configuration")
    metadata = catalogue.iloc[0]
    data = []
    for name in ("returns", "excess_returns"):
        path = PROCESSED_DATA / f"{name}.parquet"
        if sha256_file(path) != metadata[f"{name}_sha256"]:
            raise ValueError("prepared portfolio inputs have changed")
        data.append(pd.read_parquet(path))

    date = pd.Timestamp(metadata["decision_date"])
    settings = config["portfolio"]
    window = settings["estimation_window_years"] * 252
    fit, benchmark_covariance = _fit_catalogue_sleeves(config, *data, date, window)
    band = RiskBand(key=risk_band, **config["risk_bands"][risk_band])
    constraints = profile["constraints"]
    equity = config["benchmark"]
    excluded = resolve_client_exclusions(constraints["excluded_groups"], benchmark_equity=equity)
    cap = constraints["max_etf_weight"]
    cap = min(cap, settings["max_weight_per_asset"]) if cap is not None else None
    allocations = {}
    for strategy in config["scope"]["core_strategies"]:
        covariance = benchmark_covariance if strategy == "benchmark_60_40" else fit.annual_covariance
        try:
            allocations[strategy] = reoptimize_for_client(
                strategy, covariance, band, excluded_assets=excluded, max_etf_weight=cap,
                allow_borrowing=constraints["allow_borrowing"], leverage_limit=settings["leverage_limit"],
                capacity_volatility=risk["capacity_volatility"], annual_excess_mean=fit.annual_excess_mean,
                reference_sharpe=config["reference_sharpe"], benchmark_equity=equity,
            )
        except NoEligibleAssetsError:
            allocations[strategy] = None
    return date, allocations


def main() -> Path:
    config_path = ROOT / "config.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    manifest = json.loads((PROCESSED_DATA / "common_sample_manifest.json").read_text(encoding="utf-8"))
    extended_name = "common_extended_returns.parquet"
    files = {"returns": PROCESSED_DATA / "returns.parquet",
             "excess_returns": PROCESSED_DATA / "excess_returns.parquet",
             "extended_calendar": PROCESSED_DATA / extended_name}
    expected_hashes = {"returns": manifest["inputs"]["returns"],
                       "excess_returns": manifest["inputs"]["excess_returns"],
                       "extended_calendar": manifest["files"][extended_name]["sha256"]}
    for name, path in files.items():
        if sha256_file(path) != expected_hashes[name]:
            raise ValueError(f"catalogue input checksum mismatch: {path.name}")
    dates = pd.read_parquet(files["extended_calendar"], columns=[config["benchmark"]]).index
    close = monthly_decision_closes(dates)[-1]
    main_period = manifest["periods"]["main"]
    catalogue = build_portfolio_catalogue(
        config, pd.read_parquet(files["returns"]), pd.read_parquet(files["excess_returns"]),
        decision_date=close, comparison_start=main_period["first_date"], comparison_end=main_period["last_date"],
        input_hashes={"config": sha256_file(config_path), **expected_hashes},
    )

    RESULTS.mkdir(parents=True, exist_ok=True)
    output = RESULTS / CATALOGUE_FILE
    with TemporaryDirectory(dir=RESULTS) as staging:
        temporary = Path(staging) / CATALOGUE_FILE
        catalogue.to_parquet(temporary, index=False)
        temporary.replace(output)
    print(f"{len(catalogue)} entries written to {output.relative_to(ROOT)} ({catalogue['catalogue_version'].iat[0]}).")
    return output


if __name__ == "__main__":
    main()
