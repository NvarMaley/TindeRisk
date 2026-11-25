from datetime import date,datetime
import pytest
from riskmatch.analytics.futures import Spec,Mark,variation,integer_position,simulate,continuous_changes


SPEC=Spec('TEST',10.,.25,'points')
def mark(day,price,contract='20240300',**kwargs):
    return Mark(datetime(2024,1,day,23),contract,price,{contract:price},**kwargs)


def test_negative_mark_and_integer_size():
    assert variation(2,1000,5,-3)==-16000
    assert variation(-2,1000,5,-3)==16000
    assert integer_position(-100,SPEC,10000,.55,1,.1,.2)==5
    assert integer_position(0,SPEC,10000,.55,1,.1,.2)==0
    assert integer_position(100,SPEC,100,.55,1,.1,.2)==0


def test_roll_no_artificial_gap_and_reconciliation():
    a=mark(2,100);b=mark(3,123,'20240600',roll_from=a.contract,old_price=102,new_price=120,roll_stamp=datetime(2024,1,3,20));rows=[a,b,mark(4,125,'20240600')]
    r=simulate(rows,SPEC,capital=10000,target=.5,commission=0,slippage_ticks=0)
    first=r['ledger'][0]['quantity'];new=r['rolls'][0]['new_quantity'];assert first==5
    assert r['rolls'][0]['curve_gap']==18
    assert r['ledger'][1]['variation_margin']==first*10*2+new*10*3
    assert r['final_nav']==pytest.approx(10000+r['total_variation_margin'])
    assert continuous_changes(rows)[1]['change']==5
    with_cost=simulate(rows,SPEC,capital=10000,target=.5,commission=2,slippage_ticks=1)
    assert with_cost['total_cost']>0
    assert with_cost['final_nav']==pytest.approx(10000+with_cost['total_variation_margin']-with_cost['total_cost'])


def test_missing_overlap_expired_and_gap():
    a=mark(2,100);b=mark(3,120,'20240600')
    assert simulate([a,b],SPEC)['reason']=='Missing simultaneous old/new quote on roll'
    with pytest.raises(ValueError,match='expired'):simulate([mark(2,100,'20231200'),mark(3,100,'20231200')],SPEC)
    assert simulate([a,mark(15,100)],SPEC)['status']=='stopped'


def test_margin_increase_and_spec_change():
    rows=[mark(2,100),mark(3,100),mark(4,100)]
    r=simulate(rows,SPEC,capital=10000,target=1,gross_limit=1.5,commission=0,slippage_ticks=0,margin_schedule={date(2024,1,3):(.95,.9)})
    assert r['status']=='stopped' and r['ledger'][-1]['quantity']==0 and 'margin' in r['reason']
    r=simulate(rows,SPEC,capital=10000,target=.5,spec_schedule={date(2024,1,3):Spec('TEST',20,.25,'points')})
    assert r['status']=='stopped' and 'specification changed' in r['reason']


def test_cash_interest_and_negative_wealth():
    r=simulate([mark(2,100),mark(3,100)],SPEC,capital=10000,target=0,cash_rate=.0365,commission=0,slippage_ticks=0)
    assert r['final_nav']==pytest.approx(10001.)
    r=simulate([mark(2,100),mark(3,-1000)],SPEC,capital=10000,target=1,commission=0,slippage_ticks=0)
    assert r['status']=='stopped' and r['final_nav']<0
