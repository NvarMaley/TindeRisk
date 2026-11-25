"""Long-only fixed-weight benchmark ledger with explicit close-to-close timing."""
from datetime import date
import numpy as np
from riskmatch.analytics.tail_risk import empirical

VERSION='baseline-v1'


def weights_checked(weights):
    w=np.asarray(weights,float)
    if w.ndim!=1 or len(w)==0 or not np.isfinite(w).all() or np.any(w<0) or not np.isclose(w.sum(),1,atol=1e-10,rtol=0):raise ValueError('Require finite long-only funded weights summing to one')
    return w/w.sum()


def trade(holdings,target,flow,cost_rate):
    """Self-financing target after flow and proportional fee on absolute trade notional."""
    h=np.asarray(holdings,float);w=weights_checked(target);available=float(h.sum()+flow)
    if h.shape!=w.shape or not np.isfinite(h).all() or np.any(h<0) or not np.isfinite([flow,cost_rate]).all() or not 0<=cost_rate<=.02 or available<0:raise ValueError('Invalid or unfunded trade')
    # Solve v + c*sum(|v*w-h|) = available; monotone because c < 1.
    if available+1e-10<cost_rate*h.sum():raise ValueError('Withdrawal cannot cover liquidation fees')
    lo,hi=0.,available
    for _ in range(65):
        mid=(lo+hi)/2
        if mid+cost_rate*np.abs(mid*w-h).sum()>available:hi=mid
        else:lo=mid
    v=(lo+hi)/2;after=v*w;delta=after-h;turnover=float(np.abs(delta).sum());fee=cost_rate*turnover
    if not np.isclose(after.sum()+fee,available,rtol=1e-10,atol=1e-8):raise ArithmeticError('Trade ledger does not reconcile')
    return after,delta,fee,turnover


def simulate(returns,intervals,weights,*,frequency='monthly',capital=100.,cost_bps=0.,flows=None):
    """Initial buy at first interval start, returns then close valuation and trades.

    External flows at interval ends; deposit/withdrawal invested pro-rata when no
    scheduled rebalance. Last close is marked, not liquidated or gratuitously rebalanced.
    Returns are time weighted, stripping end-of-period external flows.
    """
    x=np.asarray(returns,float);w=weights_checked(weights)
    if x.ndim!=2 or x.shape!=(len(intervals),len(w)) or len(x)==0 or not np.isfinite(x).all() or np.any(x< -1):raise ValueError('Invalid return matrix')
    if frequency not in ('monthly','quarterly','buy_hold') or not np.isfinite([capital,cost_bps]).all() or capital<=0 or not 0<=cost_bps<=200:raise ValueError('Invalid benchmark settings')
    if any(a>=b or (i and a!=intervals[i-1][1]) for i,(a,b) in enumerate(intervals)):raise ValueError('Require strictly ordered contiguous intervals')
    f=np.zeros(len(x)) if flows is None else np.asarray(flows,float)
    if f.shape!=(len(x),) or not np.isfinite(f).all():raise ValueError('Invalid flows')
    rate=cost_bps/10000
    h,delta,fee,turnover=trade(np.zeros(len(w)),w,capital,rate)
    initial={'date':str(intervals[0][0]),'starting_capital':float(capital),'nav':float(h.sum()),'fees':fee,'traded_notional':turnover,'trade':delta.tolist(),'weights':w.tolist()}
    ledger=[];prev=float(capital);wealth=1.;twr=[]
    for i,(row,(start,end),flow) in enumerate(zip(x,intervals,f)):
        if prev<=0 or h.sum()<=0:raise ValueError('Portfolio exhausted')
        opening=h.copy();h*=1+row;before=float(h.sum());drift=h/before if before else np.zeros(len(w));rebalance=i<len(x)-1 and (frequency=='monthly' or frequency=='quarterly' and end.month%3==0)
        fee=notional=0.;delta=np.zeros(len(w))
        if rebalance or flow!=0:
            if before<=0:raise ValueError('Portfolio exhausted before trade')
            h,delta,fee,notional=trade(h,w if rebalance else drift,float(flow),rate)
        after=float(h.sum());period=(after-float(flow))/prev-1
        if period< -1-1e-10:raise ValueError('Flow-adjusted return below total loss')
        wealth*=1+period;twr.append(period)
        ledger.append({'start':str(start),'end':str(end),'opening_nav':float(opening.sum()),'pre_trade_nav':before,'flow':float(flow),'net_nav':after,'fee':fee,'traded_notional':notional,'one_way_turnover':notional/(2*before) if before else 0.,'trade':delta.tolist(),'opening_weights':(opening/opening.sum()).tolist(),'drift_weights':drift.tolist(),'closing_weights':(h/after).tolist() if after else [0.]*len(w),'rebalance':rebalance,'return':period,'twr_index':wealth})
        if not np.isclose(after,before+flow-fee,atol=1e-8,rtol=1e-10):raise ArithmeticError('NAV does not reconcile')
        prev=after
    return {'frequency':frequency,'initial':initial,'ledger':ledger,'returns':twr,'final_nav':prev,'final_weights':ledger[-1]['closing_weights'],'total_fees':initial['fees']+sum(v['fee'] for v in ledger),'total_traded_notional':initial['traded_notional']+sum(v['traded_notional'] for v in ledger),'annual_one_way_turnover':sum(v['one_way_turnover'] for v in ledger)*12/len(x)}


def metrics(returns,reference):
    r=np.asarray(returns,float);rf=np.asarray(reference,float)
    if r.ndim!=1 or len(r)<2 or r.shape!=rf.shape or not np.isfinite(r).all() or not np.isfinite(rf).all() or np.any(r< -1):raise ValueError('Invalid metrics inputs')
    nav=np.r_[1.,np.cumprod(1+r)];dd=nav/np.maximum.accumulate(nav)-1;vol=float(np.std(r,ddof=1)*np.sqrt(12));excess=r-rf;s=float(np.std(excess,ddof=1));rolling=[float(np.prod(1+r[i:i+12])-1) for i in range(len(r)-11)]
    return {'cumulative':float(nav[-1]-1),'cagr':float(nav[-1]**(12/len(r))-1),'annual_volatility':vol,'max_drawdown':float(-dd.min()),'annual_excess_ratio':float(excess.mean()/s*np.sqrt(12)) if s>1e-12 else None,'worst_month':float(r.min()),'worst_12_months':min(rolling) if rolling else None,'monthly_es95':empirical(-r,.95)['es'] if len(r)>=100 else None,'drawdown':dd[1:].tolist()}
