"""Asset-level historical diagnostics extracted from Raf's Step 2.1 notebook."""

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.diagnostic import acorr_ljungbox


def max_drawdown(returns: pd.Series) -> float:
    """Signed peak-to-trough loss including the initial unit wealth."""
    values = returns.to_numpy(dtype=float)
    if not len(values) or not np.isfinite(values).all() or (values <= -1).any():
        raise ValueError("drawdown needs finite nonempty returns strictly above -1")
    wealth = np.r_[1., np.cumprod(1 + values)]
    return float((wealth / np.maximum.accumulate(wealth) - 1).min())


def descriptive_statistics(returns: pd.DataFrame, rf_daily: pd.Series, annualize=252) -> pd.DataFrame:
    """Preserve Raf's conventions; CAGR is geometric, Sharpe uses asset std.

    VaR/ES are signed lower-tail daily returns, not positive loss magnitudes.
    Undefined statistics for constant series stay NaN, not infinite Sharpe.
    """
    if len(returns) < 12 or returns.shape[1] == 0 or annualize <= 0:
        raise ValueError("at least 12 observations, one asset and positive annualization required")
    if not returns.index.is_unique or not returns.index.is_monotonic_increasing or returns.columns.duplicated().any():
        raise ValueError("returns need sorted unique dates and unique asset columns")
    if not returns.index.equals(rf_daily.index):
        raise ValueError("risk-free dates must exactly match return dates")
    if not np.isfinite(returns.to_numpy(dtype=float)).all() or not np.isfinite(rf_daily.to_numpy(dtype=float)).all():
        raise ValueError("returns and risk-free rates must be finite and complete")
    if returns.le(-1).any().any():
        raise ValueError("returns must be strictly above -1")
    rows = {}
    for asset in returns:
        r = returns[asset]
        std = r.std(ddof=1)
        variable = r.nunique() > 1
        quantile = r.quantile(.05)
        rows[asset] = {
            "ann_return": float(np.expm1(np.log1p(r).sum() * annualize / len(r))),
            "ann_vol": std * np.sqrt(annualize),
            "sharpe": (r-rf_daily).mean() / std * np.sqrt(annualize) if variable else np.nan,
            "skew": stats.skew(r) if variable else np.nan,
            "ex_kurtosis": stats.kurtosis(r) if variable else np.nan,
            "JB_pvalue": stats.jarque_bera(r).pvalue if variable else np.nan,
            "AC1": r.autocorr(1) if variable else np.nan,
            "LB10_pvalue": acorr_ljungbox(r, lags=[10], return_df=True).lb_pvalue.iloc[0] if variable else np.nan,
            "LB10_sq_pval": acorr_ljungbox(r**2, lags=[10], return_df=True).lb_pvalue.iloc[0] if (r**2).nunique() > 1 else np.nan,
            "max_drawdown": max_drawdown(r),
            "VaR95_daily": quantile,
            "ES95_daily": r[r <= quantile].mean(),
        }
    result = pd.DataFrame.from_dict(rows, orient="index")
    result.index.name = "asset"
    return result
