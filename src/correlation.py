"""Descriptive correlations, never predictive signals or strategy results."""

import pandas as pd

from .estimation import validate_returns


def correlation_diagnostics(returns: pd.DataFrame, *, benchmark: str,
                            diversifiers: list[str], window: int = 252):
    """Pearson heatmap and trailing full-window correlations within one sample.

    Initial window-1 rows remain NaN; do not silently warm up with another
    period. Daily asset returns are unscaled (correlation is dimensionless).
    """
    validate_returns(returns)
    if not isinstance(window, int) or window < 2:
        raise ValueError("window must be an integer of at least 2")
    if not diversifiers or len(set(diversifiers)) != len(diversifiers):
        raise ValueError("diversifiers must be nonempty and unique")
    if benchmark not in returns or any(asset not in returns for asset in diversifiers):
        raise ValueError("benchmark and diversifiers must belong to returns")
    rolling = pd.DataFrame({f"{benchmark}/{asset}": returns[benchmark].rolling(
        window, min_periods=window).corr(returns[asset]) for asset in diversifiers})
    return returns.corr(), rolling
