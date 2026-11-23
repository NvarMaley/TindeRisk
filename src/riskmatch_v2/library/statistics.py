"""Monthly risk sheets using one actual month-end observation per security."""
import numpy as np
import pandas as pd


def sheet(months, returns, fx, dates):
    """months consecutive; returns in USD. FX at both endpoints on the true dates."""
    local = np.asarray(returns,dtype=float)
    rates = np.asarray(fx,dtype=float)
    if len(local) != months or len(rates) != months + 1 or len(dates) != months+1:
        raise ValueError("Incoherent window calendar")
    if ((rates<=0) | np.isinf(rates)).any():
        raise ValueError("Invalid exchange rates")
    gross = 1 + local
    with np.errstate(divide="ignore", invalid="ignore"):
        monthly = gross * rates[1:] / rates[:-1] - 1
    valid = np.isfinite(monthly) & (gross >= 0)
    sample = monthly[valid]
    n = len(sample)
    out = dict(expected=months, observations=n, first_return=None, last_return=None,
               full_sample=n==months, mean=None, annual_mean=None, variance=None, volatility=None,
               cumulative=None, cagr=None, max_drawdown=None, peak=None, trough=None, recovery=None,
               recovery_days=None, trough_to_recovery_days=None, observed_levels=int(np.isfinite(rates).sum()), recovery_state="unavailable", tail_n=0, es95=None,
               skew=None, excess_kurtosis=None)
    if n:
        out.update(first_return=str(dates[1:][np.flatnonzero(valid)[0]])[:10],
                   last_return=str(dates[1:][np.flatnonzero(valid)[-1]])[:10],
                   mean=float(sample.mean()), annual_mean=float(sample.mean()*12))
        tail = sample[sample <= np.quantile(sample,.05)]
        out.update(tail_n=len(tail), es95=float(-tail.mean()))
    if n>1:
        variance=float(sample.var(ddof=1)*12)
        out.update(variance=variance, volatility=variance**.5)
    if n>=4 and sample.std()>0:
        z=(sample-sample.mean())/sample.std()
        out.update(skew=float(np.mean(z**3)), excess_kurtosis=float(np.mean(z**4)-3))
    # Intermediate missing FX does not erase USD wealth. A missing local return does.
    if not np.isfinite(gross).all() or (gross<0).any() or not np.isfinite(rates[[0,-1]]).all():
        return out
    levels=np.r_[1.,np.cumprod(gross)]*rates/rates[0]
    observed=np.isfinite(levels)
    x=levels[observed]
    d=np.asarray(dates,dtype="datetime64[D]")[observed]
    draw=x/np.maximum.accumulate(x)-1
    trough=int(np.argmin(draw))
    peak=int(np.flatnonzero(x[:trough+1]==x[:trough+1].max())[-1])
    regained=np.flatnonzero(x[trough:] >= x[peak])
    out.update(cumulative=float(x[-1]-1),cagr=float(x[-1]**(12/months)-1),
               max_drawdown=float(draw[trough]), peak=str(d[peak]),trough=str(d[trough]),
               recovery_state="unrecovered" if not len(regained) else "recovered")
    if len(regained):
        end=trough+regained[0]
        out.update(recovery=str(d[end]),recovery_days=int((d[end]-d[peak]).astype(int)),
                   trough_to_recovery_days=int((d[end]-d[trough]).astype(int)))
    return out
