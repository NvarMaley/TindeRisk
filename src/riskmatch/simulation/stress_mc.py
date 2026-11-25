"""Conditional correlated paths and self-financing wealth projection (monthly)."""
import numpy as np
from scipy.special import ndtr,ndtri
from scipy.stats import rankdata
from sklearn.covariance import LedoitWolf

VERSION='stress-mc-v2'
MODELS=('normal','student_t','block_bootstrap','regime','gaussian_copula')
PERCENTILES=(5,25,50,75,95)


def covariance_model(x):
    x=np.asarray(x,float);m=x.mean(0);d=x-m;n=len(x)
    # Shrink standardized covariance, then restore original marginal variances.
    # This avoids injecting equity-sized noise into low-volatility cash.
    sd=np.sqrt(np.sum(d*d,axis=0)/n);z=np.divide(d,sd,out=np.zeros_like(d),where=sd>1e-12);lw=LedoitWolf().fit(z);shrink=float(lw.shrinkage_);factor=d*np.sqrt((1-shrink)/n);noise=sd*np.sqrt(max(0,shrink));cov=factor.T@factor+np.diag(noise**2);return m,factor,noise,cov


def paths(x,months,count,model,seed=24,market=None,mean_shift=0.,vol_scale=1.,regime_stress=1.,df=5,block=6):
    """Yield monthly paths and diagnostic clipping counts. Joint asset + cash history.

    All calibrations are from supplied history only. Low-rank LW representation
    avoids a dense per-path factor multiplication on a wide universe.
    """
    x=np.asarray(x,float)
    if model not in MODELS or x.ndim!=2 or len(x)<max(12,block) or not np.isfinite(x).all() or np.any(x< -1) or months<1 or count<1 or df<=2 or vol_scale<=0 or regime_stress<=0:raise ValueError('Invalid path calibration')
    rng=np.random.default_rng(seed);n,d=x.shape;m,f,noise,cov=covariance_model(x);last=None
    def gaussian(f,noise):return rng.standard_normal((count,len(f)))@f+rng.standard_normal((count,d))*noise
    if model=='block_bootstrap':
        starts=rng.integers(0,n-block+1,(count,(months+block-1)//block));ix=(starts[:,:,None]+np.arange(block)).reshape(count,-1)[:,:months]
    if model=='regime':
        b=np.asarray(market if market is not None else x[:,0],float);state=(b<np.quantile(b,.30)).astype(int);trans=np.ones((2,2))
        for a,c in zip(state[:-1],state[1:]):trans[a,c]+=1
        trans[:,1]*=regime_stress;trans/=trans.sum(1,keepdims=True);last=np.full(count,state[-1],int);fits=[covariance_model(x[state==s] if np.sum(state==s)>=2 else x) for s in (0,1)]
    if model=='gaussian_copula':
        latent=ndtri((rankdata(x,axis=0)-.5)/n);_,lf,ln,lc=covariance_model(latent);sd=np.sqrt(np.maximum(np.diag(lc),1e-12));ordered=np.sort(x,axis=0)
    for t in range(months):
        if model=='normal':r=m+gaussian(f,noise)
        elif model=='student_t':r=m+gaussian(f,noise)*np.sqrt((df-2)/rng.chisquare(df,count))[:,None]
        elif model=='block_bootstrap':r=x[ix[:,t]].copy()
        elif model=='regime':
            last=(rng.random(count)<trans[last,1]).astype(int);r=np.empty((count,d))
            for state in (0,1):
                sm,sf,sn,_=fits[state];part=last==state;j=int(part.sum());r[part]=sm+rng.standard_normal((j,len(sf)))@sf+rng.standard_normal((j,d))*sn
        else:
            q=ndtr(gaussian(lf,ln)/sd);indices=np.minimum(n-1,(q*n).astype(int));r=np.take_along_axis(ordered,indices,axis=0)
        # Shift only risk assets; cash mean untouched. Floor prevents impossible simple returns.
        r=m+(r-m)*vol_scale;r[:,:-1]+=mean_shift/12;clipped=int((r<-.999999).sum());r=np.maximum(r,-.999999);yield r,clipped


def rebalance(h,w,rate):
    """Simultaneous fee-adjusted target excluding cash from transaction fees."""
    nav=h.sum(1)
    if rate==0:return np.maximum(nav,0)[:,None]*w,np.zeros(len(h))
    lo=np.zeros(len(h));hi=np.maximum(nav,0)
    for _ in range(42):
        v=(lo+hi)/2;fee=rate*np.abs(v[:,None]*w[:-1]-h[:,:-1]).sum(1);test=v+fee>nav;hi=np.where(test,v,hi);lo=np.where(test,lo,v)
    v=(lo+hi)/2;new=v[:,None]*w;fee=rate*np.abs(new[:,:-1]-h[:,:-1]).sum(1)
    if not np.allclose(new.sum(1)+fee,np.maximum(nav,0),atol=1e-5,rtol=1e-9):raise ArithmeticError('Monte Carlo trade reconciliation failed')
    return new,fee


def pay(h,amount,rate):
    """Proportional liquidation funds obligation; no borrowing of missing payment."""
    free=np.maximum(h[:,-1]+np.minimum(h[:,:-1],0).sum(1),0);cash_paid=np.minimum(free,amount);h[:,-1]-=cash_paid;remaining=amount-cash_paid;nav=np.maximum(h.sum(1),0);tradable=np.abs(h[:,:-1]).sum(1);available=np.maximum(nav-rate*tradable,0);paid=np.minimum(available,remaining);fraction=np.divide(paid,available,out=np.zeros_like(paid),where=available>0);fee=rate*tradable*fraction;h*=1-fraction[:,None];return h,remaining-paid,fee


def interval(p,n):
    # Wilson interval: Monte Carlo sampling error only, not model uncertainty.
    z=1.95996398454;den=1+z*z/n;centre=(p+z*z/(2*n))/den;half=z*np.sqrt(p*(1-p)/n+z*z/(4*n*n))/den;return [float(max(0,centre-half)),float(min(1,centre+half))]


def project(generator,w,capital,months,count,events,goals,*,inflation=.02,cost_bps=10.,frequency=3,borrow_bps=300.,funding_bps=200.,fractions=None):
    """Start cash; monthly rebalancing, dated events within each month, no borrowing for goals.

    events[m] = [(fraction, kind, amount)], goals[m] similarly with index and funding.
    Signed targets permitted only for standalone research; collateral and fees are hypothetical.
    """
    w=np.asarray(w,float);cash=1-w.sum();signed=bool((w<0).any());full=np.r_[w,cash]
    if not np.isfinite(w).all() or cash< -1e-8 or np.abs(w).sum()>1.5+1e-8 or capital<=0 or not 0<=cost_bps<=200 or frequency<1 or inflation<=-1:raise ValueError('Invalid projection inputs')
    h=np.zeros((count,len(full)));h[:,-1]=capital;rate=cost_bps/10000;fees=np.zeros(count);unmet=np.zeros(count);debt=np.zeros(count);dead=np.zeros(count,bool);fan=[np.full(5,capital).tolist()];real_fan=[fan[0]];goals_out={};clipped=0;total_borrow=np.zeros(count);total_funding=np.zeros(count);forced=np.zeros(count,bool);withdrawal_gap=np.zeros(count);joint=np.ones(count,bool);target_count=0
    fractions=np.ones(months) if fractions is None else np.asarray(fractions,float);elapsed=0.
    if fractions.shape!=(months,) or np.any(fractions<=0) or np.any(fractions>1):raise ValueError('Invalid horizon fractions')
    for i,(r,clips) in enumerate(generator):
        if i>=months or r.shape!=h.shape:raise ValueError('Path dimensions mismatch')
        clipped+=clips;duration=fractions[i];
        if i%frequency==0:
            h,fee=rebalance(h,full,rate);fees+=fee
        groups={}
        for frac,kind,amount in events.get(i,[]):groups.setdefault(frac,[]).append((kind,amount))
        for frac,g in goals.get(i,[]):groups.setdefault(frac,[]).append(('goal',g))
        groups.setdefault(duration,[]);previous=0.
        for frac,items in sorted(groups.items()):
            if not previous<=frac<=duration+1e-9:raise ValueError('Event outside modeled interval')
            period=frac-previous;previous=frac
            if period:
                short=-np.minimum(h[:,:-1],0).sum(1);free=h[:,-1]-short;borrow=short*borrow_bps/120000*period if signed else np.zeros(count);fund=np.maximum(-free,0)*(np.maximum(r[:,-1],0)+funding_bps/120000)*period if signed else np.zeros(count);interest=(np.maximum(free,0) if signed else h[:,-1])*np.expm1(np.log1p(r[:,-1])*period);h[:,:-1]*=np.exp(np.log1p(r[:,:-1])*period);h[:,-1]+=interest-borrow-fund;total_borrow+=borrow;total_funding+=fund
                nav=h.sum(1);insolvent=(nav<=0)&(np.abs(h[:,:-1]).sum(1)>0);debt[insolvent]+=np.maximum(-nav[insolvent],0);h[insolvent]=0;dead|=insolvent
                # Monthly/subevent gross guard, not clearing margin certification.
                if signed:
                    nav=h.sum(1);breach=(nav>0)&(np.abs(h[:,:-1]).sum(1)>1.5*nav);forced|=breach
                    if breach.any():
                        fee=rate*np.abs(h[breach,:-1]).sum(1);value=nav[breach]-fee;ix=np.flatnonzero(breach);bad=ix[value<0];debt[bad]+=-value[value<0];dead[bad]=True;h[breach]=0;h[breach,-1]=np.maximum(value,0);fees[breach]+=fee
            # Cash flow precedence: contributions, contractual withdrawals, then priority goals.
            contribution=sum(v for k,v in items if k=='contribution');h[:,-1]+=np.where(dead,0.,contribution)
            for kind in ('liability','withdrawal'):
                due=sum(v for k,v in items if k==kind)
                if due:
                    h,gap,fee=pay(h,due,rate);unmet+=gap;fees+=fee
                    if kind=='withdrawal':withdrawal_gap+=gap
            for g in sorted([v for k,v in items if k=='goal'],key=lambda v:(-v.get('priority',0),v['index'])):
                target=g['target'];nav=h.sum(1)
                if target is None:goals_out[g['index']]={'index':g['index'],'status':'preference_only','date':g['date']};continue
                if g['funding']:h,gap,fee=pay(h,target,rate);unmet+=gap;fees+=fee
                else:gap=np.maximum(target-nav,0)
                joint&=(gap<=1e-7);target_count+=1;probability=float(np.mean(gap<=1e-7));mean=float(gap.mean());se=float(gap.std(ddof=1)/np.sqrt(count)) if count>1 else 0.;goals_out[g['index']]={'index':g['index'],'date':g['date'],'target':target,'funding':g['funding'],'probability':probability,'probability_interval':interval(probability,count),'expected_deficit':mean,'deficit_sampling_interval':[max(0.,mean-1.96*se),mean+1.96*se],'conditional_deficit':float(gap[gap>1e-7].mean()) if np.any(gap>1e-7) else 0.}
        elapsed+=duration;nav=np.maximum(h.sum(1),0);fan.append(np.percentile(nav,PERCENTILES).tolist());real_fan.append(np.percentile(nav/(1+inflation)**(elapsed/12),PERCENTILES).tolist())
    terminal=nav;real=terminal/(1+inflation)**(elapsed/12);success=float(np.mean((unmet<=1e-7)&~dead));jp=float(np.mean(joint&(unmet<=1e-7)&~dead)) if target_count else None;return {'percentiles':fan[-1],'real_percentiles':real_fan[-1],'fan':fan,'real_fan':real_fan,'terminal_mean':float(terminal.mean()),'real_mean':float(real.mean()),'lower_5pct_mean_wealth':float(np.sort(terminal)[:max(1,int(np.ceil(.05*count)))].mean()),'goals':list(goals_out.values()),'all_targeted_goals_probability':jp,'all_targeted_goals_interval':interval(jp,count) if jp is not None else None,'all_funded_obligations_probability':success,'all_funded_obligations_interval':interval(success,count),'expected_unmet_cash':float(unmet.mean()),'expected_withdrawal_gap':float(withdrawal_gap.mean()),'insolvency_probability':float(dead.mean()),'expected_insolvency_debt':float(debt.mean()),'gross_guard_probability':float(forced.mean()),'mean_fees':float(fees.mean()),'mean_borrow':float(total_borrow.mean()),'mean_funding':float(total_funding.mean()),'clipped_asset_returns':clipped}
