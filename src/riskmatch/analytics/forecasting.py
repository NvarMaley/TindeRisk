"""Chapter 08: experimental one-period forecasts; no investment approval."""
from __future__ import annotations

import hashlib
import warnings
from dataclasses import asdict
from datetime import datetime, timezone

import numpy as np
from scipy.stats import spearmanr

from riskmatch.contracts import ForecastBundle, RunMetadata, Status

VERSION = "forecast-v1.2.0"
SEED = 42
MIN_OBSERVATIONS = 100


def lagged_examples(returns, window=20):
    """One-step labels; X[t] uses only returns strictly before y[t]."""
    r = np.asarray(returns, dtype=float)
    if r.ndim != 1 or not np.isfinite(r).all() or len(r) <= window:
        raise ValueError("Expected a finite continuous return sequence")
    def features(h):
        return [h[-1], h[-5:].mean(), h.mean(), h.std(ddof=1),
                np.sqrt(np.mean(np.minimum(h, 0)**2))]
    X = np.array([features(r[i-window:i]) for i in range(window, len(r))])
    return X, r[window:], np.array(features(r[-window:]))[None, :]


def _linear(X, y, alpha=0., l1_ratio=0.):
    """Train-only standardization; coordinate descent for elastic net."""
    center = X.mean(axis=0)
    scale = X.std(axis=0)
    scale[scale == 0] = 1.
    z = (X-center)/scale
    intercept = y.mean()
    v = y-intercept
    if alpha == 0:
        coef = np.linalg.lstsq(z, v, rcond=None)[0]
    else:
        coef = np.zeros(z.shape[1])
        gram = z.T@z/len(y)
        target = z.T@v/len(y)
        for _ in range(1000):
            old = coef.copy()
            for j in range(len(coef)):
                rho = target[j]-gram[j]@coef+gram[j,j]*coef[j]
                denominator = gram[j,j]+alpha*(1-l1_ratio)
                coef[j] = np.sign(rho)*max(abs(rho)-alpha*l1_ratio, 0)/denominator if denominator else 0
            if np.max(np.abs(coef-old)) < 1e-10:
                break
    return lambda x: intercept+(x-center)/scale@coef


def _mean_predictions(r, window, mode):
    out = []
    for i in range(window, len(r)+1):
        history = r[:i]
        if mode == "historical":
            out.append(history.mean())
        elif mode == "rolling":
            out.append(history[-window:].mean())
        else:
            weights = .94**np.arange(len(history)-1, -1, -1)
            out.append(np.dot(history, weights)/weights.sum())
    return np.asarray(out)


def _scores(y, p, lower, upper, cost):
    error = y-p
    position = (p > 0).astype(float)
    turnover = np.abs(np.diff(position, prepend=0))
    net = position*y-cost*turnover
    corr = spearmanr(y,p).statistic if np.ptp(y)>0 and np.ptp(p)>0 else np.nan
    return {"mse":float(np.mean(error**2)), "mae":float(np.mean(np.abs(error))),
            "directional_accuracy":float(np.mean(np.sign(p)==np.sign(y))),
            "temporal_rank_correlation":float(corr) if np.isfinite(corr) else None,
            "interval_coverage":float(np.mean((y>=lower)&(y<=upper))),
            "net_strategy_mean":float(np.mean(net)),
            "buy_hold_mean":float(np.mean(y)), "turnover_mean":float(turnover.mean())}


def _bound(values, kind):
    """Unlevered simple price/total returns cannot lose more than all capital."""
    return np.maximum(values,-1.) if kind in ("total_return","price_return") else values


def _optional_models(X, y, val_x, val_y, all_x, kind):
    """Use actual libraries when installed; never relabel a substitute."""
    models, unavailable = {}, {}
    try:
        import sklearn
        from sklearn.ensemble import RandomForestRegressor
        from sklearn.exceptions import ConvergenceWarning
        from sklearn.neural_network import MLPRegressor
        from sklearn.pipeline import make_pipeline
        from sklearn.preprocessing import StandardScaler
        families = {
            "random_forest":[(dict(max_depth=d,n_estimators=60,random_state=SEED,n_jobs=1),
                              RandomForestRegressor) for d in (2,4)],
            "neural_network":[(dict(hidden_layer_sizes=(h,),alpha=.01,random_state=SEED,
                                    max_iter=2000,max_fun=30000,solver="lbfgs"),MLPRegressor) for h in (4,8)],
        }
        for name, choices in families.items():
            candidates = []
            # Scale inputs and target on train only; neural target scaling avoids tiny-return loss.
            ym, ys = y.mean(), max(y.std(), 1e-8)
            for params, cls in choices:
                model = make_pipeline(StandardScaler(),cls(**params))
                with warnings.catch_warnings(record=True) as report:
                    warnings.simplefilter("always",ConvergenceWarning)
                    model.fit(X,(y-ym)/ys)
                converged=not any(issubclass(w.category,ConvergenceWarning) for w in report)
                predict = lambda x: _bound(model.predict(x)*ys+ym,kind)
                if converged:
                    candidates.append((float(np.mean((val_y-predict(val_x))**2)),
                                       params | {"library_version":sklearn.__version__,"converged":True},predict(all_x)))
            if not candidates:
                unavailable[name]="No candidate converged on training data"
                continue
            _, params, predictions = min(candidates,key=lambda c:c[0])
            models[name]=(predictions,params)
    except ImportError:
        for name in ("random_forest","neural_network"):
            unavailable[name]="scikit-learn unavailable"
    try:
        import xgboost
        from xgboost import XGBRegressor
        candidates=[]
        ym, ys = y.mean(), max(y.std(), 1e-8)
        for depth in (2,3):
            params=dict(max_depth=depth,n_estimators=60,learning_rate=.05,random_state=SEED,n_jobs=1)
            model=XGBRegressor(**params)
            model.fit(X,(y-ym)/ys)
            prediction=_bound(model.predict(val_x)*ys+ym,kind)
            candidates.append((float(np.mean((val_y-prediction)**2)),params | {"library_version":xgboost.__version__},_bound(model.predict(all_x)*ys+ym,kind)))
        _, params, predictions=min(candidates,key=lambda c:c[0])
        models["xgboost"]=(predictions,params)
    except (ImportError, OSError):
        unavailable["xgboost"]="XGBoost unavailable"
    return models, unavailable


def factor_reference(asset, factors, risk_free, market_weights=None, covariance=None, risk_aversion=2.5):
    """Train-only contemporaneous factor regressions; no claim of PIT factor availability.

    Inputs must be aligned and decimal-period returns; future factors are replaced
    by their training means. BL no-view equilibrium reference only.
    """
    a=np.asarray(asset,float)
    f=np.asarray(factors,float)
    rf=np.asarray(risk_free,float)
    if f.ndim!=2 or f.shape[0]!=len(a) or rf.shape!=a.shape or not np.isfinite(np.c_[a,rf,f]).all():
        raise ValueError("Factor inputs must be finite and aligned")
    result={}
    for name,k in (("capm",1),("multifactor",f.shape[1])):
        design=np.column_stack((np.ones(len(a)),f[:,:k]))
        coefficients=np.linalg.lstsq(design,a-rf,rcond=None)[0]
        result[name]={"alpha":float(coefficients[0]),"beta":coefficients[1:].tolist(),
                      "expected_total":float(rf.mean()+coefficients[1:]@f[:,:k].mean(axis=0))}
    if market_weights is not None and covariance is not None:
        w=np.asarray(market_weights,float); cov=np.asarray(covariance,float)
        if cov.shape!=(len(w),len(w)) or not np.allclose(cov,cov.T) or np.linalg.eigvalsh(cov).min() < -1e-10:
            raise ValueError("Invalid BL covariance")
        result["black_litterman_no_view"]=(risk_aversion*cov@w).tolist()
    return result


def forecast(returns, dates, *, instrument, frequency, currency, kind, data_version,
             as_of, window=20, cost=.001, include_ml=False):
    """Fixed train/validation/test split; one-period, nonoverlapping labels.

    The final test segment is never used for parameter selection or intervals.
    Forecasts use realized past observations as they become available.
    """
    r=np.asarray(returns,float)
    if frequency not in ("daily","weekly","monthly") or kind not in ("total_return","price_return","excess_return"):
        raise ValueError("Unsupported frequency or target")
    if kind in ("total_return","price_return") and np.any(r < -1):
        raise ValueError("Invalid unlevered simple return")
    if not isinstance(window,int) or window<10 or not 0<=cost<=1:
        raise ValueError("Invalid forecast window or transaction cost")
    if len(r)!=len(dates) or len(r)<max(MIN_OBSERVATIONS,window+60):
        raise ValueError("Insufficient continuous history (100 observations required)")
    if any(a>=b for a,b in zip(dates,dates[1:])) or str(dates[-1])[:10]>str(as_of)[:10]:
        raise ValueError("Dates must be ordered and available at cutoff")
    X,y,next_x=lagged_examples(r,window)
    n=len(y); a,b=int(.6*n),int(.8*n)
    all_x=np.vstack((X,next_x))
    baseline={m:(_mean_predictions(r,window,m),{"window":window,"decay":.94} if m=="ewma" else {"window":window} if m=="rolling" else {})
              for m in ("historical","rolling","ewma")}
    baseline["zero_return"]=(np.zeros(n+1),{})
    models=baseline.copy()
    models["ols"]=(_linear(X[:a],y[:a])(all_x),{})
    for name,ratio in (("ridge",0.),("lasso",1.),("elastic_net",.5)):
        candidates=[]
        for alpha in (1e-5,1e-4,1e-3,.01,.1):
            p=_bound(_linear(X[:a],y[:a],alpha,ratio)(all_x),kind)
            candidates.append((float(np.mean((y[a:b]-p[a:b])**2)),alpha,p))
        _, alpha,p=min(candidates,key=lambda c:c[0])
        models[name]=(p,{"alpha":alpha,"l1_ratio":ratio})
    # Prespecified ablations: fewer inputs and train-only tail clipping.
    models["ols_lag_only"]=(_linear(X[:a,:1],y[:a])(all_x[:,:1]),{})
    limits=np.quantile(y[:a],[.01,.99])
    models["ols_clipped"]=(_linear(X[:a],np.clip(y[:a],*limits))(all_x),{"quantiles":[.01,.99]})
    # Shorter historical window on identical forecast origins and test dates.
    models["rolling_10"]=(_mean_predictions(r,10,"rolling")[window-10:],{"window":10})
    training_residual=y[:a]-models["ols"][0][:a]
    tss=np.sum((y[:a]-y[:a].mean())**2)
    rss=np.sum(training_residual**2)
    ols_diagnostics={"train_r_squared":float(1-rss/tss) if tss>0 else None,
                     "train_durbin_watson":float(np.sum(np.diff(training_residual)**2)/rss) if rss>0 else None,
                     "design_rank":int(np.linalg.matrix_rank(np.column_stack((np.ones(a),X[:a]))))}
    unavailable={"capm":"requires approved aligned market/RF inputs",
                 "fama_french":"requires approved PIT factor history",
                 "black_litterman":"requires approved prior/covariance/views",
                 "cash":"requires aligned risk-free series",
                 "cross_sectional_rank_ic":"requires point-in-time multi-asset panel"}
    if include_ml:
        optional, missing=_optional_models(X[:a],y[:a],X[a:b],y[a:b],all_x,kind)
        models.update(optional); unavailable.update(missing)
    else:
        unavailable.update({m:"optional advanced model run not requested" for m in ("random_forest","xgboost","neural_network")})
    results={}
    for name,(p,params) in models.items():
        p=_bound(p,kind)
        errors=y[a:b]-p[a:b]
        lo,hi=np.quantile(errors,[.05,.95])
        pred=p[b:n]; lower=_bound(pred+lo,kind); upper=_bound(pred+hi,kind)
        metrics=_scores(y[b:],pred,lower,upper,cost)
        results[name]={"parameters":params,"validation_mse":float(np.mean(errors**2)),
                       "test":metrics,"expected_return":float(p[-1]),
                       "interval":[float(_bound(p[-1]+lo,kind)),float(_bound(p[-1]+hi,kind))],
                       "residual_quantiles":np.quantile(y[b:]-pred,[.05,.5,.95]).tolist(),
                       "history":[[str(dates[window+i])[:10],float(y[i]),float(p[i]),float(lower[i-b]),float(upper[i-b])] for i in range(b,n)]}
    chosen=min(results,key=lambda m:results[m]["validation_mse"])
    stamp=datetime.fromisoformat(str(as_of)[:10]).replace(tzinfo=timezone.utc)
    run=hashlib.sha256(repr((VERSION,data_version,instrument,frequency,currency,kind,str(as_of),window,cost,include_ml,tuple(r),tuple(map(str,dates)),[(name,info["parameters"]) for name,info in results.items()])).encode()).hexdigest()
    bundle=ForecastBundle(meta=RunMetadata(as_of=stamp,run_id=run,model_version=VERSION,
        units=(("return","decimal per period"),),provenance=(data_version,),status=Status.EXPERIMENTAL),
        snapshot_id=data_version,instrument_ids=(instrument,),expected_returns=(results[chosen]["expected_return"],),
        horizon_periods=1,frequency=frequency,currency=currency,distribution_ref=run)
    envelope=asdict(bundle)
    envelope["meta"]["as_of"]=stamp.isoformat()
    return {"status":"experimental","approved":False,"version":VERSION,"data_version":data_version,
            "seed":SEED,"kind":kind,"frequency":frequency,"currency":currency,
            "horizon_periods":1,"selected_model":chosen,"window":window,"cost":cost,
            "split":{"train":a,"validation":b-a,"test":n-b,"train_end":str(dates[window+a-1])[:10],
                     "validation_end":str(dates[window+b-1])[:10],"test_end":str(dates[-1])[:10]},
            "models":results,"unavailable":unavailable,"bundle":envelope,
            "ols_diagnostics":ols_diagnostics,
            "interval_nominal_coverage":.90,"warning":"Experimental forecasts; empirical validation residual intervals are not guaranteed."}
