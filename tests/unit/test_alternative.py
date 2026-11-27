from datetime import date
import numpy as np
import pytest
from riskmatch.strategies.alternative import capped, signed_rank, ledger, rank_signal, filtered_probability
from riskmatch.strategies.alternative_report import target


def test_signed_accounting():
    w=np.array([[.5,-.5],[.5,-.5]])
    r=ledger(np.array([[.1,-.1],[0.,0.]]),np.zeros(2),w,cost_bps=0,borrow_bps=0)
    assert r['returns'][0]==pytest.approx(.1)
    assert r['returns'][1]==pytest.approx(0)
    assert r['ledger'][0]['free_cash']==pytest.approx(50)
    assert r['ledger'][0]['net']==0
    assert r['ledger'][0]['gross']==1
    cost=ledger(np.zeros((2,2)),np.zeros(2),w,cost_bps=10,borrow_bps=1200)
    assert cost['returns'][0]<0 and cost['ledger'][0]['borrow']>0


def test_neutral_and_caps():
    s=np.arange(9.);u=np.full(9,.25);b=np.array([0,1,2,0,1,2,0,1,2.])
    w=signed_rank(s,u,b)
    assert w.sum()==pytest.approx(0,abs=1e-8)
    assert w@b==pytest.approx(0,abs=1e-8)
    assert max(abs(w))<=.25+1e-8
    assert capped([1,2],[.65,.65]).sum()==pytest.approx(1)
    with pytest.raises(ValueError):capped([1,1],[.2,.2])


def test_lag_and_filtered_probability():
    h=np.tile([.01,.02],(36,1));before=rank_signal(h);h[-1]=[.8,-.8]
    np.testing.assert_allclose(rank_signal(h),before)
    assert filtered_probability(np.zeros(24))<filtered_probability(np.full(24,.12))
    assert np.isfinite(filtered_probability(np.array([10.])))


def test_turnover_limit_and_exhaustion():
    x=np.zeros((2,2));w=[[1,0],[0,1]]
    assert ledger(x,[0,0],w,turnover_limit=.1)['status']=='unavailable'
    assert ledger([[0,3],[0,0]],[0,0],[[.5,-.5],[0,0]])['reason']=='Capital exhausted'


def test_tactical_bounds_and_unsupported_data():
    tick=['SPY','SHY','IEF','BIL','TIP'];assets=[{'ticker':t,'category':'equity_etf' if t=='SPY' else 'treasury_etf','source':'etf_crsp_monthly'} for t in tick]
    h=np.tile([.02,.002,.003,.001,.004],(48,1));u=np.ones(5)
    w=target('tactical_allocation',h,u,assets,None,None)
    assert w[0]==pytest.approx(.8) and w[2]==pytest.approx(.2)
    with pytest.raises(ValueError,match='Unsupported'):target('managed_futures',h,u,assets,None,None)


def test_momentum_can_run_with_no_treasury_reference_series():

    assets = [
        {"ticker": "SPY", "source": "etf_crsp_monthly", "category": "equity_etf"},
        {"ticker": "ABC", "source": "stock_monthly", "category": "stock"},
    ]
    returns = np.tile([.01, .02], (36, 1))
    caps = np.array([.65, .05])

    weights = target("cross_sectional_momentum", returns, caps, assets, None, None)

    np.testing.assert_allclose(weights, [0., .05])


def test_tail_hedge_measures_drawdown_from_the_opening_value():
    assets = [
        {"ticker": "SPY", "source": "etf_crsp_monthly", "category": "equity_etf"},
        {"ticker": "IEF", "source": "etf_crsp_monthly", "category": "treasury_etf"},
    ]
    returns = np.zeros((36, 2))
    returns[-12, 0] = -.15
    caps = np.ones(2)
    assert target("tail_hedge_proxy", returns, caps, assets, None, None) == pytest.approx([.2, .8])

    returns[-1, 0] = .1
    assert target("tail_hedge_proxy", returns, caps, assets, None, None) == pytest.approx([.6, .4])


def test_multi_strategy_correlation_uses_actual_sleeve_volatility():
    assets = [
        {"ticker": "SPY", "source": "etf_crsp_monthly", "category": "equity_etf"},
        {"ticker": "IEF", "source": "etf_crsp_monthly", "category": "treasury_etf"},
    ]
    returns = np.column_stack([np.tile([.001, .003], 18), np.full(36, -.01)])
    diagnostics = {}
    target("multi_strategy", returns, np.ones(2), assets, None, None, diagnostics)
    assert np.diag(diagnostics["correlation"]) == pytest.approx([1., 1., 1.])

    returns[:, 0] -= .01
    target("multi_strategy", returns, np.ones(2), assets, None, None, diagnostics)
    assert diagnostics["correlation"][1] == [None, None, None]
