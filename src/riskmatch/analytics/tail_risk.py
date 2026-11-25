"""Chapter 11: loss risk per observed period, never annualized."""
import numpy as np
from scipy import stats, special

VERSION = 'tail-v2'
LEVELS = (.95, .99)


def empirical(loss, alpha):
    x = np.asarray(loss,float)
    if x.ndim!=1 or not len(x) or not np.isfinite(x).all() or not 0<alpha<1:
        raise ValueError("Invalid loss sample or confidence")
    x = np.sort(x)[::-1]
    k = len(x)*(1-alpha)
    # Fractional mass at the boundary, including ties.
    weights = np.clip(k-np.arange(len(x)), 0, 1)
    return {'var': float(x[min(len(x)-1, len(x)-int(np.ceil(alpha*len(x))))]),
            'es': float(weights@x/k)}


def contributions(returns, weights, alpha=.95):
    x=np.asarray(returns,float); w=np.asarray(weights,float)
    if x.ndim!=2 or w.ndim!=1 or not len(x) or x.shape[1]!=len(w) or not np.isfinite(x).all() or not np.isfinite(w).all() or not 0<alpha<1:
        raise ValueError('Invalid aligned scenarios')
    losses=-x@w; k=len(x)*(1-alpha); order=np.argsort(-losses)
    mass=np.zeros(len(x)); mass[order]=np.clip(k-np.arange(len(x)),0,1)
    # Share boundary mass equally across all tied scenarios.
    boundary=losses[order[min(len(x)-1,int(np.ceil(k))-1)]]
    tied=losses==boundary; mass[tied]=mass[tied].sum()/tied.sum()
    marginal=-(mass@x)/k
    return {'es':float(marginal@w),'marginal':marginal.tolist(),'contributions':(marginal*w).tolist()}


def currency_loss(loss_return, capital):
    """Signed loss in base currency; gains are negative losses."""
    if not np.isfinite([loss_return,capital]).all() or capital<0:
        raise ValueError("Invalid loss or capital")
    return float(loss_return*capital)


def drawdown(r, dates):
    wealth=np.r_[1.,np.cumprod(1+np.asarray(r))]; peak=np.maximum.accumulate(wealth)
    dd=wealth/peak-1; trough=int(np.argmin(dd)); p=int(np.argmax(wealth[:trough+1]))
    recovery=next((i for i in range(trough+1,len(wealth)) if wealth[i]>=wealth[p]),None)
    run=longest=0
    for v in dd:
        run=run+1 if v<0 else 0; longest=max(run,longest)
    return {'maximum':float(-dd[trough]),'longest_duration':longest,'recovery_periods':recovery-trough if recovery is not None and trough else None,
            'underwater':dd[1:].tolist(),'dates':[str(d) for d in dates]}


def normal(loss,a):
    m=float(np.mean(loss)); s=float(np.std(loss,ddof=1)); z=stats.norm.ppf(a)
    return {'var':float(m+s*z),'es':float(m+s*stats.norm.pdf(z)/(1-a))}


def validation(loss,a):
    n=len(loss); split=int(n*.7); train=loss[:split]; test=loss[split:]
    if len(train)*(1-a)<5 or len(test)<20:return None
    f=empirical(train,a); hit=test>f['var']; count=int(hit.sum()); p=1-a
    def ll(k,n,p):return special.xlogy(k,p)+special.xlogy(n-k,1-p)
    uc=max(0.,float(2*(ll(count,len(hit),count/len(hit))-ll(count,len(hit),p))))
    pairs=np.zeros((2,2),int)
    for i,j in zip(hit[:-1],hit[1:]):pairs[int(i),int(j)]+=1
    totals=pairs.sum(axis=1); total=int(totals.sum()); successes=int(pairs[:,1].sum())
    ind=None
    if all(totals):
        lr=2*(sum(ll(int(pairs[i,1]),int(totals[i]),pairs[i,1]/totals[i]) for i in range(2))-ll(successes,total,successes/total))
        ind=float(stats.chi2.sf(max(0,lr),1))
    return {'test_count':len(test),'exceptions':count,'expected':float(len(test)*p),'kupiec_p':float(stats.chi2.sf(uc,1)),
            'independence_p':ind,'forecast_var':f['var'],'forecast_es':f['es'],
            'realized_exception_mean':float(test[hit].mean()) if count else None,'low_power':len(test)*p<10}


def evt(loss,a,threshold,rng):
    u=float(np.quantile(loss,threshold)); excess=loss[loss>u]-u; p=len(excess)/len(loss)
    if len(excess)<30 or a<=1-p or np.std(excess)==0:return None
    shape,_,scale=stats.genpareto.fit(excess,floc=0)
    if not np.isfinite([shape,scale]).all() or shape>=1 or scale<=0:return None
    q=u+stats.genpareto.ppf(1-(1-a)/p,shape,scale=scale)
    es=(q+scale-shape*u)/(1-shape)
    if not np.isfinite([q,es]).all():return None
    # Conditional sampling uncertainty (fixed threshold and fitted shape).
    draws=stats.genpareto.rvs(shape,scale=scale,size=(100,len(excess)),random_state=rng)
    scale_samples=draws.mean(axis=1)*(1-shape)
    qs=u+stats.genpareto.ppf(1-(1-a)/p,shape,scale=scale_samples)
    return {'var':float(q),'es':float(es),'threshold':u,'exceedances':len(excess),'shape':float(shape),
            'conditional_var_interval':np.quantile(qs,[.025,.975]).tolist()}


def profile(returns,dates,regular=True,target=0.):
    r=np.asarray(returns,float)
    if len(r)<2 or len(r)!=len(dates) or not np.isfinite(r).all() or np.any(r< -1) or not np.isfinite(target):raise ValueError('Invalid return series')
    loss=-r; rng=np.random.default_rng(11); models={}; checks={}; sensitivity={}
    histogram,edges=np.histogram(loss,bins=20)
    if regular:
        for a in LEVELS:
            key=str(int(a*100)); models[key]={}
            if len(r)*(1-a)<5-1e-9:continue
            m=models[key]; m['historical']=empirical(loss,a); m['gaussian']=normal(loss,a)
            m['simulated']=empirical(rng.normal(loss.mean(),loss.std(ddof=1),20000),a)
            if np.std(loss)>1e-12:
                df,loc,scale=stats.t.fit(loss)
                if df>1 and scale>0:
                    z=stats.t.ppf(a,df); es=loc+scale*stats.t.pdf(z,df)*(df+z*z)/((df-1)*(1-a))
                    if np.isfinite(es):m['student_t']={'var':float(loc+scale*z),'es':float(es),'df':float(df)}
                sensitivity[key]={str(t):v for t in (.85,.90,.95) if (v:=evt(loss,a,t,rng)) is not None}
                if '0.9' in sensitivity[key]:m['evt']=sensitivity[key]['0.9']
            checks[key]=validation(loss,a)
    return {'observations':len(r),'models':models,'validation':checks,'evt_sensitivity':sensitivity,
            'downside_target':float(target),'downside_deviation':float(np.sqrt(np.mean(np.minimum(r-target,0)**2))), 'shortfall_probability':float(np.mean(r<target)),
            'drawdown':drawdown(r,dates),'loss_histogram':{'counts':histogram.tolist(),'edges':edges.tolist()},
            'warning':'VaR is not a maximum loss; estimates use observed-period returns; negative loss indicates gain.'}


def dependence(returns):
    x=np.asarray(returns,float)
    if x.ndim!=2 or not 2<=x.shape[1]<=8 or len(x)<100 or not np.isfinite(x).all():raise ValueError('Require 100 aligned observations and 2–8 assets')
    train=x[:int(.7*len(x))];test=x[len(train):]; n,d=train.shape
    if np.any(np.std(train,axis=0)<1e-12):raise ValueError('Constant series: copula undefined')
    u=np.column_stack([stats.rankdata(c)/(n+1) for c in train.T]); z=stats.norm.ppf(u)
    corr=np.corrcoef(z,rowvar=False); corr=.999*corr+.001*np.eye(d)
    # Fixed df sensitivity, not an estimated or selected production model.
    df=5; tail=2*stats.t.cdf(-np.sqrt((df+1)*(1-corr)/(1+corr)),df+1)
    rng=np.random.default_rng(11); draws=rng.multivariate_normal(np.zeros(d),corr,20000)
    tdraws=draws/np.sqrt(rng.chisquare(df,len(draws))[:,None]/df)
    w=np.ones(d)/d; simulations={}
    for name,v in [('gaussian_copula',stats.norm.cdf(draws)),('student_t_copula',stats.t.cdf(tdraws,df))]:
        simulated=np.column_stack([np.quantile(train[:,j],v[:,j]) for j in range(d)])
        simulations[name]={str(int(a*100)):empirical(-simulated@w,a) for a in LEVELS}
    threshold=np.quantile(train,.05,axis=0); hits=(test<=threshold).astype(float)
    joint=hits.T@hits/len(test); denom=hits.mean(axis=0)
    empirical_tail=np.divide(joint,denom[:,None],out=np.zeros_like(joint),where=denom[:,None]>0)
    return {'observations':len(x),'test_observations':len(test),'weights':w.tolist(),'gaussian_correlation':corr.tolist(),
            'student_t_df':df,'student_t_lower_upper_tail':tail.tolist(),'empirical_lower_tail_conditional':empirical_tail.tolist(),
            'test_tail_counts':hits.sum(axis=0).tolist(),'simulated_risk':simulations,'empirical_risk':{'95':empirical(-train@w,.95)},
            'es_contributions':contributions(train,w),'warning':'Equal-weight illustration; fixed df=5; sparse tail estimates, not portfolio recommendations.'}
