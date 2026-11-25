"""Chapter 10 retrospective factor research, not a point-in-time trading signal."""
from __future__ import annotations

import numpy as np
from scipy.stats import spearmanr
import statsmodels.api as sm
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

VERSION="factors-v1.1.0"
PUBLISHED=("Mkt-RF","SMB","HML","RMW","CMA","Mom")
TAXONOMY={
    "market":"Mkt-RF, published excess market return",
    "value":"HML, published value premium",
    "size":"SMB, published size premium (five-factor definition)",
    "momentum":"Mom, published momentum premium",
    "quality":"internal as-reported annual profitability/leverage score, long-short proxy",
    "low_volatility":"internal negative trailing volatility score, long-short proxy",
    "profitability":"RMW, published profitability premium",
    "investment":"CMA, published investment premium",
    "carry":"change in 3-month Treasury yield, sensitivity proxy not traded carry",
    "term":"change in 10-year Treasury yield, sensitivity proxy",
    "treasury_curve":"change in 10Y-2Y slope and 2*5Y-2Y-10Y curvature",
    "liquidity":"internal size-neutralized log reported monthly share volume proxy",
    "inflation":"realized monthly CPI change, latest-vintage ex-post proxy; not inflation surprise",
}


def zscore(values):
    x=np.asarray(values,float); valid=np.isfinite(x); out=np.full(x.shape,np.nan)
    if valid.sum()<10:return out
    lo,hi=np.quantile(x[valid],[.01,.99]); v=np.clip(x[valid],lo,hi)
    scale=v.std(ddof=1)
    if scale>0:out[valid]=(v-v.mean())/scale
    return out


def neutralize(values, control):
    x=np.asarray(values,float); c=np.asarray(control,float)
    valid=np.isfinite(x)&np.isfinite(c); out=np.full(x.shape,np.nan)
    if valid.sum()>=10 and np.ptp(c[valid])>0:
        design=np.column_stack((np.ones(valid.sum()),c[valid]))
        out[valid]=x[valid]-design@np.linalg.lstsq(design,x[valid],rcond=None)[0]
    return out


def factor_portfolio(ids, scores, returns, previous=None, cost=.001):
    """Equal-weight extreme quintiles; missing constituent outcomes invalidate return."""
    scores=np.asarray(scores,float); returns=np.asarray(returns,float)
    valid=np.flatnonzero(np.isfinite(scores)); n=len(valid)
    if n<50:return None
    order=valid[np.lexsort((np.asarray(ids)[valid],scores[valid]))]; k=n//5
    lo,hi=order[:k],order[-k:]
    weights={ids[i]:-1/k for i in lo}|{ids[i]:1/k for i in hi}
    turnover=sum(abs(weights.get(i,0)-(previous or {}).get(i,0)) for i in set(weights)|set(previous or {}))
    selected=np.r_[lo,hi]
    complete=np.isfinite(returns[selected]).all()
    gross=float(returns[hi].mean()-returns[lo].mean()) if complete else None
    pair=np.isfinite(scores)&np.isfinite(returns)
    ic=spearmanr(scores[pair],returns[pair]).statistic if pair.sum()>=10 and np.ptp(scores[pair])>0 and np.ptp(returns[pair])>0 else np.nan
    return {"gross":gross,"net":gross-cost*turnover if gross is not None else None,
            "turnover":float(turnover),"rank_ic":float(ic) if np.isfinite(ic) else None,
            "scored":n,"selected":len(selected),"matched":int(np.isfinite(returns[selected]).sum()),"weights":weights}


def _metrics(y,p):
    error=y-p
    return {"mse":float(np.mean(error**2)),"mae":float(np.mean(abs(error)))}


def regression(y, x, dates, names, frequency):
    """Train/validation/test; test predictions are conditional on realized factors."""
    y=np.asarray(y,float); x=np.asarray(x,float)
    n=len(y); p=x.shape[1]
    if n<max(36,8*p) or x.shape!=(n,len(names)) or len(dates)!=n or not np.isfinite(np.c_[y,x]).all():
        raise ValueError("Insufficient matched factor observations")
    if any(a>=b for a,b in zip(dates,dates[1:])):raise ValueError("Unordered dates")
    if np.ptp(y)<=1e-12:raise ValueError("Constant return target")
    a,b=int(.6*n),int(.8*n)
    design=sm.add_constant(x,has_constant="add")
    if np.linalg.matrix_rank(design[:a])<p+1:raise ValueError("Rank-deficient factor design")
    hac_lags=min(6 if frequency=="monthly" else 10,a//5)
    fit=sm.OLS(y[:a],design[:a]).fit(cov_type="HAC",cov_kwds={"maxlags":hac_lags})
    coef=fit.params; predicted=design@coef
    resid=y-predicted
    standard=StandardScaler().fit(x[:a]); train=standard.transform(x[:a]); full=standard.transform(x)
    candidates=[]
    for penalty in (.01,.1,1.,10.):
        model=Ridge(alpha=penalty).fit(train,y[:a]); p_hat=model.predict(full)
        candidates.append((_metrics(y[a:b],p_hat[a:b])["mse"],penalty,p_hat,
                           model.coef_/standard.scale_,float(model.intercept_-model.coef_@(standard.mean_/standard.scale_))))
    _,penalty,ridge_prediction,ridge_beta,ridge_alpha=min(candidates,key=lambda c:c[0])
    # VIF on training columns, no future data.
    vif={}
    for j,name in enumerate(names):
        others=np.delete(x[:a],j,axis=1)
        if not others.shape[1]:vif[name]=1.;continue
        aux=sm.OLS(x[:a,j],sm.add_constant(others,has_constant="add")).fit()
        vif[name]=float(1/(1-aux.rsquared)) if aux.rsquared<1-1e-12 else None
    window=36 if frequency=="monthly" else 126
    rolling=[]
    for end in range(window,n+1,max(1,n//120)):
        z=design[end-window:end]
        if frequency=="monthly":
            months=[d.year*12+d.month for d in dates[end-window:end]]
            if months[-1]-months[0]!=window-1 or len(set(months))!=window:continue
        if np.linalg.matrix_rank(z)==p+1:
            rolling.append([str(dates[end-1])[:10],*np.linalg.lstsq(z,y[end-window:end],rcond=None)[0][1:].tolist()])
    drift=[float(v) for v in np.std(np.array([r[1:] for r in rolling]),axis=0)] if rolling else []
    factor_premium=x[:a].mean(0)
    systematic=float(coef[1:]@np.atleast_2d(np.cov(x[:a],rowvar=False,ddof=1))@coef[1:])
    residual_variance=float(np.var(resid[:a],ddof=1))
    attributed=x[b:]*coef[1:]
    return {"observations":n,"split":{"train":a,"validation":b-a,"test":n-b},
            "first":str(dates[0])[:10],"last":str(dates[-1])[:10],"factor_names":list(names),
            "alpha":float(coef[0]),"beta":dict(zip(names,map(float,coef[1:]))),
            "hac_se":dict(zip(names,map(float,fit.bse[1:]))),"hac_p":dict(zip(names,map(float,fit.pvalues[1:]))),
            "hac_lags":hac_lags,"r_squared":float(fit.rsquared),"condition_number":float(np.linalg.cond(train)),
            "vif":vif,"residual_durbin_watson":float(sm.stats.durbin_watson(resid[:a])),
            "validation":_metrics(y[a:b],predicted[a:b]),"test":_metrics(y[b:],predicted[b:]),
            "ridge":{"alpha_penalty":penalty,"intercept":ridge_alpha,"beta":dict(zip(names,map(float,ridge_beta))),
                     "validation":_metrics(y[a:b],ridge_prediction[a:b]),"test":_metrics(y[b:],ridge_prediction[b:])},
            "rolling":rolling,"rolling_beta_std":drift,
            "attribution":{"alpha":float(coef[0]),"mean_factor_contribution":dict(zip(names,attributed.mean(0).tolist())),
                           "mean_residual":float(resid[b:].mean()),"mean_realized_excess":float(y[b:].mean())},
            "factor_risk":{"systematic_variance":systematic,"residual_variance":residual_variance},
            "implied_expected_excess":float(coef[1:]@factor_premium),"approved":False}


def pca_diagnostics(x):
    x=np.asarray(x,float)
    if x.ndim!=2 or len(x)<30 or not np.isfinite(x).all():raise ValueError("Invalid PCA input")
    a=int(.6*len(x)); train=x[:a]; mean=train.mean(0); scale=train.std(0,ddof=1)
    if np.any(scale<=0):raise ValueError("Constant PCA input")
    z=(train-mean)/scale; _,s,v=np.linalg.svd(z,full_matrices=False)
    count=min(5,len(v)); loadings=v[:count]
    # Orient largest absolute loading positive; compare validation components via |cosine|.
    for row in loadings:
        if row[np.argmax(abs(row))]<0:row*=-1
    hold=(x[a:]-mean)/scale; _,_,hv=np.linalg.svd(hold,full_matrices=False)
    stability=[float(np.max(abs(hv[:count]@row))) for row in loadings]
    return {"basis":"training correlation","explained_variance_ratio":(s[:count]**2/np.sum(s*s)).tolist(),
            "loadings":loadings.tolist(),"heldout_loading_similarity":stability,"approved":False}
