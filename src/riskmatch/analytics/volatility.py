"""Chapter 09: causal volatility and aligned covariance research estimators."""
from __future__ import annotations

import numpy as np
from scipy.optimize import minimize
from scipy.stats import chi2
from sklearn.covariance import LedoitWolf, OAS

VERSION="risk-v1.2.0"
FLOOR=1e-12


def _finite_matrix(values):
    x=np.asarray(values,float)
    if x.ndim!=2 or len(x)<2 or not np.isfinite(x).all():
        raise ValueError("Require finite, aligned observations")
    return x


def covariance_diagnostics(matrix):
    c=np.asarray(matrix,float)
    if c.ndim!=2 or c.shape[0]!=c.shape[1] or not np.isfinite(c).all():
        raise ValueError("Invalid covariance")
    symmetric=np.allclose(c,c.T,atol=1e-12,rtol=0)
    eigen=np.linalg.eigvalsh((c+c.T)/2)
    tolerance=max(1e-12,float(np.max(np.abs(eigen)))*1e-10)
    return {"symmetric":bool(symmetric),"psd":bool(symmetric and eigen[0]>=-tolerance),
            "min_eigenvalue":float(eigen[0]),"max_eigenvalue":float(eigen[-1]),
            "condition_number":float(eigen[-1]/eigen[0]) if eigen[0]>tolerance else None,
            "tolerance":tolerance}


def regularize(matrix, relative_floor=1e-8):
    """Traceable eigenvalue floor; raw matrix is retained separately."""
    c=np.asarray(matrix,float)
    before=covariance_diagnostics(c)
    if not before["symmetric"] or not before["psd"]:
        raise ValueError("Cannot silently regularize a materially invalid covariance")
    vals,vecs=np.linalg.eigh((c+c.T)/2)
    floor=max(FLOOR,float(np.max(vals))*relative_floor)
    adjusted=np.maximum(vals,floor)
    out=(vecs*adjusted)@vecs.T
    return out,{"before":before,"after":covariance_diagnostics(out),"floor":floor,
                "eigenvalues_adjusted":int(np.sum(vals<floor)),
                "frobenius_change":float(np.linalg.norm(out-c))}


def ewma_covariance(values, decay=.94):
    x=_finite_matrix(values)
    if not 0<decay<1:
        raise ValueError("Invalid decay")
    # Zero-mean shocks, initial variance from a first, explicitly observed row.
    cov=np.outer(x[0],x[0])
    for row in x[1:]:
        cov=decay*cov+(1-decay)*np.outer(row,row)
    return cov


def _qlike(y,h):
    h=np.maximum(h,FLOOR)
    return float(np.mean(np.log(h)+y/h))


def _var_metrics(y,h):
    return {"qlike":_qlike(y,h),"mse":float(np.mean((y-h)**2)),
            "mean_forecast_variance":float(np.mean(h)),"realized_variance":float(np.mean(y))}


def _autocorrelation_test(z):
    z=np.asarray(z,float)
    n=len(z); lag=min(10,n//5)
    if lag<1 or np.ptp(z)==0:
        return None
    centered=z-z.mean()
    rho=[float(centered[i:]@centered[:-i]/(centered@centered)) for i in range(1,lag+1)]
    q=n*(n+2)*sum(r*r/(n-i) for i,r in enumerate(rho,1))
    return float(chi2.sf(q,lag))


def _arch_curves(shocks, train, name):
    """Fit only on train; recurse one-step variances from prior observed shocks."""
    from arch import arch_model
    import arch
    x=shocks*100
    spec={"garch":("GARCH",0),"gjr_garch":("GARCH",1),"egarch":("EGARCH",1)}[name]
    fit=arch_model(x[:train],mean="Zero",vol=spec[0],p=1,o=spec[1],q=1,rescale=False).fit(
        disp="off",show_warning=False,options={"maxiter":1000})
    p={k:float(v) for k,v in fit.params.items()}
    if fit.convergence_flag or not np.isfinite(list(p.values())).all():
        raise ValueError("Nonconvergence")
    alpha=p["alpha[1]"]; beta=p["beta[1]"]; gamma=p.get("gamma[1]",0.)
    persistence=beta if name=="egarch" else alpha+beta+gamma/2
    if not 0<=persistence<.9999999:
        raise ValueError("Nonstationary or boundary persistence")
    h=np.empty(len(x)+1)
    h[0]=max(float(fit.conditional_volatility[0])**2,1e-8)
    guarded=[]
    for i,r in enumerate(x):
        if name=="egarch":
            z=r/np.sqrt(h[i])
            logh=p["omega"]+alpha*(abs(z)-np.sqrt(2/np.pi))+gamma*z+beta*np.log(h[i])
            if not np.isfinite(logh): raise ValueError("Nonfinite exponential variance")
            # Prespecified numerical guard, not a test-dependent model rejection.
            # Extreme forecasts remain penalized in QLIKE; counts are disclosed.
            bounded=np.clip(logh,-18.,18.)
            if bounded!=logh:guarded.append(i+1)
            h[i+1]=np.exp(bounded)
        else:
            h[i+1]=p["omega"]+(alpha+gamma*(r<0))*r*r+beta*h[i]
        if h[i+1]<=0 or not np.isfinite(h[i+1]):
            raise ValueError("Invalid conditional variance")
    h=h/10000
    z=shocks[:train]/np.sqrt(h[:train])
    return h,{"parameters":p,"persistence":float(persistence),"converged":True,
              "numerical_guard_count":len(guarded),"guarded_training":sum(i<train for i in guarded),
              "guarded_train_validation":sum(i<int(.8*len(shocks)) for i in guarded),
              "residual_ljung_box_p":_autocorrelation_test(z),
              "squared_residual_ljung_box_p":_autocorrelation_test(z*z),"library_version":arch.__version__}


def volatility_models(returns, dates, periods_per_year):
    r=np.asarray(returns,float)
    if len(r)<60 or len(r)!=len(dates) or not np.isfinite(r).all() or periods_per_year<=0:
        raise ValueError("Require at least 60 contiguous observations")
    if any(a>=b for a,b in zip(dates,dates[1:])):
        raise ValueError("Unordered dates")
    a,b=int(.6*len(r)),int(.8*len(r))
    shocks=r-r[:a].mean(); y=shocks**2; n=len(r)
    init=max(float(y[0]),FLOOR)
    expanding=np.array([max(float(y[:i].mean()),FLOOR) if i else init for i in range(n+1)])
    rolling=np.array([max(float(y[max(0,i-20):i].mean()),FLOOR) if i else init for i in range(n+1)])
    ewma=np.empty(n+1); ewma[0]=init
    for i,v in enumerate(y): ewma[i+1]=.94*ewma[i]+.06*v
    models={"historical":(expanding,{}),"rolling":(rolling,{"window":20}),"ewma":(ewma,{"decay":.94})}
    unavailable={}
    if len(r)>=100 and np.ptp(r[:a])>1e-12:
        for name in ("garch","egarch","gjr_garch"):
            try: models[name]=_arch_curves(shocks,a,name)
            except (ValueError,RuntimeError,ArithmeticError,ImportError) as exc: unavailable[name]=str(exc)
    else:
        unavailable={name:"Insufficient GARCH history or constant training series" for name in ("garch","egarch","gjr_garch")}
    output={}
    for name,(h,info) in models.items():
        h=np.maximum(h,FLOOR)
        output[name]=info|{"next_variance":float(h[-1]),"annualized_volatility":float(np.sqrt(h[-1]*periods_per_year)),
             "validation":_var_metrics(y[a:b],h[a:b]),"test":_var_metrics(y[b:],h[b:n]),
             "history":[[str(dates[i])[:10],float(np.sqrt(h[i]*periods_per_year)),float(np.sqrt(y[i]*periods_per_year))] for i in range(b,n)]}
    chosen=min((name for name in output if not output[name].get("guarded_train_validation",0)),
               key=lambda name:output[name]["validation"]["qlike"])
    return {"status":"experimental","approved":False,"version":VERSION,"observations":n,
            "split":{"train":a,"validation":b-a,"test":n-b},"annualization":periods_per_year,
            "selected_model":chosen,"models":output,"unavailable":unavailable}


def covariance_models(values, periods_per_year):
    """Common exact intervals only; fixed-train covariance, chronological test."""
    x=_finite_matrix(values)
    if len(x)<20 or periods_per_year<=0:
        raise ValueError("Insufficient aligned covariance data")
    a,b=int(.6*len(x)),int(.8*len(x))
    train=x[:a]; mean=train.mean(0); centered=train-mean
    sample=np.atleast_2d(np.cov(train,rowvar=False,ddof=1))
    lw=LedoitWolf().fit(train); oas=OAS().fit(train)
    models={"sample":(sample,{}),"ewma":(ewma_covariance(centered),{"decay":.94}),
            "ledoit_wolf":(lw.covariance_,{"shrinkage":float(lw.shrinkage_)}),
            "oas":(oas.covariance_,{"shrinkage":float(oas.shrinkage_)})}
    # Statistical factor reference: train-only PCA, no external factor claims.
    _,_,v=np.linalg.svd(centered,full_matrices=False)
    count=min(3,len(train)-1,x.shape[1])
    f=centered@v[:count].T
    factors=factor_covariance(train,f)
    models["pca_factor_diagonal"]=(np.asarray(factors["diagonal_residual_covariance"]),{"factors":count,"residual":"diagonal"})
    models["pca_factor_full"]=(np.asarray(factors["full_residual_covariance"]),{"factors":count,"residual":"full"})
    # Fixed equal-weight benchmark, not an optimized portfolio.
    w=np.full(x.shape[1],1/x.shape[1]); realized=(x-mean)@w
    results={}
    for name,(c,params) in models.items():
        corrected,diag=regularize(c)
        variance=max(float(w@c@w),0.)
        results[name]={"parameters":params,"covariance":c.tolist(),"annualized_covariance":(c*periods_per_year).tolist(),
                       "diagnostics":diag,"regularized_covariance":corrected.tolist(),
                       "validation":_var_metrics(realized[a:b]**2,np.full(b-a,variance)),
                       "test":_var_metrics(realized[b:]**2,np.full(len(x)-b,variance)),
                       "equal_weight_annual_volatility":float(np.sqrt(periods_per_year*variance)),
                       "test_realized_annual_volatility":float(np.sqrt(periods_per_year*np.mean(realized[b:]**2)))}
    def inverse_vol(y):
        weights=1/np.maximum(y.std(0,ddof=1),np.sqrt(FLOOR))
        return weights/weights.sum()
    initial=inverse_vol(train); revised=inverse_vol(x[:b])
    chosen=min(results,key=lambda key:results[key]["validation"]["qlike"])
    return {"observations":len(x),"assets":x.shape[1],"split":{"train":a,"validation":b-a,"test":len(x)-b},
            "annualization":periods_per_year,"models":results,"approved":False,
            "selected_model":chosen,
            "stability_reference":{"method":"inverse_volatility_diagnostic",
                "weight_half_l1_change":float(.5*np.abs(initial-revised).sum()),
                "train_weights_test_realized_volatility":float(np.sqrt(periods_per_year*np.mean(((x[b:]-mean)@initial)**2))),
                "revised_weights_test_realized_volatility":float(np.sqrt(periods_per_year*np.mean(((x[b:]-x[:b].mean(0))@revised)**2)))}}


def factor_covariance(asset_returns,factors):
    x=_finite_matrix(asset_returns); f=_finite_matrix(factors)
    if len(x)!=len(f):raise ValueError("Factor and asset dates must align")
    design=np.column_stack([np.ones(len(f)),f])
    beta=np.linalg.lstsq(design,x,rcond=None)[0][1:].T
    residual=x-design@np.linalg.lstsq(design,x,rcond=None)[0]
    systematic=beta@np.atleast_2d(np.cov(f,rowvar=False,ddof=1))@beta.T
    residual_cov=np.atleast_2d(np.cov(residual,rowvar=False,ddof=1))
    return {"beta":beta.tolist(),"diagonal_residual_covariance":(systematic+np.diag(np.diag(residual_cov))).tolist(),
            "full_residual_covariance":(systematic+residual_cov).tolist(),"approved":False}


def dcc_correlation(values):
    """Fit a,b on standardized training innovations; fixed parameters thereafter."""
    x=_finite_matrix(values)
    if not 2<=x.shape[1]<=8 or len(x)<100:raise ValueError("DCC requires 2–8 assets and 100 aligned periods")
    a=int(.6*len(x)); shocks=x-x[:a].mean(0)
    z=[]; variances=[]
    for j in range(x.shape[1]):
        h,_=_arch_curves(shocks[:,j],a,"garch")
        z.append(shocks[:,j]/np.sqrt(h[:-1]))
        variances.append(h)
    z=np.column_stack(z)
    target,_=regularize(np.atleast_2d(np.cov(z[:a],rowvar=False,ddof=1)))
    def normalize(q):
        d=np.sqrt(np.diag(q)); return q/np.outer(d,d)
    def recurse(params,limit,score=False):
        alpha,beta=params; q=target.copy(); loss=0.; history=[]
        for i in range(limit):
            corr=normalize(q)
            if score:
                sign,logdet=np.linalg.slogdet(corr)
                if sign<=0:return 1e12
                loss+=logdet+z[i]@np.linalg.solve(corr,z[i])
            else:history.append(corr)
            q=(1-alpha-beta)*target+alpha*np.outer(z[i],z[i])+beta*q
        return loss if score else (history,normalize(q))
    fit=minimize(lambda p:recurse(p,a,True),[.03,.94],method="SLSQP",bounds=[(0,.98),(0,.98)],
                 constraints=[{"type":"ineq","fun":lambda p:.999-sum(p)}],options={"maxiter":100})
    if not fit.success:raise ValueError("DCC nonconvergence")
    hist,next_corr=recurse(fit.x,len(z))
    variances=np.column_stack(variances)
    next_cov=next_corr*np.outer(np.sqrt(variances[-1]),np.sqrt(variances[-1]))
    b=int(.8*len(x)); w=np.ones(x.shape[1])/x.shape[1]
    test_variance=[]
    for t in range(b,len(x)):
        sd=np.sqrt(variances[t]); test_variance.append(float(w@(hist[t]*np.outer(sd,sd))@w))
    return {"alpha":float(fit.x[0]),"beta":float(fit.x[1]),"next_correlation":next_corr.tolist(),
            "next_covariance":next_cov.tolist(),"diagnostics":covariance_diagnostics(next_corr),
            "covariance_diagnostics":covariance_diagnostics(next_cov),
            "test":_var_metrics((shocks[b:]@w)**2,np.array(test_variance)),
            "test_correlations":[c.tolist() for c in hist[b:]]}
