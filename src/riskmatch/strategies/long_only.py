"""Dated passive and long-only strategy signals with drift-aware turnover control."""
import numpy as np
from riskmatch.optimization.hierarchical import proportional_cap
from riskmatch.backtesting.baselines import trade,metrics

VERSION='long-only-v2'
FACTORS=('size','value','momentum','low_volatility','liquidity','quality','profitability_proxy','investment')
REGISTRY={
 'passive_index':{'signal':'none','estimate':'SPY index ETF','allocation':'full ETF replication proxy','benchmark':'SPY','exit':'eligibility/cap infeasible'},
 'passive_etfs':{'signal':'none','estimate':'eligible index ETFs','allocation':'capped equal ETF weights','benchmark':'SPY','exit':'eligibility'},
 'active_long_only':{'signal':'rolling 36-month alpha vs SPY','estimate':'prior returns OLS intercept','allocation':'top positive ranks','benchmark':'SPY','exit':'rank exit subject to turnover'},
 'smart_beta_equal':{'signal':'none','estimate':'dated eligible universe','allocation':'1/N','benchmark':'SPY','exit':'eligibility'},
 'smart_beta_factor':{'signal':'mean of available standardized factor scores','estimate':'dated score artifact','allocation':'top ranks','benchmark':'SPY','exit':'rank exit subject to turnover'},
 'smart_beta_fundamental':{'signal':'positive book equity','estimate':'accepted original filings','allocation':'capped proportional book equity','benchmark':'SPY','exit':'missing/stale filing target zero'},
 'factor_investing':{'signal':'eight factor sleeves','estimate':'dated standardized scores','allocation':'equal sleeve budgets, aggregate cap','benchmark':'SPY','exit':'rank exit subject to turnover'},
 'core_satellite':{'signal':'passive ETF core and active alpha satellite','estimate':'prior returns','allocation':'fixed core/satellite budgets','benchmark':'SPY','exit':'eligibility/rank'},
 **{f'factor_{k}':{'signal':k,'estimate':'dated standardized factor score','allocation':'top ranks','benchmark':'SPY','exit':'rank exit subject to turnover'} for k in FACTORS}}


def allocate(raw,upper):
    raw=np.asarray(raw,float);u=np.asarray(upper,float);active=(raw>0)&(u>0)
    if not np.any(active) or u[active].sum()<1-1e-10:raise ValueError('Insufficient supported target capacity')
    w=np.zeros(len(u));w[active],_=proportional_cap(raw[active]/raw[active].sum(),u[active]);return w


def ranked(score,upper,ids,quantile=.3,positive_only=False,fallback=True):
    s=np.asarray(score,float);u=np.asarray(upper,float);valid=np.flatnonzero(np.isfinite(s)&(u>0)&((s>0) if positive_only else True));
    if not len(valid) or np.ptp(s[valid])<1e-12:
        if not fallback:raise ValueError('Flat or missing factor signal')
        return allocate((u>0).astype(float),u),{'valid_scores':len(valid),'fallback':'flat_or_missing_signal_capped_equal'}
    order=valid[np.lexsort((np.asarray(ids)[valid],-s[valid]))];k=max(1,int(np.ceil(len(order)*quantile)))
    while k<len(order) and u[order[:k]].sum()<1-1e-10:k+=1
    if u[order[:k]].sum()<1-1e-10:
        if not fallback:raise ValueError('Insufficient scored factor capacity')
        return allocate((u>0).astype(float),u),{'valid_scores':len(valid),'fallback':'positive_signal_capacity_insufficient_capped_equal'}
    raw=np.zeros(len(u));raw[order[:k]]=np.arange(k,0,-1);return allocate(raw,u),{'valid_scores':len(valid),'selected_scores':k,'fallback':None}


def cap_turnover(previous,target,upper,limit):
    """Minimal forced exit projection then feasible interpolation toward target."""
    p=np.asarray(previous,float);t=np.asarray(target,float);u=np.asarray(upper,float)
    if limit<0 or u.sum()<1-1e-10 or abs(t.sum()-1)>1e-7 or np.any(t>u+1e-8):raise ValueError('Invalid target or turnover cap')
    base=np.minimum(p,u);missing=1-base.sum();room=u-base
    if missing>1e-12:base+=missing*room/room.sum()
    forced=float(np.abs(base-p).sum()/2)
    if forced>limit+1e-9:return None,forced
    if np.abs(t-p).sum()/2<=limit+1e-10:return t,forced
    lo,hi=0.,1.
    for _ in range(60):
        mid=(lo+hi)/2;w=(1-mid)*base+mid*t
        if np.abs(w-p).sum()/2>limit:hi=mid
        else:lo=mid
    return (1-lo)*base+lo*t,forced


def alpha_signal(history,benchmark):
    x=np.asarray(history,float);b=np.asarray(benchmark,float);var=float(np.var(b,ddof=1));beta=(x-x.mean(0)).T@(b-b.mean())/((len(b)-1)*var) if var>1e-12 else np.zeros(x.shape[1]);return 12*(x.mean(0)-beta*b.mean())


def dynamic_ledger(x,intervals,targets,caps,cost_bps,turnover_limit,frequency='monthly'):
    """Target selected before interval start; drift, then trade at start before return."""
    x=np.asarray(x,float)
    if x.ndim!=2 or len(x)!=len(intervals) or len(targets)!=len(x) or len(caps)!=len(x) or not np.isfinite(x).all() or np.any(x< -1) or not 0<=cost_bps<=200 or not 0<=turnover_limit<=1 or frequency not in ('monthly','quarterly') or any(a>=b or i and a!=intervals[i-1][1] for i,(a,b) in enumerate(intervals)):raise ValueError('Invalid dynamic ledger inputs')
    n=x.shape[1];h=np.zeros(n);capital=100.;previous=100.;fees=0.;rows=[];net=[];weights=[];rate=cost_bps/10000
    for i,(r,(a,b),t,u) in enumerate(zip(x,intervals,targets,caps)):
        if t is None:return {'status':'unavailable','reason':'Target unavailable','date':str(a),'completed_months':i}
        rebalance=i==0 or frequency=='monthly' or a.month%3==0;forced=0.
        if i==0:target=t;h,delta,fee,notional=trade(h,target,capital,rate);turnover=None
        else:
            drift=h/h.sum();must=np.any(drift>u+1e-9);desired=t if rebalance else drift
            if rebalance or must:
                if not rebalance:desired=allocate(np.maximum(np.minimum(drift,u),1e-12)*(u>0),u)
                target,forced=cap_turnover(drift,desired,u,turnover_limit)
                if target is None:return {'status':'infeasible','reason':'Forced eligibility/cap exits exceed turnover limit','date':str(a),'forced_turnover':forced,'completed_months':i}
                before=float(h.sum());new,delta,fee,notional=trade(h,target,0.,rate);turnover=notional/(2*before)
                if turnover>turnover_limit+1e-10:
                    # Fees change executable notional slightly; enforce actual traded amount too.
                    base,_=cap_turnover(drift,desired,u,forced+1e-12);trial=trade(h,base,0.,rate)
                    if trial[3]/(2*before)>turnover_limit+1e-10:return {'status':'infeasible','reason':'Fee-adjusted forced exits exceed turnover limit','date':str(a),'forced_turnover':trial[3]/(2*before),'completed_months':i}
                    lo,hi=0.,1.;candidate=target
                    for _ in range(50):
                        mid=(lo+hi)/2;q=(1-mid)*base+mid*candidate;res=trade(h,q,0.,rate)
                        if res[3]/(2*before)>turnover_limit:hi=mid
                        else:lo=mid
                    target=(1-lo)*base+lo*candidate;new,delta,fee,notional=trade(h,target,0.,rate);turnover=notional/(2*before)
                h=new
            else:fee=notional=0.;target=drift;turnover=0.
        if not np.isclose(target.sum(),1,atol=1e-7) or np.any(target>u+1e-7):raise ArithmeticError('Executed target violates cap')
        weights.append(target.copy());h*=1+r;nav=float(h.sum());net.append(nav/previous-1);fees+=fee;rows.append({'start':str(a),'end':str(b),'nav':nav,'fees':fee,'turnover':turnover,'forced_turnover':forced,'traded_notional':notional,'max_weight':float(target.max()),'rebalance':bool(rebalance or (i>0 and must))});previous=nav
    return {'status':'computed','returns':np.array(net),'weights':np.array(weights),'ledger':rows,'fees':fees,'annual_turnover':float(sum(r['turnover'] or 0 for r in rows)*12/len(rows))}
