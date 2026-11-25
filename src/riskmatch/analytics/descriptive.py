"""Research descriptive statistics with explicit missingness and interval alignment."""
import numpy as np
from math import erfc,exp,gamma,sqrt
from statistics import NormalDist


def chi_square_survival(value,degrees):
    """Integer-df chi-square survival via the half-integer gamma recurrence."""
    x=max(0.0,value/2)
    a=.5 if degrees%2 else 1.
    tail=erfc(sqrt(x)) if degrees%2 else exp(-x)
    while a<degrees/2:
        tail+=exp(-x)*x**a/gamma(a+1)
        a+=1
    return min(1.,max(0.,tail))


def average_ranks(values):
    _,inverse,counts=np.unique(values,return_inverse=True,return_counts=True)
    ranks=np.cumsum(counts)-(counts-1)/2
    return ranks[inverse]


def finite_values(values):
    a=np.asarray(values,dtype=float)
    return a[np.isfinite(a)]


def summarize(values,k=None):
    a=np.asarray(values,dtype=float)
    x=finite_values(a)
    n=len(x)
    result={"count":n,"missing":len(a)-n}
    if not n:
        return result
    q=np.quantile(x,[0,.01,.05,.25,.5,.75,.95,.99,1])
    result.update(dict(zip(("min","q01","q05","q25","median","q75","q95","q99","max"),map(float,q))))
    mean=float(x.mean())
    result.update(mean=mean,geometric_mean=float(np.expm1(np.log1p(x).mean())) if min(x)>-1 else (-1.0 if min(x)==-1 else None),
                  downside_deviation=float(np.sqrt(np.mean(np.minimum(x,0)**2))))
    if n>1:
        deviation=float(x.std(ddof=1))
        result.update(variance=deviation**2,volatility=deviation,
                      annualized_volatility=deviation*np.sqrt(k) if k else None)
    if n>3 and x.std()>0:
        z=(x-mean)/x.std()
        g1=float(np.mean(z**3))
        g2=float(np.mean(z**4)-3)
        result.update(skewness=float(np.sqrt(n*(n-1))/(n-2)*g1),
                      excess_kurtosis=float((n-1)/((n-2)*(n-3))*((n+1)*g2+6)),
                      jarque_bera=float(n/6*(g1*g1+g2*g2/4)),
                      jarque_bera_p=chi_square_survival(n/6*(g1*g1+g2*g2/4),2))
    return result


def distribution(values,bins=20):
    x=finite_values(values)
    if not len(x):
        return {"histogram":[],"cdf":[],"qq":[]}
    counts,edges=np.histogram(x,bins=bins)
    p=np.linspace(.01,.99,49)
    q=np.quantile(x,p)
    empirical=np.searchsorted(np.sort(x),q,side="right")/len(x)
    return {"histogram":[[float(a),float(b),int(c)] for a,b,c in zip(edges[:-1],edges[1:],counts)],
            "cdf":[[float(v),float(prob)] for v,prob in zip(q,empirical)],
            "qq":[[NormalDist().inv_cdf(float(a)),float(b)] for a,b in zip(p,q)]}


def time_diagnostics(values,max_lag=10):
    x=np.asarray(values,dtype=float)
    n=len(x)
    if n<20 or not np.isfinite(x).all() or x.std()==0:
        return {"observations":n,"acf":[],"pacf":[]}
    centered=x-x.mean()
    m=min(max_lag,n//5)
    acf=np.array([1.0]+[float(centered[:-i]@centered[i:]/(centered@centered)) for i in range(1,m+1)])
    pacf=[1.]
    for lag in range(1,m+1):
        idx=np.arange(lag)
        pacf.append(float(np.linalg.lstsq(acf[np.abs(idx[:,None]-idx)],acf[1:lag+1],rcond=None)[0][-1]))
    q=float(n*(n+2)*sum(acf[i]**2/(n-i) for i in range(1,m+1)))
    # ADF(1), intercept; report statistic only (nonstandard null distribution).
    delta=np.diff(x)
    design=np.column_stack((np.ones(n-2),x[1:-1],delta[:-1]))
    y=delta[1:]
    coef=np.linalg.lstsq(design,y,rcond=None)[0]
    residual=y-design@coef
    var=float(residual@residual/(len(y)-3))
    se=np.sqrt(var*np.linalg.pinv(design.T@design)[1,1])
    adf=float(coef[1]/se) if se>0 and np.linalg.matrix_rank(design)==3 else None
    return {"observations":n,"acf":acf.tolist(),"pacf":pacf,"ljung_box":q,
            "ljung_box_p":chi_square_survival(q,m),"adf_lag1_t":adf}


def longest_contiguous(frame):
    """Take the longest valid contiguous interval run from a sorted frame."""
    import pandas as pd
    best_start,best_end=0,0
    start=0
    previous=None
    for i,row in enumerate(frame.itertuples()):
        if not np.isfinite(row.value) or pd.isna(row.start_date):
            start=i+1
            previous=None
            continue
        if previous is not None and row.start_date!=previous:
            start=i
        if i+1-start>best_end-best_start:
            best_start,best_end=start,i+1
        previous=row.end_date
    return frame.value.to_numpy()[best_start:best_end]


def covariance_matrix(matrix):
    """Complete-case sample covariance; no pairwise PSD claim."""
    a=np.asarray(matrix,dtype=float)
    if a.ndim!=2:
        raise ValueError("Expected observations by assets")
    a=a[np.isfinite(a).all(axis=1)]
    if len(a)<2:
        return {"count":len(a),"covariance":None,"pearson":None,"spearman":None,"psd":None}
    cov=np.atleast_2d(np.cov(a,rowvar=False,ddof=1))
    def correlation(values):
        centered=values-values.mean(axis=0)
        norm=np.sqrt(np.sum(centered**2,axis=0))
        denom=np.outer(norm,norm)
        return np.divide(centered.T@centered,denom,out=np.full(denom.shape,np.nan),where=denom>0)
    def serial(m):
        return [[float(v) if np.isfinite(v) else None for v in row] for row in m]
    eig=np.linalg.eigvalsh(cov)
    return {"count":len(a),"covariance":serial(cov),"pearson":serial(correlation(a)),
            "spearman":serial(correlation(np.apply_along_axis(average_ranks,0,a))),
            "psd":bool(eig.min()>=-1e-12),"min_eigenvalue":float(eig.min())}


def portfolio_variance(covariance,weights):
    c=np.asarray(covariance,dtype=float)
    w=np.asarray(weights,dtype=float)
    if c.shape!=(len(w),len(w)) or not np.isfinite(c).all() or not np.isfinite(w).all():
        raise ValueError("Invalid covariance or weights")
    return float(w@c@w)


def training_transform(train,values):
    """Fit clipping and standardization on training observations only."""
    x=finite_values(train)
    if len(x)<2:
        return None
    low,high=np.quantile(x,[.01,.99])
    clipped=np.clip(x,low,high)
    scale=clipped.std(ddof=1)
    if scale<=0:
        return None
    return (np.clip(np.asarray(values,dtype=float),low,high)-clipped.mean())/scale


def rolling_statistics(values,benchmark,window,k):
    """Trailing complete windows; caller provides interval-aligned observations."""
    a=np.asarray(values,dtype=float)
    b=np.asarray(benchmark,dtype=float)
    if len(a)!=len(b) or window<2 or k<=0:
        raise ValueError("Invalid rolling inputs")
    result=[]
    for end in range(len(a)):
        x=a[max(0,end-window+1):end+1]
        y=b[max(0,end-window+1):end+1]
        row={"mean":None,"volatility":None,"beta":None,"correlation":None}
        if len(x)==window and np.isfinite(x).all():
            row.update(mean=float(x.mean()),volatility=float(x.std(ddof=1)*np.sqrt(k)))
            if np.isfinite(y).all() and y.var(ddof=1)>0:
                row["beta"]=float(np.cov(x,y,ddof=1)[0,1]/y.var(ddof=1))
                if x.std()>0:
                    row["correlation"]=float(np.corrcoef(x,y)[0,1])
        result.append(row)
    return result
