import copy
import json
from pathlib import Path
import numpy as np
import pytest
from riskmatch.analytics.objectives import SPECS, bootstrap_indices, evaluate
from riskmatch.profiling.mandate import OBJECTIVES, validate_mandate


def fixture():
    m=json.loads((Path(__file__).resolve().parents[2]/'configs/mandate-example.json').read_text())
    m.update(as_of='2026-01-01',horizon_date='2027-01-01',contribution_monthly=0,withdrawal_monthly=0,inflation=.02)
    m['goals']=[dict(objective_id='OBJ10',due_date='2027-01-01',amount=120000,currency='USD',basis='nominal',priority=3,shortfall_penalty=1,funding=True)]
    return m


def test_all_objectives_and_zero_return():
    m=fixture();z=np.zeros((200,12));r=evaluate(m,z,z)
    g=r['goals'][0]
    assert g['probability']==0 and g['expected_deficit']==20000
    assert r['mean_terminal_wealth']==0 and r['mean_unpaid_obligations']==20000
    assert set(SPECS)==set(OBJECTIVES)
    m['goals']=[dict(m['goals'][0],objective_id=k,amount=10000,funding=k in ('OBJ09','OBJ10')) for k in OBJECTIVES]
    r=evaluate(m,z,z,distribution_proxy=z)
    assert len(r['goals'])==11 and sum(g['weight'] for g in r['goals'])==pytest.approx(1.)
    assert r['goals'][6]['metrics']['real_market_cagr']<0
    assert r['goals'][7]['metrics']['cash_excess_cagr']==0


def test_priorities_and_no_double_spending():
    m=fixture();m['goals']=[dict(m['goals'][0],amount=80000,priority=1),dict(m['goals'][0],amount=80000,priority=5)]
    z=np.zeros((100,12));r=evaluate(m,z,z)
    assert r['goals'][1]['probability']==1
    assert r['goals'][0]['expected_deficit']==60000
    assert r['mean_terminal_wealth']==0
    assert r['weighted_target_penalty']==pytest.approx(1/6*.75)


def test_liability_and_dated_flows():
    m=fixture();m['dated_flows']=[{'date':'2026-02-01','kind':'liability','amount':150000},{'date':'2026-03-15','kind':'contribution','amount':10000}]
    z=np.zeros((100,12));r=evaluate(m,z,z)
    assert r['liability_schedule'][0]['mean_paid']==100000
    assert r['goals'][0]['metrics']['expected_unpaid_liability']==50000
    assert r['goals'][0]['expected_deficit']==110000
    assert r['mean_unpaid_obligations']==160000


def test_inflation_shock_and_partial_month():
    m=fixture();m['goals'][0].update(amount=100000,basis='real');z=np.zeros((100,12));base=evaluate(m,z,z)
    shocked=evaluate(m|{'inflation':.04},z,z)
    assert shocked['goals'][0]['expected_deficit']>base['goals'][0]['expected_deficit']>0
    m['horizon_date']='2026-01-16';m['goals'][0].update(objective_id='OBJ05',due_date='2026-01-16',amount=100000,basis='nominal',funding=False)
    a=np.full((100,1),.1);g=evaluate(m,a,a)['goals'][0]
    assert g['metrics']['mean_wealth']==pytest.approx(100000*1.1**(15/31))
    assert g['metrics']['cash_excess_cagr']==pytest.approx(0)


def test_invalid_shapes_and_conflicts():
    m=fixture();z=np.zeros((100,12));
    with pytest.raises(ValueError):evaluate(m,z[:,:1],z[:,:1])
    with pytest.raises(ValueError):evaluate(m,z-1,z)
    with pytest.raises(ValueError):evaluate(m|{'capital':1e7},z,z)
    with pytest.raises(ValueError):evaluate(m|{'goals':[dict(m['goals'][0],due_date='2028-01-01')]},z,z)
    a=bootstrap_indices(120,12,paths=10);assert np.array_equal(a,bootstrap_indices(120,12,paths=10))
    assert np.all(np.diff(a[:,:6],axis=1)==1)


def test_required_return_and_income_proxy():
    m=fixture();m['goals'][0].update(objective_id='OBJ05',amount=110000,funding=False);r=validate_mandate(m)
    assert r['goals'][0]['required_return']['annual_return']==pytest.approx(.1,abs=.001)
    m['goals'][0].update(objective_id='OBJ02',amount=12000);z=np.zeros((100,12));r=evaluate(m,z,z,distribution_proxy=z+.01)
    assert r['goals'][0]['probability'] is None
    assert r['goals'][0]['metrics']['income_target_proxy_coverage']==pytest.approx(1.)
