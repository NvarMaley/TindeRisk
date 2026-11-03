"""Walk-forward validation and prepared portfolio catalogue outputs (step 6)."""

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

