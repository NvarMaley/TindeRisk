"""Re-optimize a strategy on eligible assets and enforce final ETF weights."""

from collections.abc import Sequence
from dataclasses import dataclass
from math import isfinite

import pandas as pd

from .baselines import benchmark_60_40_weights
from .classic import classic_weights
from .connected import connected_portfolio
from .optim import TargetAllocation, capped_erc, target_vol, vol
from .profiling import RiskBand, volatility_band_position

_SECTORS = {"XLK", "XLF", "XLE", "XLV", "XLY", "XLP", "XLI", "XLB", "XLU"}
_EXCLUSION_GROUPS = {"energy": ("XLE",), "gold": ("GLD",), "treasuries": ("IEF", "TLT")}


class NoEligibleAssetsError(ValueError):
    """All risky assets of the requested strategy were excluded."""


def resolve_client_exclusions(choices: Sequence[str] | None, *, benchmark_equity: str = "SPY") -> tuple[str, ...]:
    """Translate resolved questionnaire exclusions into ineligible ETF tickers."""
    if choices is None:
        raise ValueError("client exclusions must be resolved")
    excluded = set()
    for choice in choices:
        if choice not in _EXCLUSION_GROUPS and choice not in _SECTORS:
            raise ValueError(f"unknown client exclusion: {choice}")
        excluded.update(_EXCLUSION_GROUPS.get(choice, (choice,)))
    if excluded.intersection(_SECTORS):
        excluded.add(benchmark_equity)
    return tuple(sorted(excluded))


@dataclass(frozen=True)
class ClientAllocation:
    band: RiskBand
    target_volatility: float
    allocation: TargetAllocation
    method: str

    @property
    def target_shortfall(self) -> float:
        return max(0., self.band.reference_volatility - self.allocation.achieved_volatility)

    @property
    def reference_gap(self) -> float:
        return self.allocation.achieved_volatility - self.band.reference_volatility

    @property
    def band_position(self) -> str:
        return volatility_band_position(self.allocation.achieved_volatility, self.band)


def reoptimize_for_client(
    strategy: str, annual_covariance: pd.DataFrame, band: RiskBand, *,
    excluded_assets: Sequence[str] = (), max_etf_weight: float | None, allow_borrowing: bool,
    leverage_limit: float = 1.5, capacity_volatility: float | None = None,
    annual_excess_mean: pd.Series | None = None, reference_sharpe: float = .35,
    views: tuple[pd.DataFrame, pd.Series, pd.DataFrame] | None = None,
    benchmark_equity: str = "SPY",
) -> ClientAllocation:
    """Fit the eligible risky sleeve, then enforce the actual capital and risk limits."""
    if strategy not in {"classic", "erc", "black_litterman", "benchmark_60_40"}:
        raise ValueError(f"unsupported client strategy: {strategy}")
    if not isinstance(allow_borrowing, bool):
        raise ValueError("client borrowing permission must be resolved")
    if not isfinite(leverage_limit) or leverage_limit < 1:
        raise ValueError("leverage limit must be finite and at least 1")
    if max_etf_weight is None:
        raise ValueError("client ETF cap must be resolved")
    if not isfinite(max_etf_weight) or not 0 < max_etf_weight <= 1:
        raise ValueError("maximum ETF weight must be in (0, 1]")
    reference = band.reference_volatility
    if not isfinite(reference) or reference <= 0:
        raise ValueError("reference volatility must be positive and finite")
    if capacity_volatility is not None and (not isfinite(capacity_volatility) or capacity_volatility < 0):
        raise ValueError("client capacity must be finite and nonnegative")
    target = reference if capacity_volatility is None else min(reference, capacity_volatility)
    exposure_limit = leverage_limit if allow_borrowing else 1.

    labels = annual_covariance.columns
    if not labels.is_unique or not annual_covariance.index.equals(labels):
        raise ValueError("covariance must have matching unique asset labels")
    strategy_assets = benchmark_60_40_weights(benchmark_equity).index if strategy == "benchmark_60_40" else labels
    if not strategy_assets.isin(labels).all():
        raise ValueError("covariance must cover all strategy assets")
    eligible = strategy_assets[~strategy_assets.isin(excluded_assets)]
    if eligible.empty:
        raise NoEligibleAssetsError("no eligible ETF remains for this strategy")
    covariance = annual_covariance.loc[eligible, eligible]

    connected_views = {}
    if views is not None:
        if strategy != "black_litterman":
            raise ValueError("views apply only to Connected")
        p, q, omega = views
        if (not p.columns.equals(labels) or not p.index.is_unique or not q.index.equals(p.index)
                or not omega.index.equals(p.index) or not omega.columns.equals(p.index)):
            raise ValueError("views must align with the original portfolio universe")
        forbidden = labels[~labels.isin(eligible)]
        kept = p.index[p.loc[:, forbidden].eq(0).all(axis=1)]
        connected_views = {"p": p.loc[kept, eligible], "q": q.loc[kept], "omega": omega.loc[kept, kept]}

    def fit(cap: float) -> tuple[pd.Series, str]:
        if strategy == "classic":
            if annual_excess_mean is None or not annual_excess_mean.index.equals(labels):
                raise ValueError("Classic requires expected excess returns for the original universe")
            return classic_weights(annual_excess_mean.loc[eligible], covariance, cap)
        weights = capped_erc(covariance, cap)
        if strategy == "black_litterman":
            connected = connected_portfolio(weights, covariance, reference_sharpe=reference_sharpe,
                                            max_weight=cap, **connected_views)
            return connected.weights, "connected" if connected.tau is not None else "connected_no_views"
        return weights, "erc"

    if strategy == "benchmark_60_40":
        mix = benchmark_60_40_weights(benchmark_equity).loc[eligible]
        weights, method = mix / mix.sum(), "benchmark_eligible_mix"
    else:
        weights, method = fit(1.)
        requested_exposure = min(exposure_limit, target / vol(weights, covariance))
        if requested_exposure * weights.max() > max_etf_weight:
            sleeve_cap = max(1 / len(eligible), max_etf_weight / requested_exposure)
            weights, method = fit(sleeve_cap)

    scaled = target_vol(weights, covariance, target, max_risky_exposure=exposure_limit,
                        max_etf_weight=max_etf_weight)
    final_weights = scaled.risky_weights.reindex(labels, fill_value=0.)
    allocation = TargetAllocation(final_weights, scaled.cash_weight, vol(final_weights, annual_covariance))
    return ClientAllocation(band, target, allocation, method)
