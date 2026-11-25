"""Research-only signed portfolios. All exposures are fractions of NAV."""
import numpy as np
from scipy.optimize import linprog
from statsmodels.tsa.stattools import coint, adfuller

VERSION = 'alternative-v1'
REGISTRY = {
    'long_short': 'Top and bottom 12–1 month momentum ranks',
    'market_neutral': 'Dollar and rolling beta neutral rank portfolio',
    'global_macro': 'Growth, inflation and cash-rate vintage proxy',
    'cta_etf_proxy': '12-month trend, inverse-volatility ETF proxy (not futures)',
    'managed_futures': 'Dated futures execution, roll and margin',
    'statistical_arbitrage': 'Train-selected cointegrated total-return spread',
    'carry': 'Instrument-level forward/roll carry',
    'cross_sectional_momentum': 'Long-only 12–1 month winners',
    'time_series_momentum': 'Positive 12-month ETF trends',
    'mean_reversion': 'Three-month return z-score with stop and exit',
    'tactical_allocation': 'Bounded 60/40 tilt',
    'volatility_target': '60/40 with 10% annual volatility target, no leverage',
    'all_weather': 'Four ETF regime proxy, inverse volatility',
    'multi_strategy': 'Inverse-volatility budgets across three aggregated long-only sleeves (not exact ERC)',
    'regime_switching': 'Forward-filtered two-state volatility signal',
    'tail_hedge_proxy': 'Conditional defensive ETF allocation, not derivative hedge',
    'tail_hedging': 'Conditional futures hedge with actual margin and costs',
}


def capped(raw, upper, budget=1.):
    raw=np.maximum(np.asarray(raw,float),0); upper=np.asarray(upper,float); w=np.zeros_like(raw)
    if budget<=0:return w
    if upper[raw>0].sum()<budget-1e-9:raise ValueError('Insufficient eligible capacity')
    for _ in range(len(raw)+1):
        active=(raw>0)&(upper-w>1e-12); rem=budget-w.sum()
        if rem<1e-10:return w
        if not active.any():raise ValueError('Insufficient capacity')
        w[active]+=np.minimum(upper[active]-w[active],rem*raw[active]/raw[active].sum())
    return w


def rank_signal(h):
    return np.prod(1+h[-12:-1],axis=0)-1


def beta(h,b):
    v=np.var(b,ddof=1)
    return (h-h.mean(0)).T@(b-b.mean())/((len(b)-1)*v) if v>1e-12 else np.zeros(h.shape[1])


def signed_rank(score, upper, betas=None):
    eligible=np.flatnonzero(upper>0); order=eligible[np.argsort(score[eligible],kind='stable')]; k=max(1,len(order)//3)
    if len(order)<4:raise ValueError('Need at least four eligible assets')
    low,high=order[:k],order[-k:]; budget=min(.5,upper[low].sum(),upper[high].sum())
    if budget<=0:raise ValueError('Insufficient signed capacity')
    if betas is None:
        return capped(np.isin(np.arange(len(score)),high),upper,budget)-capped(np.isin(np.arange(len(score)),low),upper,budget)
    ix=np.r_[high,low]; sign=np.r_[np.ones(k),-np.ones(k)]
    res=linprog(-score[ix]*sign,A_eq=np.array([sign,sign*betas[ix],np.ones(len(ix))]),b_eq=[0,0,2*budget],bounds=[(0,upper[i]) for i in ix],method='highs')
    if not res.success:raise ValueError('Beta/dollar neutral rank constraints infeasible')
    w=np.zeros(len(score));w[ix]=res.x*sign;return w


def select_pair(h, indices):
    """Fixed training-only pair; Bonferroni control across candidates."""
    p=np.log(np.maximum(np.cumprod(1+h,axis=0),1e-12));pairs=[]
    for j,i in enumerate(indices):
        for k in indices[j+1:]:
            if np.std(p[:,i])<1e-8 or np.std(p[:,k])<1e-8:continue
            _,pv,_=coint(p[:,i],p[:,k]); slope,intercept=np.polyfit(p[:,k],p[:,i],1)
            if np.isfinite(pv) and slope>0:pairs.append((pv,i,k,slope,intercept))
    if not pairs:return None
    best=min(pairs);return best if best[0]<.05/max(1,len(indices)*(len(indices)-1)/2) else None


def pair_target(h,pair,u):
    if pair is None:raise ValueError('No training pair passes multiple-testing threshold')
    _,i,j,b,a=pair; p=np.log(np.maximum(np.cumprod(1+h,axis=0),1e-12));s=p[:,i]-b*p[:,j]-a;w=np.zeros(len(u));window=s[-36:]
    if len(window)<36 or np.std(window)<1e-9 or adfuller(window,autolag='AIC')[1]>.1:return w
    z=(s[-1]-window[:-1].mean())/window[:-1].std(ddof=1)
    if 2<=abs(z)<4:
        size=min(.5,u[i],u[j]/b);w[i]=-np.sign(z)*size;w[j]=np.sign(z)*size*b
    return w


def filtered_probability(h):
    """Fixed two-state Gaussian HMM filter with training-independent parameters."""
    p=np.array([.8,.2]); trans=np.array([[.95,.05],[.2,.8]])
    for r in h:
        sd=np.array([.035,.09]); loglike=-.5*(r/sd)**2-np.log(sd);likelihood=np.exp(loglike-loglike.max())
        p=(p@trans)*likelihood;p/=p.sum()
    return float(p[1])


def ledger(x,rf,targets,*,cost_bps=10.,borrow_bps=300.,funding_bps=200.,turnover_limit=1.):
    """Self-financing signed holdings and collateral; short proceeds earn zero.

    Solve post-fee NAV before trading; actual short availability is unspecified.
    Cash interest only on positive unencumbered collateral. No intramonth margin model.
    """
    x=np.asarray(x,float);rf=np.asarray(rf,float);targets=np.asarray(targets,float)
    if x.shape!=targets.shape or len(rf)!=len(x) or not np.isfinite(x).all() or not np.isfinite(targets).all() or not np.isfinite(rf).all() or np.any(x< -1) or not 0<=cost_bps<=200 or not 0<=borrow_bps<=5000 or not 0<=funding_bps<=5000 or not 0<=turnover_limit<=2:raise ValueError('Invalid ledger inputs')
    holdings=np.zeros(x.shape[1]);nav=100.;rows=[];returns=[];c=cost_bps/10000
    for t,(r,w,rate) in enumerate(zip(x,targets,rf)):
        if np.abs(w).sum()>1.5+1e-8 or w.sum()>1+1e-8 or np.max(np.abs(w))>1+1e-8:raise ValueError('Exposure exceeds research collateral bounds')
        lo,hi=0.,nav
        for _ in range(60):
            v=(lo+hi)/2
            if v+c*np.abs(v*w-holdings).sum()>nav:hi=v
            else:lo=v
        v=(lo+hi)/2;h=v*w;notional=float(np.abs(h-holdings).sum());fee=c*notional;turn=notional/(2*nav)
        if not np.isclose(v+fee,nav,rtol=1e-9,atol=1e-8):return {'status':'unavailable','reason':'Insufficient NAV for trading costs','completed_months':t}
        if t and turn>turnover_limit+1e-9:return {'status':'unavailable','reason':'Actual turnover cap exceeded','completed_months':t}
        short=float(-h[h<0].sum());long=float(h[h>0].sum());cash=v-h.sum();free=cash-short;interest=max(free,0)*rate;fund=max(-free,0)*(max(rate,0)+funding_bps/120000);borrow=short*borrow_bps/120000
        holdings=h*(1+r);end=float(holdings.sum()+cash+interest-fund-borrow)
        if end<=0:return {'status':'unavailable','reason':'Capital exhausted','completed_months':t}
        returns.append(end/nav-1);rows.append({'nav':end,'gross':float(np.abs(w).sum()),'net':float(w.sum()),'fee':fee,'borrow':borrow,'funding':fund,'interest':interest,'turnover':turn,'collateral':float(cash),'free_cash':float(free)});nav=end
    return {'status':'computed','returns':np.array(returns),'ledger':rows}
