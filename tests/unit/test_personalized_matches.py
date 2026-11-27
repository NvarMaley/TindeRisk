import copy
import json
from datetime import date
from pathlib import Path

import numpy as np

from riskmatch.personalized_matches import (
    adapt_target, bounds_for, defensive_reference, fingerprint, risk_preferences, valid_weights,
)
from riskmatch.profiling.mandate import validate_mandate


def test_mandate_conditioned_stress_overlay():
    upper = np.array([.65, .65, 1.])
    shocks = np.array([[-.4, -.1, 0.], [-.1, -.2, 0.]])
    covariance = np.diag([.09, .03, 0.])
    reference = defensive_reference(upper, shocks, covariance, .08, .10)
    target = np.array([.65, .35, 0.])
    cautious = adapt_target(target, reference, upper, shocks, .08, covariance, .10)
    permissive = adapt_target(target, reference, upper, shocks, .30, covariance, 1.)
    assert valid_weights(cautious, upper, shocks, .08, covariance, .10)
    assert valid_weights(permissive, upper, shocks, .30, covariance, 1.)
    assert cautious[0] < permissive[0]
    assert cautious[2] > permissive[2]
    assert defensive_reference(np.array([.1, .1, .1]), shocks, covariance, .08, .1) is None


def test_mandate_asset_filter_and_preference_version():
    root = Path(__file__).resolve().parents[2]
    mandate = json.loads((root / "configs/mandate-example.json").read_text())
    mandate["constraints"]["allowed_assets"] = ["treasury", "cash"]
    mandate["constraints"]["max_asset_weight"]["value"] = .25
    report = validate_mandate(mandate)
    assert report["personalized_eligible"] and not report["demo_eligible"]
    assets = [{"category": "stock", "instrument": "1", "ticker": "ABC"},
              {"category": "treasury_etf", "instrument": "2", "ticker": "SHY"}]
    upper, cash = bounds_for(assets, mandate, "date", {"date": {"1"}})
    assert np.allclose(upper, [0, .25])
    assert cash == .25
    assert risk_preferences(mandate, report, 30)[0] > risk_preferences(mandate, report, 1)[0]
    assert fingerprint(mandate, 1, "data") != fingerprint(mandate, 30, "data")
    amended = copy.deepcopy(mandate)
    amended["constraints"]["max_asset_weight"]["value"] = .3
    assert fingerprint(mandate, 1, "data") != fingerprint(amended, 1, "data")
    amended["constraints"]["max_issuer_weight"]["value"] = .2
    assert not validate_mandate(amended)["personalized_eligible"]


def test_variance_penalty_scale():
    penalty, safety_weight = risk_preferences({"goals": []}, {"horizon_years": 15}, 1)
    assert safety_weight == .25
    assert np.isclose(penalty, 1.83125)


def test_matching_mean_does_not_shrink_treasuries_toward_equity():
    from riskmatch.optimization.mean_variance_report import class_regularized_mean

    assets = [{"category": kind} for kind in ("stock", "equity_etf", "treasury_etf", "treasury_etf")]
    history = np.tile([.02, .04, -.02, 0.], (60, 1))
    assert np.allclose(class_regularized_mean(history, assets), [.30, .42, -.18, -.06])


def test_matching_report_distinguishes_research_and_incomplete_replay():
    from riskmatch.personalized_matches import FUNDED_METHODS, RESEARCH_METHODS, comparison_report

    assert len(FUNDED_METHODS) == 47
    assert set(RESEARCH_METHODS) == {"passive_index", "maximum_sortino", "maximum_omega"}
    assert "smart_beta_equal" not in FUNDED_METHODS
    card = {"name": "minimum_variance", "equivalent_methods": ["inverse_variance"]}
    unavailable = dict.fromkeys(set(FUNDED_METHODS) - {"minimum_variance", "inverse_variance"},
                                "Target breaches a modeled hard constraint")
    unavailable["equal_weight"] = "2021-02-26: missing observed return for a held security"
    report = comparison_report({"cards": [card], "unavailable": unavailable, "market_reference": {}})
    rows = {row["name"]: row for row in report["methods"]}
    assert rows["equal_weight"]["status"] == "backtest_incomplete"
    assert rows["passive_index"]["status"] == "research"
    assert rows["inverse_variance"]["card"] == "minimum_variance"
    assert rows["constrained_utility"]["status"] == "unavailable"


def test_matching_catalog_exposes_only_panel_instruments_and_cash(monkeypatch, tmp_path):
    from riskmatch import personalized_matches
    from riskmatch.profiling.mandate import add_month

    end = date(2025, 12, 31)
    boundaries = [add_month(date(2020, 12, 31), i) for i in range(61)]
    monkeypatch.setattr(personalized_matches, "market_data", lambda root: (
        [{"id": "stock:1", "source": "stock_monthly"},
         {"id": "ETF-IEF", "source": "etf_crsp_monthly"}], list(zip(boundaries, boundaries[1:]))))
    monkeypatch.setattr(personalized_matches, "client_catalog", lambda root, as_of: {
        "items": [{"id": item} for item in ("stock:1", "ETF-IEF", "ETF-GLD", "btc", "cash")],
        "as_of": as_of.isoformat()})
    catalog = personalized_matches.matching_catalog(tmp_path, end)
    assert [item["id"] for item in catalog["items"]] == ["stock:1", "ETF-IEF", "cash"]
    assert [item["matching_source"] for item in catalog["items"]] == [
        "stock_monthly", "etf_crsp_monthly", "fama_french_rf"]
    assert catalog["matching_data_start"] == "2020-12-31" and catalog["matching_months"] == 60
    assert catalog["matching_data_end"] == "2025-12-31"


def test_card_tail_loss_uses_fractional_worst_month_and_free_cash_trades():
    from riskmatch.prototype import metrics
    from riskmatch.backtesting.walk_forward import execute

    sample = np.r_[-.10, -.02, np.zeros(23)]
    assert np.isclose(metrics(sample[:, None], [1])["es95_monthly"], .084)
    holdings = np.array([0., 100_000.])
    funded, _, fee = execute(holdings, [0., 1.], .001)
    assert fee == 0 and np.isclose(funded.sum(), 100_000.)
    invested, _, fee = execute(funded, [.5, .5], .001)
    assert np.isclose(fee, .001*invested[0])


def test_historical_membership_lag_and_unpriced_holding(monkeypatch):
    from datetime import date, timedelta
    from riskmatch.backtesting import mandate_replay as module

    days = [date(2020,1,1)+timedelta(days=30*i) for i in range(68)]
    intervals = list(zip(days,days[1:]))
    spy = dict(id="SPY", ticker="SPY", category="equity_etf", instrument="1", source="etf")
    old = dict(id="OLD", ticker="OLD", category="stock", instrument="2", source="stock_monthly")
    assets = [spy,old]
    panel = np.zeros((67,2))
    panel[62,1] = np.nan
    stamp = np.full(panel.shape,np.datetime64("NaT"))
    caps = {day:{"2":1.} for day in days[:63]}
    monkeypatch.setattr(module,"archive",lambda *args:(assets,panel,stamp,None,None,caps,{}))
    decisions = []

    def construct(sample,mandate,report,aversion,end,origin):
        decisions.append((origin,[a["ticker"] for a in sample[0]],len(sample[2])))
        weights = np.zeros(len(sample[0])+1)
        weights[-1] = 1
        risky = weights.copy()
        risky[-1] = 0
        risky[-2] = 1
        return {"cash":weights, "risky":risky}, {}

    data = ([spy],intervals,None,np.zeros(67),"test",61,64)
    mandate = {"constraints":{"allowed_assets":["equity","cash"]}}
    history, failures = module.replay(None,data,mandate,{},15,construct,days[-1],())
    assert decisions == [(days[60],["SPY","OLD"],60),(days[63],["SPY"],60)]
    assert np.allclose(history["cash"]["returns"],0)
    assert "risky" not in history
    assert "missing observed return" in failures["risky"]
    assert "OLD" in failures["risky"]


def test_merger_proceeds_are_accounted_for_once_without_a_sale(monkeypatch):
    from datetime import timedelta
    from riskmatch.backtesting import mandate_replay as module

    days = [date(2020, 1, 1) + timedelta(days=30*i) for i in range(66)]
    intervals = list(zip(days, days[1:]))
    asset = dict(id="stock:1", ticker="OLD", category="stock", instrument="1", source="stock_monthly")
    panel = np.zeros((65, 1))
    panel[61, 0] = .12
    panel[62:] = np.nan
    stamps = np.full(panel.shape, np.datetime64("NaT"))
    caps = {day: {"1": 1.} for day in days}
    settlements = {0: (days[62] + timedelta(days=3), days[62])}
    monkeypatch.setattr(module, "archive",
                        lambda *args: ([asset], panel, stamps, None, None, caps, settlements))
    decisions = []

    def construct(sample, mandate, report, aversion, end, origin):
        decisions.append((origin, len(sample[0])))
        return {"risky": np.array([1., 0.] if sample[0] else [1.])}, {}

    cash = np.zeros(65)
    cash[62] = .002
    data = ([asset], intervals, None, cash, "test", 61, 64)
    constraints = {"allowed_assets": ["equity", "cash"],
                   "max_asset_weight": {"mode": "hard", "value": 1.}}
    history, failures = module.replay(None, data, {"constraints": constraints},
                                      {}, 15, construct, days[-1], ())
    assert not failures
    assert decisions == [(days[60], 1), (days[63], 0)]
    assert np.allclose(history["risky"]["returns"], [1.12/1.001-1, .002, 0., 0.])
    assert np.allclose(history["risky"]["turnover"][1:], 0.)


def test_matching_eligibility_filters_missing_late_and_unlisted_securities():
    from riskmatch.backtesting.mandate_replay import eligible_indices

    assets = [{"category": "stock", "instrument": str(i)} for i in range(4)]
    assets.append({"category": "equity_etf", "instrument": "SPY"})
    origin = date(2025, 12, 31)
    history = np.zeros((60, len(assets)))
    stamps = np.full(history.shape, np.datetime64("NaT"), dtype="datetime64[D]")
    history[0, 0] = -1  # a genuine complete loss remains an observation
    history[0, 1] = np.nan
    stamps[-1, 2] = np.datetime64("2026-01-01")
    assert eligible_indices(assets, history, stamps, origin, {"0", "1", "2"}).tolist() == [0, 4]


def test_dated_company_and_sector_exclusions():
    from riskmatch.market_data.portfolio_classification import exclusion_rule, sector_code

    day, past = date(2025, 12, 31), date(2022, 12, 30)
    rows = {day: {"1":("10","ABC","51"),"2":("10","ABD","51"),"3":("11","DEF","52")},
            past: {"1":("10","OLD","31"),"2":("10","ABD","51"),"3":("11","DEF","51")}}
    mandate = {"constraints":{"excluded_companies":["ABC"],"excluded_sectors":["52"]}}
    allowed = exclusion_rule(mandate, rows, day, {})
    stock = lambda instrument: {"category":"stock","instrument":instrument}
    assert not allowed(stock("1"),past) and not allowed(stock("2"),day)
    assert not allowed(stock("3"),day) and allowed(stock("3"),past)
    assert not allowed(stock("unknown"),day)
    assert not allowed({"category":"equity_etf"},day)
    assert allowed({"category":"treasury_etf"},day)
    assert sector_code("334510") == "31" and sector_code("000000") is None


def test_portfolio_composition_reports_signed_covariance(monkeypatch):
    from riskmatch import personalized_matches as pm

    assets = [{"category":"stock","instrument":"1"},{"category":"treasury_etf","instrument":"2"}]
    monkeypatch.setattr(pm,"matching_classification",lambda *args:{pm.DATA_END:{"1":("11","ABC","51")}})
    covariance = np.array([[.04,-.01,0],[-.01,.01,0],[0,0,0]])
    weights = np.array([.5,.5,0])
    result = pm.portfolio_composition(None,(assets,["ABC","SHY","USD cash"]),weights,covariance)
    assert np.isclose(result["volatility"]**2, .0075)
    assert np.isclose(result["cross_covariance"], -.005)
    assert np.isclose(sum(result["variance_shares"].values()), 1.)
    assert result["stock_sectors"] == {"51":.5}


def test_funded_matching_covariance_preserves_cash_volatility():
    from riskmatch.personalized_matches import construct, DATA_END

    root = Path(__file__).resolve().parents[2]
    mandate = json.loads((root / "configs/mandate-example.json").read_text())
    mandate["constraints"]["allowed_assets"] = ["equity", "cash"]
    report = validate_mandate(mandate)
    assets = [{"id": "ETF-SPY", "ticker": "SPY", "category": "equity_etf",
               "source": "etf_crsp_monthly", "instrument": "84398"}]
    risky = np.tile([-.08, .1], 30)
    cash = np.tile([.001, .003], 30)
    data = (assets, None, np.r_[np.nan, risky][:, None], np.r_[np.nan, cash],
            None, None, None, None, ({}, {}, {}), {}, {}, None)
    _, _, _, covariance, *_ = construct(data, mandate, report, 18, 61, DATA_END)
    assert np.allclose(np.diag(covariance), np.var(np.column_stack([risky, cash]), axis=0) * 12)
