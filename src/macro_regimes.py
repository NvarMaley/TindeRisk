"""Select a monthly Gaussian HMM on macro training data."""

from collections.abc import Sequence

from hmmlearn.hmm import GaussianHMM
import numpy as np
import pandas as pd
import pandas_market_calendars as mcal
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits


def macro_month_ends(daily: pd.DataFrame, start, end) -> pd.DataFrame:
    """Sample publication-lagged features on completed NYSE month-end sessions."""
    start, end = pd.Timestamp(start), pd.Timestamp(end)
    if pd.isna(start) or pd.isna(end) or start > end:
        raise ValueError("The macro training bounds must be valid and chronological")
    if (not isinstance(daily.index, pd.DatetimeIndex) or daily.index.tz is not None
            or daily.index.hasnans or not daily.index.is_unique or daily.columns.has_duplicates):
        raise ValueError("Macro input requires unique timezone-naive dates and feature labels")
    dates = mcal.get_calendar("NYSE").valid_days(
        start.to_period("M").start_time, end.to_period("M").end_time.normalize(), tz=None,
    )
    month_ends = dates[~dates.to_period("M").duplicated(keep="last")]
    month_ends = month_ends[(month_ends >= start) & (month_ends <= end)]
    panel = daily.reindex(month_ends)
    if not np.isfinite(panel.to_numpy(dtype=float)).all():
        raise ValueError("Every completed training month needs complete macro observations")
    return panel


def select_macro_hmm(
    training: pd.DataFrame,
    *,
    candidates: Sequence[int] = (3, 4),
    seeds: Sequence[int] = tuple(range(12)),
) -> tuple[GaussianHMM, StandardScaler, pd.DataFrame]:
    """Fit each state count with multiple seeds and select the lowest BIC."""
    if (not candidates or len(set(candidates)) != len(candidates)
            or min(candidates) < 2 or not seeds or len(set(seeds)) != len(seeds)):
        raise ValueError("Provide distinct state counts and initialization seeds")
    months = pd.DatetimeIndex(training.index).to_period("M")
    if (len(months) < 12 or months.hasnans or not months.equals(
        pd.period_range(months[0], periods=len(months), freq="M")
    )):
        raise ValueError("HMM training requires at least 12 consecutive months in time order")
    values = training.to_numpy(dtype=float)
    if (values.shape[1] == 0 or not np.isfinite(values).all()
            or (np.ptp(values, axis=0) == 0).any()):
        raise ValueError("HMM features must be finite and nonconstant")
    scaler = StandardScaler().fit(training)
    z = scaler.transform(training)

    models, rows = {}, []
    # Parallel K-means starts add overhead for this small monthly panel.
    with threadpool_limits(limits=1):
        for states in candidates:
            fits = []
            for seed in seeds:
                model = GaussianHMM(
                    n_components=states, covariance_type="diag", n_iter=300,
                    tol=1e-4, random_state=seed,
                ).fit(z)
                history = model.monitor_.history
                gain = history[-1] - history[-2] if len(history) > 1 else np.inf
                likelihood = model.score(z)
                if np.isfinite(likelihood) and -1e-6 <= gain < model.tol:
                    fits.append((likelihood, seed, model))
            if not fits:
                raise RuntimeError(f"No converged HMM fit for {states} states")
            likelihood, seed, best = max(fits, key=lambda fit: fit[0])
            models[states] = best
            rows.append({
                "states": states, "months": len(z), "converged_starts": len(fits),
                "total_starts": len(seeds), "best_seed": seed,
                "log_likelihood": likelihood, "bic": best.bic(z),
            })

    comparison = pd.DataFrame(rows).set_index("states").sort_index()
    comparison["delta_bic"] = comparison["bic"] - comparison["bic"].min()
    return models[comparison["bic"].idxmin()], scaler, comparison
