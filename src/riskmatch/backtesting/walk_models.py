"""Train-only strategy registry used by the Chapter 23 chronological engine."""
import numpy as np
from sklearn.covariance import LedoitWolf
from riskmatch.optimization.mean_variance import MeanVariance,Constraints
from riskmatch.optimization.mean_variance_report import regularized_mean
from riskmatch.optimization.hierarchical import risk_budget,hierarchy,hrp,herc,maximum_diversification,proportional_cap,inverse_variance
from riskmatch.optimization.downside import cvar,cdar,omega,sortino
from riskmatch.optimization.black_litterman import posterior,delta_estimate
from riskmatch.optimization.black_litterman_report import default_views
from riskmatch.optimization.advanced import robust_utility,resampled_utility,wasserstein_utility,kelly,entropy_utility,uncertainty
from riskmatch.strategies.long_only_report import weights_at
from riskmatch.strategies.long_only import REGISTRY as LONG_REGISTRY
from riskmatch.strategies.alternative_report import target as alternative_target
from riskmatch.strategies.alternative import select_pair

OPTIMIZERS=('minimum_variance','maximum_sharpe','mean_variance_utility','inverse_variance','risk_parity','hrp','herc','maximum_diversification','minimum_cvar','minimum_cdar','maximum_sortino','maximum_omega','tracking_error','black_litterman','capm_utility','ewma_utility','robust_utility','resampled_utility','wasserstein_utility','kelly','fractional_kelly','entropy_utility')
SIGNED=('long_short','market_neutral','cta_etf_proxy','statistical_arbitrage')
ALTERNATIVE=('cross_sectional_momentum','time_series_momentum','mean_reversion','tactical_allocation','volatility_target','all_weather','multi_strategy','regime_switching','tail_hedge_proxy','global_macro',*SIGNED)
REGISTRY={'equal_weight':'Capped equal weight',**{k:k.replace('_',' ').title() for k in OPTIMIZERS},**{k:k.replace('_',' ').title() for k in LONG_REGISTRY},**{k:k.replace('_',' ').title() for k in ALTERNATIVE}}
TUNABLE={'mean_variance_utility','black_litterman','capm_utility','ewma_utility'}


def fit_models(keys,x,rf,assets,u,day,signals,*,optimizer_limit=64,market_caps=None,lam=3.,seed=23,macro=None,forecast=None):
    """Fit models on preceding returns; optional forecast only for a current-date target."""
    n=len(assets);u=np.asarray(u,float);ids=[a['id'] for a in assets];spy=next(i for i,a in enumerate(assets) if a['ticker']=='SPY');out={};membership,scores,books=signals
    if u.sum()<1-1e-9:return {k:{'status':'unavailable','reason':'Insufficient dated eligible capacity'} for k in keys}
    candidates=np.flatnonzero(u>0);stocks=[i for i in candidates if assets[i]['source']=='stock_monthly'];etfs=[i for i in candidates if i not in stocks]
    # All ETFs retained; only large-matrix optimizers use a dated cap-ranked stock subset.
    if len(candidates)>optimizer_limit:
        ordered=sorted(stocks,key=lambda i:(-(market_caps or {}).get(str(assets[i]['instrument']),0.),ids[i]));idx=np.array(etfs+ordered[:max(0,optimizer_limit-len(etfs))],int)
    else:idx=candidates
    local=x[:,idx];cap=u[idx];reference=proportional_cap(np.ones(len(idx))/len(idx),cap)[0] if cap.sum()>=1-1e-9 else None
    # Compute shared estimation only on the earlier training matrix.
    if forecast is not None:
        forecast=np.asarray(forecast,float)
        if forecast.shape!=(n,) or not np.isfinite(forecast).all():raise ValueError('Invalid dated forecast vector')
    mu=regularized_mean(local,forecast[idx] if forecast is not None else None);cov=LedoitWolf().fit(local).covariance_*12;rfa=float(np.mean(rf)*12);asset_subset=[assets[i] for i in idx];b=x[:,spy]
    engine=None;tree=None;unc=None
    def result(w):return {'status':'computed','weights':w}
    def unpack(r):
        if r.get('status') not in ('optimal','constrained_optimal','heuristic','aggregated_feasible','converged','computed','heuristic_capped','optimal_capped') or 'weights' not in r:raise ValueError(r.get('reason',r.get('message',r.get('status','Solver unavailable'))))
        return np.asarray(r['weights'],float)
    def expand(w):
        full=np.zeros(n);full[idx]=w;return full
    for key in keys:
        try:
            if key=='equal_weight':w=proportional_cap((u>0).astype(float)/np.sum(u>0),u)[0]
            elif key in LONG_REGISTRY:
                w,_,detail=weights_at(key,x,assets,u,day,membership,scores,books,.6,spy)
                if w is None:raise ValueError(detail.get('reason','Target unavailable'))
            elif key in ALTERNATIVE:
                pair=select_pair(x,[i for i,a in enumerate(assets) if a['ticker'] in ('SPY','IEF','SHY','TIP','BIL')]) if key=='statistical_arbitrage' else None
                w=alternative_target(key,x,u,assets,macro,pair)
            else:
                if reference is None or len(idx)<2:raise ValueError('Optimizer subset has insufficient cap capacity')
                if engine is None:engine=MeanVariance(mu,cov,rfa,Constraints(np.zeros(len(idx)),cap))
                if key=='minimum_variance':z=unpack(engine.solve())
                elif key=='maximum_sharpe':z=unpack(engine.max_sharpe())
                elif key=='mean_variance_utility':z=unpack(engine.solve(return_weight=1.,variance_weight=lam))
                elif key=='inverse_variance':z=proportional_cap(inverse_variance(cov),cap)[0]
                elif key=='risk_parity':z=unpack(risk_budget(cov,upper=cap))
                elif key in ('hrp','herc'):
                    if tree is None:tree=hierarchy(cov,ids=[ids[i] for i in idx])
                    if key=='hrp':z=proportional_cap(hrp(cov,tree),cap)[0]
                    else:z=proportional_cap(unpack(herc(cov,tree,min(3,len(idx)),cap)),cap)[0]
                elif key=='maximum_diversification':z=unpack(maximum_diversification(cov,cap))
                elif key=='minimum_cvar':z=unpack(cvar(local,cap,.95))
                elif key=='minimum_cdar':z=unpack(cdar(local,cap,.95))
                elif key=='maximum_sortino':z=unpack(sortino(local,cap))
                elif key=='maximum_omega':z=unpack(omega(local,cap))
                elif key=='tracking_error':
                    # Covariance of each candidate minus fixed external SPY, funded sum=1.
                    d=local-b[:,None];s=LedoitWolf().fit(d).covariance_*12;z=unpack(MeanVariance(np.zeros(len(idx)),s,0.,Constraints(np.zeros(len(idx)),cap)).solve())
                elif key=='capm_utility':
                    beta=(local-local.mean(0)).T@(b-b.mean())/((len(b)-1)*max(np.var(b,ddof=1),1e-12));m=rfa+beta*float(np.mean(b-rf)*12);z=unpack(MeanVariance(m,cov,rfa,Constraints(np.zeros(len(idx)),cap)).solve(return_weight=1.,variance_weight=lam))
                elif key=='ewma_utility':
                    p=.94**np.arange(len(local)-1,-1,-1);p/=p.sum();m=p@local;d=local-m;s=(d.T*p)@d*12;z=unpack(MeanVariance(m*12,s,rfa,Constraints(np.zeros(len(idx)),cap)).solve(return_weight=1.,variance_weight=lam))
                elif key=='black_litterman':
                    anchor=reference;P,q,corr_conf,corr,_=default_views(asset_subset,anchor,mu,rfa);delta=delta_estimate(local,rf,anchor)['delta'];bl=posterior(cov,anchor,delta,.05,P,q,corr_conf,corr);z=unpack(MeanVariance(rfa+bl['posterior_excess'],bl['predictive_covariance'],rfa,Constraints(np.zeros(len(idx)),cap)).solve(return_weight=1.,variance_weight=lam))
                elif key in ('robust_utility','resampled_utility','wasserstein_utility'):
                    if unc is None:unc=uncertainty(local,4,seed=seed)
                    m,c,h,r,means,covs=unc
                    if key=='robust_utility':z=unpack(robust_utility(m,c,h,r,cap,lam,0.,reference))
                    elif key=='resampled_utility':z=unpack(resampled_utility(means,covs,cap,lam,0.,reference))
                    else:z=unpack(wasserstein_utility(m,c,float(np.linalg.norm(h)),cap,lam,0.,reference))
                elif key in ('kelly','fractional_kelly'):
                    z=unpack(kelly(local,cap,0.,reference))
                    if key=='fractional_kelly':z=.25*z+.75*reference
                elif key=='entropy_utility':z=unpack(entropy_utility(mu,cov,.01,cap,lam,0.,reference))
                else:raise ValueError('Unknown model')
                w=expand(z)
            if w is None or not np.isfinite(w).all() or (key not in SIGNED and np.any(w< -1e-7)) or np.any(abs(w)>u+1e-6) or w.sum()>1+1e-6 or key in SIGNED and abs(w).sum()>1.5+1e-6:raise ValueError('Invalid/funded target unavailable')
            out[key]=result(w if key in SIGNED else np.maximum(w,0))|{'candidate_count':len(idx) if key in OPTIMIZERS else len(candidates)}
        except (ValueError,ArithmeticError,RuntimeError,np.linalg.LinAlgError) as exc:out[key]={'status':'unavailable','reason':str(exc)}
    return out
