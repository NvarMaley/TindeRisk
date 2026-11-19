import numpy as np
import pandas as pd
import yaml
from streamlit.testing.v1 import AppTest

from src import portfolio_catalogue as catalogue
from src.paths import ROOT
from src.provenance import sha256_file


def test_portfolios_display_personalized_estimated_volatility_separate_from_backtest(monkeypatch, tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_bytes((ROOT / "config.yaml").read_bytes())
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assets = config["tickers"]["sectors"] + config["tickers"]["diversifiers"] + [config["benchmark"]]
    dates = pd.bdate_range("2007-01-01", periods=780)
    generator = np.random.default_rng(135)
    returns = pd.DataFrame(generator.normal(.0006, .009, (len(dates), len(assets))), index=dates, columns=assets)
    excess = returns - .0001
    returns.to_parquet(tmp_path / "returns.parquet")
    excess.to_parquet(tmp_path / "excess_returns.parquet")
    hashes = {name: sha256_file(tmp_path / filename) for name, filename in
              {"config": "config.yaml", "returns": "returns.parquet", "excess_returns": "excess_returns.parquet"}.items()}
    prepared = catalogue.build_portfolio_catalogue(
        config, returns, excess, decision_date=dates[-1], comparison_start="2010-01-04",
        comparison_end="2020-03-31", input_hashes=hashes,
    )
    prepared.to_parquet(tmp_path / catalogue.CATALOGUE_FILE, index=False)
    for name in ("ROOT", "PROCESSED_DATA", "RESULTS"):
        monkeypatch.setattr(catalogue, name, tmp_path)

    profile = {
        "risk": {"reference_check_passed": True, "category": {"id": "balanced"}, "capacity_volatility": .08},
        "constraints": {"excluded_groups": ["energy", "treasuries"],
                        "max_etf_weight": .25, "allow_borrowing": True},
    }
    page = next((ROOT / "app/pages").glob("2_*_Portfolios.py"))
    app = AppTest.from_file(str(page))
    app.session_state["risk_band"] = "balanced"
    app.session_state["profile"] = profile
    app.run(timeout=30)
    assert not app.exception
    estimates = [item for item in app.metric if item.label == "Estimated annual volatility"]
    assert len(estimates) == 3
    assert any("no eligible ETF" in notice.value for notice in app.info)
    _, expected = catalogue.profile_volatility_preview(profile, "balanced")
    fit = expected["classic"]
    assert estimates[0].value == f"{fit.allocation.achieved_volatility:.2%}"
    assert estimates[0].delta == f"{100 * fit.reference_gap:+.2f} pp vs reference"
    assert all(item.value == "—" for item in app.metric if item.label == "Realized risk")

    def failed_preview(*args):
        raise RuntimeError("simulated optimizer failure")

    monkeypatch.setattr(catalogue, "profile_volatility_preview", failed_preview)
    app.run(timeout=30)
    assert not app.exception
    assert any("optimizer could not produce" in notice.value for notice in app.info)
    assert all(item.label != "Estimated annual volatility" for item in app.metric)
