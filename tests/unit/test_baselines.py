from datetime import date
import numpy as np
import pytest
from riskmatch.backtesting.baselines import simulate, trade, metrics
from riskmatch.backtesting.baseline_report import continuous_segments, historical_windows

DATES=[(date(2024,1,31),date(2024,2,29)),(date(2024,2,29),date(2024,3,28))]


def test_two_period_hand_reconciliation():
    r=[[1.,0.],[0.,-.5]]
    a=simulate(r,DATES,[.5,.5]);b=simulate(r,DATES,[.5,.5],frequency='buy_hold')
    assert a['ledger'][0]['pre_trade_nav']==pytest.approx(150)
    assert a['ledger'][0]['drift_weights']==pytest.approx([2/3,1/3])
    assert a['ledger'][0]['closing_weights']==pytest.approx([.5,.5])
    assert a['ledger'][0]['traded_notional']==pytest.approx(50)
    assert a['final_nav']==pytest.approx(112.5)
    assert b['final_nav']==pytest.approx(125)
    assert b['ledger'][0]['closing_weights']==pytest.approx([2/3,1/3])
    assert not a['ledger'][-1]['rebalance']


def test_fees_and_flow_reconciliation():
    a=simulate([[1.,0.],[0.,-.5]],DATES,[.5,.5],cost_bps=100,flows=[10,0]);h=100/1.01
    before=1.5*h;fee=.01*.5*h;after=before+10-fee
    assert a['initial']['nav']==pytest.approx(h)
    assert a['initial']['fees']==pytest.approx(100-h)
    assert a['ledger'][0]['fee']==pytest.approx(fee)
    assert a['ledger'][0]['net_nav']==pytest.approx(after)
    assert a['returns'][0]==pytest.approx((after-10)/100-1)
    assert a['final_nav']==pytest.approx(after*.75)
    assert a['total_fees']==pytest.approx(100-h+fee)


def test_quarterly_and_withdrawal():
    dates=DATES+[(date(2024,3,28),date(2024,4,30))]
    a=simulate([[.1,0],[0,.1],[0,0]],dates,[.5,.5],frequency='quarterly')
    assert not a['ledger'][0]['rebalance'] and a['ledger'][1]['rebalance']
    h,delta,fee,turnover=trade([60,40],[.6,.4],-10,.01)
    assert h.sum()+fee==pytest.approx(90);assert sum(delta)==pytest.approx(-10-fee)
    with pytest.raises(ValueError):trade([60,40],[.6,.4],-100,.01)


def test_metrics_and_invalid_inputs():
    m=metrics([.1,-.5],[0,0]);assert m['max_drawdown']==pytest.approx(.5)
    assert m['cumulative']==pytest.approx(-.45)
    assert metrics([0,0],[0,0])['annual_excess_ratio'] is None
    for w in ([.2,.2],[-.1,1.1],[float('nan'),1]):
        with pytest.raises(ValueError):simulate([[0,0],[0,0]],DATES,w)
    with pytest.raises(ValueError):simulate([[0,0],[0,0]],[DATES[0],(date(2024,3,1),date(2024,3,28))],[.5,.5])
    with pytest.raises(ValueError):simulate([[0,0],[0,0]],DATES,[.5,.5],flows=[-101,0])
    assert len(continuous_segments([DATES[0],(date(2024,3,1),date(2024,3,28))]))==2
    assert historical_windows([0,0],DATES)=={}
