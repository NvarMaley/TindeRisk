"""Select and filter a monthly Gaussian HMM on macro data."""

from collections.abc import Sequence

from hmmlearn.hmm import GaussianHMM
import numpy as np
import pandas as pd
import pandas_market_calendars as mcal
from scipy.optimize import linear_sum_assignment
from scipy.special import logsumexp
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits

from .data_loader import MACRO_TRANSFORMS, next_market_session


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


def filtered_state_probabilities(model: GaussianHMM, observations: np.ndarray) -> np.ndarray:
    """Evaluate P(state_t | observations through t) using only forward updates."""
    z = np.asarray(observations, dtype=float)
    if (model.covariance_type != "diag" or z.ndim != 2 or len(z) == 0
            or z.shape[1] != model.means_.shape[1] or not np.isfinite(z).all()):
        raise ValueError("Filtering requires a diagonal HMM and finite observations")
    variances = np.diagonal(model.covars_, axis1=1, axis2=2)
    if not np.isfinite(variances).all() or (variances <= 0).any():
        raise ValueError("Each state requires positive, finite emission variances")
    distance = z[:, None, :] - model.means_[None, :, :]
    emissions = -0.5 * (np.log(2 * np.pi * variances) + distance**2 / variances).sum(axis=2)
    with np.errstate(divide="ignore"):
        log_start = np.log(model.startprob_)
        log_transitions = np.log(model.transmat_)
    result = np.empty_like(emissions)
    log_prior = log_start
    for i, emission in enumerate(emissions):
        log_joint = log_prior + emission
        normalizer = logsumexp(log_joint)
        if not np.isfinite(normalizer):
            raise ValueError("The HMM assigns no probability to the observed sequence")
        log_filtered = log_joint - normalizer
        result[i] = np.exp(log_filtered)
        log_prior = logsumexp(log_filtered[:, None] + log_transitions, axis=0)
    return result


def expanding_regime_probabilities(
    panel: pd.DataFrame,
    *,
    first_observation,
    states: int,
    seeds: Sequence[int] = tuple(range(12)),
) -> pd.DataFrame:
    """Re-estimate before each month, then filter through that month's observation."""
    dates = panel.index
    if (not isinstance(dates, pd.DatetimeIndex) or dates.hasnans
            or dates.tz is not None or not dates.is_unique or not dates.is_monotonic_increasing):
        raise ValueError("Regime observations require sorted, unique timezone-naive dates")
    first = dates.get_indexer([pd.Timestamp(first_observation)])[0]
    if first < 12:
        raise ValueError("The first prediction must follow at least 12 training months")
    if not dates.to_period("M").equals(pd.period_range(dates[0], periods=len(dates), freq="M")):
        raise ValueError("Regime observations must be consecutive months")

    rows = []
    for position in range(first, len(dates)):
        train = panel.iloc[:position]
        model, scaler, comparison = select_macro_hmm(train, candidates=(states,), seeds=seeds)
        if position == first:
            reference_means, reference_scaler = model.means_.copy(), scaler
        means = (scaler.inverse_transform(model.means_) - reference_scaler.mean_) / reference_scaler.scale_
        distances = ((reference_means[:, None, :] - means[None, :, :])**2).sum(axis=2)
        order = linear_sum_assignment(distances)[1]
        z = scaler.transform(panel.iloc[:position + 1])
        probabilities = filtered_state_probabilities(model, z)[-1, order]
        rows.append({
            "train_through": dates[position - 1], "train_months": position,
            "converged_starts": comparison.loc[states, "converged_starts"],
            **{f"state_{j}": value for j, value in enumerate(probabilities)},
        })
    result = pd.DataFrame(rows, index=dates[first:].rename("observation_date"))
    result.insert(0, "available_date", next_market_session(result.index))
    return result


def macro_regime_profiles(
    model: GaussianHMM, scaler: StandardScaler, training: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Describe a fixed fit in standard deviations and original reporting units."""
    z = scaler.transform(training)
    states = pd.Index([f"state_{i}" for i in range(model.n_components)], name="state")
    standardized = pd.DataFrame(model.means_, index=states, columns=training.columns)
    profile = pd.DataFrame(
        scaler.inverse_transform(model.means_), index=states, columns=training.columns,
    )
    for column in training.columns:
        transform = MACRO_TRANSFORMS.get(column)
        if transform == "log":
            profile[column] = np.exp(profile[column])
        elif transform == "yoy":
            profile[column] = 100 * profile[column]

    probabilities = filtered_state_probabilities(model, z)
    profile["mean_filtered_probability"] = probabilities.mean(axis=0)
    profile["dominant_months"] = np.bincount(probabilities.argmax(axis=1), minlength=len(states))
    profile["self_transition"] = np.diag(model.transmat_)
    return standardized, profile
