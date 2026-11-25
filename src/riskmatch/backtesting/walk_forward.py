"""Chronological portfolio research with an explicit delayed, self-financing ledger."""
from dataclasses import dataclass
import numpy as np
from riskmatch.backtesting.baselines import metrics
from riskmatch.optimization.downside import stats
from riskmatch.optimization.hierarchical import proportional_cap

VERSION='walk-forward-v3'


@dataclass(frozen=True)
class Fold:
    train_start:int
    train_end:int
    validation_start:int
    validation_end:int
    decision:int
    test_end:int
    phase:str


def folds(n,train=36,validation=12,step=6,embargo=1,mode='rolling',holdout_fraction=.2):
    """Indices are half-open. One-month labels; embargo between train/validation/test."""
    if mode not in ('rolling','expanding') or min(train,validation,step)<2 or embargo<0 or not 0<holdout_fraction<.5:raise ValueError('Invalid fold settings')
    first=train+validation+2*embargo;holdout=n-max(6,int(np.ceil(n*holdout_fraction)))
    if first>=holdout or n-holdout<2:raise ValueError('Insufficient history for development and final holdout')
    out=[]
    for a,b,phase in ((first,holdout,'development'),(holdout,n,'locked_holdout')):
        for d in range(a,b,step):
            ve=d-embargo;vs=ve-validation;te=vs-embargo;ts=0 if mode=='expanding' else te-train
            out.append(Fold(ts,te,vs,ve,d,min(d+step,b),phase))
    return out,holdout


def feasible_weights(w,upper,signed=False):
    w=np.asarray(w,float);u=np.asarray(upper,float)
    if w.shape!=u.shape or not np.isfinite(w).all() or (not signed and np.any(w< -1e-8)) or np.any(abs(w)>u+1e-7) or w.sum()>1+1e-7 or signed and abs(w).sum()>1.5+1e-7:raise ValueError('Target violates funded exposure bounds')
    return w if signed else np.maximum(w,0)


def execute(h,w,cost_rate,signed=False):
    """Cash is separate and not charged a commission. Solve V+c|Vw-h|=NAV."""
    nav=float(h.sum());w=np.asarray(w,float)
    if nav<=0 or not 0<=cost_rate<=.04 or not np.isclose(w.sum(),1,atol=1e-8) or (not signed and np.any(w<0)) or w[-1]< -1e-8:raise ValueError('Invalid funded trade')
    lo,hi=0.,nav
    for _ in range(55):
        v=(lo+hi)/2
        if v+cost_rate*np.abs(v*w[:-1]-h[:-1]).sum()>nav:hi=v
        else:lo=v
    v=(lo+hi)/2;new=v*w;delta=new[:-1]-h[:-1];fee=float(cost_rate*np.abs(delta).sum())
    if not np.isclose(new.sum()+fee,nav,rtol=1e-10,atol=1e-7):raise ArithmeticError('Trade not self financing')
    return new,delta,fee


def ledger(x,rf,intervals,targets,upper,*,capital=100.,cost_bps=10.,delay=1,turnover_limit=1.,max_trade_notional=None,signed=False,borrow_bps=300.,funding_bps=200.):
    """Decision index→target; execution only after delay full intervals. Cash accrues RF.

    No price/quantity claims: holdings represent total-return notional accounts.
    """
    x=np.asarray(x,float);rf=np.asarray(rf,float);upper=np.asarray(upper,float);n,k=x.shape
    if n<2 or rf.shape!=(n,) or upper.shape!=(n,k) or len(intervals)!=n or not np.isfinite(x).all() or not np.isfinite(rf).all() or np.any(x< -1) or np.any(rf< -1) or not 0<=cost_bps<=400 or not 0<=delay<=3 or not 0<=turnover_limit<=1 or capital<=0:raise ValueError('Invalid ledger inputs')
    if any(a>=b or i and a!=intervals[i-1][1] for i,(a,b) in enumerate(intervals)):raise ValueError('Noncontiguous interval ledger')
    h=np.r_[np.zeros(k),float(capital)];rows=[];trades=[];returns=[];rate=cost_bps/10000
    for i,(a,b) in enumerate(intervals):
        opening=float(h.sum());decision=i-delay;target=targets.get(decision);fee=0.;delta=np.zeros(k);reason=None;forced=False
        if opening<=0:return {'status':'unavailable','reason':'Portfolio exhausted','completed':i}
        drift=h/opening
        # Dated eligibility may force exits; cap drift is enforced only at trade dates.
        forced=bool(np.any((upper[i]==0)&(abs(h[:-1])>1e-8)))
        if target is not None:
            target=np.asarray(target,float).copy();dropped=int(np.sum((upper[i]==0)&(abs(target)>1e-8)));target[upper[i]==0]=0.
            try:w=feasible_weights(target,upper[i],signed)
            except ValueError:return {'status':'unavailable','reason':'Delayed target infeasible at execution date','date':str(a),'completed':i}
            w=np.r_[w,max(0.,1-w.sum())];reason='scheduled_dropped_ineligible_to_cash' if dropped else 'scheduled'
        elif forced:
            w=drift.copy();w[-1]+=w[:-1][upper[i]==0].sum();w[:-1][upper[i]==0]=0.;reason='forced_eligibility_exit'
        else:w=None
        if w is not None:
            try:new,delta,fee=execute(h,w,rate,signed)
            except ValueError as e:return {'status':'unavailable','reason':str(e),'date':str(a),'completed':i}
            notional=float(np.abs(delta).sum());turn=notional/(2*opening)
            if i>0 and turn>turnover_limit+1e-9:return {'status':'unavailable','reason':'Executed turnover cap exceeded','date':str(a),'completed':i}
            if max_trade_notional is not None and notional>max_trade_notional+1e-8:return {'status':'unavailable','reason':'Illustrative trade-notional capacity exceeded','date':str(a),'completed':i}
            h=new;trades.append({'decision_date':str(intervals[decision][0]) if target is not None else None,'execution_date':str(a),'reason':reason,'absolute_notional':notional,'fees':fee,'delta':delta.tolist(),'target':w.tolist()})
        after_fill=float(h.sum());short=float(-np.minimum(h[:-1],0).sum());free=float(h[-1]-short);borrow=short*borrow_bps/120000 if signed else 0.;funding=max(-free,0)*(max(rf[i],0)+funding_bps/120000) if signed else 0.;interest=max(free,0)*rf[i] if signed else h[-1]*rf[i];pnl=float(h[:-1]@x[i]+interest-borrow-funding);h[:-1]*=1+x[i];h[-1]+=interest-borrow-funding;end=float(h.sum())
        if not np.isclose(end,opening-fee+pnl,atol=1e-7,rtol=1e-10):raise ArithmeticError('NAV reconciliation failed')
        if end<0:return {'status':'unavailable','reason':'Negative NAV','completed':i}
        returns.append(end/opening-1);rows.append({'start':str(a),'end':str(b),'opening_nav':opening,'post_fill_nav':after_fill,'nav':end,'asset_value':float(h[:-1].sum()),'cash':float(h[-1]),'pnl':pnl,'fee':fee,'borrow':borrow,'funding':funding,'gross_exposure':float(np.abs(h[:-1]).sum()/end) if end>0 else None,'turnover':float(np.abs(delta).sum()/(2*opening)),'return':returns[-1],'weights':(h/end).tolist() if end>0 else [0.]*(k+1),'trade_reason':reason})
    return {'status':'computed','returns':np.asarray(returns),'ledger':rows,'trades':trades,'total_cost':sum(q['fee'] for q in rows),'borrow_cost':sum(q['borrow'] for q in rows),'funding_cost':sum(q['funding'] for q in rows),'annual_turnover':sum(q['turnover'] for q in rows[1:])*12/n,'final_nav':rows[-1]['nav']}


def summarize(sim,rf,benchmark):
    if sim['status']!='computed':return sim
    r=sim['returns'];m=metrics(r,rf);s=stats(r,benchmark=benchmark);return {'status':'computed','net':m,'active':{k:s[k] for k in ('tracking_error','information_ratio','active_annual_mean','sortino','omega')},'nav':np.cumprod(1+r).tolist(),'returns':r.tolist(),'fees':sim['total_cost'],'borrow_cost':sim.get('borrow_cost',0.),'funding_cost':sim.get('funding_cost',0.),'annual_turnover':sim['annual_turnover'],'final_nav':sim['final_nav']}


def bootstrap_comparison(rows,benchmark,seed=23,draws=500,block=3):
    """Joint moving-block resampling of aligned net excess returns.

    Center each candidate null and compare max statistic across all computed
    candidates; exploratory reality-check-style diagnostic, not formal approval.
    """
    keys=list(rows);b=np.asarray(benchmark,float);n=len(b)
    if n<6 or not keys:return {'status':'unavailable','reason':'Too few matched observations'}
    x=np.array([np.asarray(rows[k])-b for k in keys]).T;mean=x.mean(0);rng=np.random.default_rng(seed);ix=(rng.integers(0,n-block+1,(draws,(n+block-1)//block,1))+np.arange(block)).reshape(draws,-1)[:,:n];raw=x[ix].mean(1)*12;null=(x-mean)[ix].mean(1)*12;maximum=null.max(1)
    return {'status':'exploratory','seed':seed,'draws':draws,'block':block,'tested_models':len(keys),'max_statistic_p':float((1+np.sum(maximum>=mean.max()*12))/(draws+1)),'intervals':{k:[float(v) for v in np.quantile(raw[:,j],[.025,.975])] for j,k in enumerate(keys)},'warning':'Small sample, dependent strategy trials and retrospective cohort; centered block max statistic is exploratory, not a formal definitive reality check or deflated Sharpe.'}
