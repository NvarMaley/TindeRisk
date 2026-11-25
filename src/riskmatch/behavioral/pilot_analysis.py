"""Synthetic analysis harness for pilot readiness; never human validation evidence."""

import numpy as np
from scipy.optimize import minimize
from scipy.special import expit


def synthetic_panel(n=180, items=40, seed=42):
    """Complete synthetic anchor panel, deliberately not real volunteers."""
    if n<60 or items<8:
        raise ValueError("Synthetic panel too small")
    rng=np.random.default_rng(seed)
    theta=rng.normal(size=n)
    language=rng.integers(0,2,n)
    order=rng.integers(0,2,(n,items))
    difficulty=np.linspace(-1.5,1.5,items)
    discrimination=np.linspace(.7,1.5,items)
    p=expit(theta[:,None]*discrimination-difficulty+.15*language[:,None]+.10*order)
    responses=rng.binomial(1,p)
    retest=rng.binomial(1,p)
    independent=rng.binomial(1,expit(theta-.3))
    return {"responses":responses,"retest":retest,"language":language,"order":order,
            "independent":independent,"person_ids":np.arange(n),"synthetic":True}


def _corr(x,y):
    if np.std(x)==0 or np.std(y)==0:return None
    return float(np.corrcoef(x,y)[0,1])


def psychometrics(panel, seed=42, bootstrap=100):
    x=np.asarray(panel["responses"],dtype=float)
    y=np.asarray(panel["retest"],dtype=float)
    if x.shape!=y.shape or x.ndim!=2 or not np.isin(x,[0,1]).all() or not np.isin(y,[0,1]).all():
        raise ValueError("Complete binary matrices required for this initial harness")
    item_stats=[{"item":i,"difficulty":float(x[:,i].mean()),
                 "corrected_item_total":_corr(x[:,i],x.sum(axis=1)-x[:,i])} for i in range(x.shape[1])]
    varying=np.std(x,axis=0)>0
    if varying.sum()<2:
        return {"status":"insufficient_item_variance","items":item_stats}
    corr=np.corrcoef(x[:,varying],rowvar=False)
    eigenvalues,eigenvectors=np.linalg.eigh(corr)
    # Exploratory one-factor loading approximation; not a fitted confirmatory omega model.
    loadings=eigenvectors[:,-1]*np.sqrt(max(0,eigenvalues[-1]-1))
    unique=np.maximum(0,1-loadings**2)
    denom=loadings.sum()**2+unique.sum()
    omega=float(loadings.sum()**2/denom) if denom else None
    rng=np.random.default_rng(seed); cors=[]
    for _ in range(bootstrap):
        sample=rng.integers(0,len(x),len(x))
        c=_corr(x[sample].mean(axis=1),y[sample].mean(axis=1))
        if c is not None:cors.append(c)
    return {"status":"exploratory_synthetic_only","items":item_stats,
            "test_retest":_corr(x.mean(axis=1),y.mean(axis=1)),
            "test_retest_ci95":np.quantile(cors,[.025,.975]).tolist() if cors else None,
            "omega_one_factor_approx":omega,"correlation_eigenvalues":eigenvalues[::-1].tolist()}


def _fit(x,y):
    def objective(b):
        z=x@b
        return float(np.sum(np.logaddexp(0,z)-y*z)+.5*np.sum(b[1:]**2))
    def derivative(b):
        penalty=b.copy();penalty[0]=0
        return x.T@(expit(x@b)-y)+penalty
    result=minimize(objective,np.zeros(x.shape[1]),jac=derivative,method="BFGS")
    if not result.success or not np.isfinite(result.x).all():
        raise RuntimeError("Exploratory logistic optimizer did not converge")
    return result.x


def _loss(x,y,b):
    z=x@b
    return float(np.mean(np.logaddexp(0,z)-y*z))


def logistic_readiness(panel, seed=42):
    """Person-level split; anchor-score proxy, item logistic DIF and independent choice prediction.

    This is not latent-variable IRT calibration. Missing randomized-session items
    need a future pilot-specific likelihood and anchor-linking design.
    """
    x=np.asarray(panel["responses"],dtype=float)
    if x.ndim!=2 or x.shape[1]<8 or not np.isin(x,[0,1]).all():
        raise ValueError("Complete binary panel required")
    n,items=x.shape; rng=np.random.default_rng(seed); ids=rng.permutation(n)
    train,val,test=np.split(ids,[int(.6*n),int(.8*n)])
    anchor_count=items//2
    anchor=x[:,:anchor_count].mean(axis=1)
    lang=np.asarray(panel["language"]); order=np.asarray(panel["order"])
    results=[]
    for i in range(anchor_count,items):
        features=np.column_stack([np.ones(n),anchor,lang,order[:,i],anchor*lang])
        beta=_fit(features[train],x[train,i])
        results.append({"item":i,"anchor_slope":float(beta[1]),"language_coefficient":float(beta[2]),
                        "order_coefficient":float(beta[3]),"language_anchor_interaction":float(beta[4]),
                        "validation_log_loss":_loss(features[val],x[val,i],beta),"test_log_loss":_loss(features[test],x[test,i],beta)})
    independent=np.asarray(panel["independent"])
    design=np.column_stack([np.ones(n),anchor]); b=_fit(design[train],independent[train])
    baseline=_fit(np.ones((len(train),1)),independent[train])
    return {"status":"synthetic_readiness_not_irt_validated","train_ids":train.tolist(),"validation_ids":val.tolist(),"test_ids":test.tolist(),
            "items":results,"independent_choice_test_loss":_loss(design[test],independent[test],b),
            "independent_baseline_test_loss":_loss(np.ones((len(test),1)),independent[test],baseline)}
