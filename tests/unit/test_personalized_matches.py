import copy
import json
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

    days = [date(2024,1,1)+timedelta(days=30*i) for i in range(10)]
    intervals = list(zip(days,days[1:]))
    spy = dict(id="SPY", ticker="SPY", category="equity_etf", instrument="1", source="etf")
    old = dict(id="OLD", ticker="OLD", category="stock", instrument="2", source="stock_monthly")
    assets = [spy,old]
    panel = np.zeros((9,2))
    panel[5,1] = np.nan
    stamp = np.full((9,2),np.datetime64("NaT"))
    caps = {day:{"2":1.} for day in days[:6]}
    monkeypatch.setattr(module,"archive",lambda *args:(assets,panel,stamp,None,None,caps))
    decisions = []

    def construct(sample,mandate,report,aversion,end,origin):
        decisions.append((origin,[a["ticker"] for a in sample[0]],len(sample[2])))
        weights = np.zeros(len(sample[0])+1)
        weights[-1] = 1
        risky = weights.copy()
        risky[-1] = 0
        risky[-2] = 1
        return {"cash":weights, "risky":risky}, {}

    data = ([spy],intervals,None,np.zeros(9),"test",4,7)
    mandate = {"constraints":{"allowed_assets":["equity","cash"]}}
    history, failures = module.replay(None,data,mandate,{},15,construct,days[-1])
    assert decisions == [(days[3],["SPY","OLD"],3),(days[6],["SPY"],6)]
    assert np.allclose(history["cash"]["returns"],0)
    assert "risky" not in history
    assert "missing observed return" in failures["risky"]
