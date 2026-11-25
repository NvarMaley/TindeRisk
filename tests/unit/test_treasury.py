from datetime import date
import numpy as np
import pytest
from riskmatch.analytics.treasury import schedule,yield_metrics,yield_price,bootstrap,discount,curve_metrics,holding_return,ladder


def test_par_and_coupon_date():
    issue=date(2025,2,28);mat=date(2030,2,28);flows,a=schedule(issue,mat,issue,.04,'treasury_note')
    assert a==0 and len(flows)==10 and flows[0][0]==date(2025,8,31)
    assert flows[-1][1]==102
    m=yield_metrics(flows,100.,a)
    assert m['yield']==pytest.approx(.04)
    assert m['modified_duration']==pytest.approx(m['yield_effective_duration'],rel=1e-6)
    y=m['yield'];b=.0001
    assert m['convexity']==pytest.approx((yield_price(flows,y+b)+yield_price(flows,y-b)-200)/(100*b*b),rel=1e-6)


def test_actual_actual_and_dated_issue():
    issue=date(2026,6,1);mat=date(2028,5,31);settle=date(2026,8,31);dated=date(2026,5,31)
    with pytest.raises(ValueError,match='irregular'):schedule(issue,mat,settle,.04,'treasury_note')
    flows,a=schedule(issue,mat,settle,.04,'treasury_note',dated)
    assert a==pytest.approx(2*(settle-dated).days/(date(2026,11,30)-dated).days)
    f,a=schedule(issue,mat,date(2026,11,30),.04,'treasury_note',dated)
    assert a==0 and f[0][0]==date(2027,5,31)
    with pytest.raises(ValueError):schedule(issue,mat,mat,.04,'treasury_note')


def test_bill_tips_indexation_and_floor():
    issue=date(2026,1,1);mat=date(2026,7,1);flows,a=schedule(issue,mat,issue,0.,'treasury_bill')
    assert len(flows)==1 and a==0 and flows[0][1]==100
    m=yield_metrics(flows,98.,0.)
    assert m['macaulay_duration']==pytest.approx((mat-issue).days/365)
    f,a=schedule(issue,date(2031,1,1),issue,.02,'tips');r=yield_metrics(f,100,a,1.15)
    assert r['indexed_dirty_per_100']==pytest.approx(115)
    assert r['yield']==pytest.approx(.02)
    assert holding_return(100,101,2)==pytest.approx(.03)


def test_bootstrap_and_key_rate_sum():
    c=bootstrap({.5:.04,2:.04,5:.04,10:.04,30:.04})
    assert discount(c,5)==pytest.approx((1.02)**-10)
    d=date(2025,1,1);f,a=schedule(d,date(2030,1,1),d,.04,'treasury_note');m=curve_metrics(f,d,100,c)
    assert sum(m['key_rate_duration'].values())==pytest.approx(m['effective_duration'],rel=1e-6)
    assert m['curve_shocks']['parallel_up_100bp']<0<m['curve_shocks']['parallel_down_100bp']


def test_ladder_no_free_money_and_key_rate():
    d=date(2026,1,1);mat=date(2027,1,1);flows,a=schedule(d,mat,d,0.,'treasury_bill');c=bootstrap({.5:.04,30:.04});m=yield_metrics(flows,96,0);k=curve_metrics(flows,d,96,c);q={'cusip':'test','flows':flows,'spread_per_100':.02,**m,**k}
    r=ladder([q],d,100,[(mat,103)],1.,0.,c)
    assert r['coverage'][0]['shortfall']==pytest.approx(0)
    assert r['invested_with_cost']+r['residual_cash']==pytest.approx(100)
    r=ladder([q],d,100,[(mat,200)],.25,10.,c)
    assert r['coverage'][0]['shortfall']>90 and r['invested_with_cost']<=25+1e-9
    k=ladder([q],d,100,[(mat,100)],1.,0.,c,'key_rate');assert len(k['key_rate_matching'])==5
    both=ladder([q],d,100,[(mat,103)],1.,0.,c,'combined');assert both['coverage'][0]['shortfall']==pytest.approx(0,abs=1e-7)
    with pytest.raises(ValueError,match='infeasible'):ladder([q],d,100,[(mat,103)],1.,0.,c,'combined',max_dv01=0.)
