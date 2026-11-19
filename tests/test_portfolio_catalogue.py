import numpy as np
import pandas as pd
import yaml

from src.paths import ROOT
from src.portfolio_catalogue import CATALOGUE_SCHEMA_VERSION, build_portfolio_catalogue


def test_catalogue_keys_weights_and_pending_metrics_round_trip(tmp_path):
    config = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
    assets = config["tickers"]["sectors"] + config["tickers"]["diversifiers"] + [config["benchmark"]]
    dates = pd.bdate_range("2007-01-01", periods=780)
    rng = np.random.default_rng(145)
    returns = pd.DataFrame(rng.normal(.0006, .009, (len(dates), len(assets))), index=dates, columns=assets)
    arguments = {"decision_date": dates[-1], "comparison_start": "2010-01-04",
                 "comparison_end": "2020-03-31", "input_hashes": {"config": "a" * 64}}
    catalogue = build_portfolio_catalogue(config, returns, returns - .0001, **arguments)
    expected = {(band, strategy) for band in config["risk_bands"]
                for strategy in config["scope"]["core_strategies"]}
    assert len(catalogue) == len(expected)
    assert set(zip(catalogue.risk_band, catalogue.strategy, strict=True)) == expected
    assert catalogue.schema_version.eq(CATALOGUE_SCHEMA_VERSION).all()
    assert catalogue.catalogue_version.nunique() == 1
    assert catalogue["historical_metrics_status"].eq("pending_backtest").all()
    assert catalogue[config["client_display"]["summary_metrics"]].isna().all().all()
    weights = catalogue.filter(regex=r"^weight_")
    assert weights.ge(0).all().all()
    assert weights.max().max() <= config["portfolio"]["max_weight_per_asset"] + 1e-9
    assert catalogue.cash_weight.ge(-1e-9).all()
    np.testing.assert_allclose(weights.sum(axis=1) + catalogue.cash_weight, 1, atol=1e-9, rtol=0)
    assert (catalogue.ex_ante_volatility <= catalogue.reference_volatility + 1e-9).all()
    benchmark = weights.loc[catalogue.strategy.eq("benchmark_60_40")]
    np.testing.assert_allclose(benchmark.weight_SPY / benchmark.weight_IEF, 1.5)

    np.testing.assert_allclose(catalogue.filter(regex=r"^risk_contribution_").sum(axis=1),
                               catalogue.ex_ante_volatility, atol=1e-12, rtol=0)
    np.testing.assert_allclose(catalogue.filter(regex=r"^risk_share_").sum(axis=1), 1., atol=1e-12, rtol=0)
    assert catalogue.loc[catalogue.strategy.eq("benchmark_60_40"), "ex_ante_tracking_error"].eq(0).all()
    assert catalogue["ex_ante_tracking_error"].ge(0).all()
    assert catalogue["information_ratio"].isna().all()

    repeat = build_portfolio_catalogue(config, returns, returns - .0001, **arguments)
    pd.testing.assert_frame_equal(repeat, catalogue)
    altered_inputs = {**arguments, "input_hashes": {"config": "b" * 64}}
    altered = build_portfolio_catalogue(config, returns, returns - .0001, **altered_inputs)
    assert altered.catalogue_version.iat[0] != catalogue.catalogue_version.iat[0]
    output = tmp_path / "catalogue.parquet"
    catalogue.to_parquet(output, index=False)
    pd.testing.assert_frame_equal(pd.read_parquet(output), catalogue)
