from datetime import date
import numpy as np
import pytest
from riskmatch.strategies.long_only import allocate,ranked,cap_turnover,dynamic_ledger,alpha_signal
from riskmatch.strategies.long_only_report import weights_at

DATES=[(date(2024,1,31),date(2024,2,29)),(date(2024,2,29),date(2024,3,28))]


def test_rank_and_zero_signal():
    w,m=ranked([3,2,1],[.6,.6,.6],['A','B','C'],.3);assert sum(w)==pytest.approx(1);assert w[2]==0;assert max(w)<=.600001
    w,m=ranked([0,0,0],[.7]*3,['A','B','C'],positive_only=True);assert w==pytest.approx([1/3]*3);assert m['fallback']
    with pytest.raises(ValueError):ranked([np.nan,np.nan],[1,1],['A','B'],fallback=False)


def test_forced_exit_and_turnover():
    p=np.array([.7,.3,0]);t=np.array([0,.5,.5]);u=np.array([0,.8,.8]);w,f=cap_turnover(p,t,u,.5);assert w is None and f==pytest.approx(.7)
    w,f=cap_turnover([.5,.5],[1.,0],[1.,1.],.2);assert w==pytest.approx([.7,.3]);assert f==pytest.approx(0)


def test_dynamic_ledger_reconciliation_and_costs():
    x=np.array([[1.,0.],[0.,-.5]]);targets=[np.array([.5,.5])]*2;caps=[np.ones(2)]*2
    a=dynamic_ledger(x,DATES,targets,caps,0,1);assert a['status']=='computed';assert a['ledger'][0]['nav']==pytest.approx(150);assert a['ledger'][1]['nav']==pytest.approx(112.5)
    b=dynamic_ledger(x,DATES,targets,caps,100,.1);assert b['status']=='computed';assert b['ledger'][1]['turnover']<=.100000001;assert b['fees']>0 and b['ledger'][1]['nav']<150
    with pytest.raises(ValueError):dynamic_ledger(x,DATES,targets[:1],caps,0,1)


def test_missing_fundamental_and_passive_cap():
    assets=[{'id':'A','source':'etf_crsp_monthly','instrument':'1','ticker':'SPY'},{'id':'B','source':'stock_monthly','instrument':'2','ticker':'B'}];d=date(2024,1,31);history=np.random.default_rng(2).normal(.01,.02,(36,2));u=np.array([.6,.6]);m={d:{'2'}}
    w,_,r=weights_at('passive_index',history,assets,u,d,m,{}, {},.6,0);assert w is None and 'cap' in r['reason']
    w,_,r=weights_at('smart_beta_fundamental',history,assets,u,d,m,{}, {},.6,0);assert w is None
    w,_,r=weights_at('passive_index',history,assets,np.ones(2),d,m,{}, {},.6,0);assert w==pytest.approx([1,0])
    w,_,r=weights_at('smart_beta_equal',history,assets,u,d,{}, {}, {},.6,0);assert w is None
