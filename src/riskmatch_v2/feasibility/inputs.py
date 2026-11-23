"""Dated market data, resampling and cross-sectional CHF risk estimates."""
from pathlib import Path
import json
from tempfile import TemporaryDirectory
from hashlib import sha256
import duckdb
import numpy as np
import pandas as pd
from scipy import sparse
from sklearn.covariance import LedoitWolf

from ..library.sources import checked

CFG = Path("config/faisabilite-5.json")
LOCAL = Path("data/local/5")
REPORT = Path("reports/05-faisabilite")


def factors(panel, factor_names, min_obs):
    """Pair each asset with the same dated factors, retain its own observation mask."""
    F=panel[factor_names].dropna()
    complete_days=panel.reindex(F.index)
    base=LedoitWolf().fit(F).covariance_*252
    loading=[]
    residual=[]
    means=[]
    counts={}
    names=[]
    for name in complete_days:
        y=complete_days[name].dropna()
        counts[name]=len(y)
        if len(y)<min_obs:
            continue
        X=F.loc[y.index].to_numpy()
        X=X-X.mean(axis=0)
        centered=y.to_numpy()-y.mean()
        beta,_,rank,_=np.linalg.lstsq(X,centered,rcond=None)
        if rank!=len(factor_names):
            continue
        resid=centered-X@beta
        loading.append(beta)
        residual.append(float(resid@resid/(len(y)-rank-1))*252)
        means.append(y.mean()*252)
        names.append(name)
    if not names:
        raise ValueError("No estimated risk")
    core=np.linalg.cholesky(base).T@np.array(loading).T
    root=sparse.vstack([sparse.csr_matrix(core),sparse.diags(np.sqrt(residual))],format="csc")
    return names,np.array(means),root,counts


def estimate(panel, method="LedoitWolf", shrink=.5):
    df=panel.dropna()
    if len(df)<2:
        raise ValueError("Less than two joint sessions")
    means=df.mean().to_numpy()*252
    if method=="factor":
        names,means,root,_=factors(panel,["SPY","IEF","GLD"],min(252,len(df)))
        if names!=list(panel.columns):
            raise ValueError("Inadequate factor coverage")
    else:
        if method=="LedoitWolf":
            cov=LedoitWolf().fit(df).covariance_*252
        elif method=="empirical":
            cov=np.atleast_2d(np.cov(df,rowvar=False))*252
        else:
            raise ValueError("Unknown estimate")
        vals,vec=np.linalg.eigh((cov+cov.T)/2)
        if vals.min() < -1e-10:
            raise ValueError("Indefinite covariance")
        root=sparse.csc_matrix(np.sqrt(vals.clip(0))[:,None]*vec.T)
    return (1-shrink)*means+shrink*np.median(means),root


def daily_inputs(cfg, signature):
    """Cache the full daily replay by its input hashes, separately from all mandates."""
    cat=Path("data/local/4")/cfg["catalogue"]
    base=pd.read_parquet(cat/"prices.parquet")
    base["symbol"]=base.id.str.split("-").str[-1]
    etf=base.pivot(index="day",columns="symbol",values="return_chf").sort_index()
    replay=pd.read_parquet(cat/"replay_2025.parquet")
    ids=replay.loc[replay.trading.eq("A"),["permno"]]
    folder=LOCAL/"cache"/signature
    folder.parent.mkdir(parents=True,exist_ok=True)
    path=folder/"daily.parquet"
    if not path.exists():
        raw=LOCAL/"raw/crsp_dsf.csv"
        checked(raw,cfg["sha256_crsp_dsf"])
        fx=pd.read_parquet(cat/"fx.parquet").set_index("day").value.reindex(etf.index)
        rates=(fx/fx.shift()).rename("ratio").reset_index()
        rates["prev"]=rates.day.shift()
        with TemporaryDirectory(dir=folder.parent) as tmp:
            target=Path(tmp)/"built"
            target.mkdir()
            con=duckdb.connect()
            con.register("active",ids)
            con.register("rates",rates)
            con.execute("SET threads=3")
            con.execute("""CREATE TEMP TABLE obs AS SELECT TRY_CAST(src.PERMNO AS INT) permno,
                DlyCalDt AS day, TRY_CAST(DlyRet AS DOUBLE) ret FROM read_csv(?,header=true,all_varchar=true) src
                JOIN active ON TRY_CAST(src.PERMNO AS INT)=active.permno
                WHERE DlyCalDt BETWEEN '2022-01-01' AND ?""",
                [str(raw),cfg["date_actions"]])
            con.execute("""CREATE TEMP TABLE dated AS SELECT permno,day,
                CASE WHEN count(*)=1 AND min(ret)>=-1 THEN min(ret) END ret
                FROM obs GROUP BY 1,2""")
            con.sql("""WITH chain AS (SELECT *,lag(day) OVER(PARTITION BY permno ORDER BY day) prev FROM dated)
                SELECT c.permno,c.day,(1+c.ret)*r.ratio-1 AS chf FROM chain c JOIN rates r
                ON c.day=r.day AND c.prev=r.prev JOIN read_parquet(?) m ON m.permno=c.permno
                AND date_trunc('month',m.day)=date_trunc('month',CAST(c.day AS DATE))
                WHERE c.ret IS NOT NULL AND r.ratio IS NOT NULL""",
                params=[str(cat/"stock_returns.parquet")]).write_parquet(str(target/"daily.parquet"),compression="zstd")
            con.close()
            try:
                target.rename(folder)
            except OSError:
                if not path.exists():
                    raise
    date=cfg["date_actions"]
    idx=etf.loc[:date].tail(504).index
    obs=pd.read_parquet(path,filters=[("day",">=",idx[0]),("day","<=",date)])
    stocks=obs.pivot(index="day",columns="permno",values="chf").reindex(index=idx,columns=ids.permno)
    stocks.columns=["PERMNO:"+str(x) for x in stocks.columns]
    return etf,etf.reindex(idx).join(stocks),cat


def signature(cfg):
    cat=Path("data/local/4")/cfg["catalogue"]
    manifest=json.loads((cat/"manifest.json").read_bytes())
    for f in ("prices.parquet","fx.parquet","decision.parquet","replay_2025.parquet","stock_returns.parquet"):
        checked(cat/f,manifest["products"][f])
    import importlib.metadata as meta
    versions={n:meta.version(n) for n in ["cvxpy","clarabel","scipy","scikit-learn","numpy","pandas","duckdb","pyarrow"]}
    key=sha256(Path(__file__).read_bytes()+CFG.read_bytes()+(cat/"manifest.json").read_bytes()+json.dumps(versions).encode()).hexdigest()
    return key[:20],versions
