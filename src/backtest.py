"""Walk-forward validation and prepared portfolio catalogue outputs (step 6)."""

from collections.abc import Mapping, Sequence

import numpy as np
import pandas as pd

CLIENT_SUMMARY_METRICS = (
    "historical_annualized_return_net",
    "realized_volatility",
    "net_sharpe",
    "max_drawdown",
    "annualized_cost",
)

TECHNICAL_METRICS = (
    "sortino",
    "calmar",
    "expected_shortfall_95",
    "turnover",
    "concentration",
    "tracking_error",
    "information_ratio",
    "realized_vs_reference_volatility",
)


def audit_strategy_calendar(
    streams: Mapping[str, pd.Series], dates: pd.DatetimeIndex, strategies: Sequence[str],
) -> pd.DataFrame:
    """Check a fixed comparison calendar without intersecting strategy histories."""
    if (not isinstance(dates, pd.DatetimeIndex) or dates.empty or dates.hasnans
            or not dates.is_unique or not dates.is_monotonic_increasing or dates.tz is not None
            or not dates.equals(dates.normalize())):
        raise ValueError("The comparison calendar must contain sorted unique session dates")
    if not strategies or len(set(strategies)) != len(strategies):
        raise ValueError("The strategy list must be nonempty and unique")

    rows = []
    for strategy in strategies:
        values = streams.get(strategy)
        if values is None:
            rows.append((strategy, "absent", len(dates), 0, 0))
            continue
        if (not isinstance(values, pd.Series) or not isinstance(values.index, pd.DatetimeIndex)
                or values.index.tz is not None or values.index.hasnans
                or not values.index.is_unique or not values.index.equals(values.index.normalize())
                or not pd.api.types.is_numeric_dtype(values)):
            raise ValueError(f"{strategy} returns require numeric values on unique session dates")
        missing = len(dates.difference(values.index))
        outside = len(values.index.difference(dates))
        common = values.loc[values.index.isin(dates)].to_numpy(dtype=float, na_value=np.nan)
        invalid = int((~np.isfinite(common)).sum())
        rows.append((strategy, "ready" if missing == invalid == 0 else "incomplete",
                     missing, invalid, outside))

    return pd.DataFrame(rows, columns=[
        "strategy", "status", "missing_sessions", "invalid_returns", "outside_sessions",
    ]).set_index("strategy")


def aligned_strategy_returns(
    streams: Mapping[str, pd.Series], dates: pd.DatetimeIndex, strategies: Sequence[str],
) -> pd.DataFrame:
    """Build the comparison panel only if every configured strategy covers it."""
    report = audit_strategy_calendar(streams, dates, strategies)
    pending = report.index[report["status"].ne("ready")].tolist()
    if pending:
        raise ValueError(f"Incomplete common-period returns: {', '.join(pending)}")
    return pd.DataFrame({name: streams[name].reindex(dates) for name in strategies}, index=dates)

