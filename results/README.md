# Results

This directory contains only the reproducible outputs used by the application: weights, metrics, walk-forward backtests, the prepared portfolio catalogue, and anonymized monitoring data.

The primary application artifact is `portfolio_catalogue.parquet`, with one dated and versioned row per `risk_band × strategy`. Each row must include:

- category range, reference volatility, and achieved volatility;
- target weights and strategy identifier;
- one common historical comparison period;
- historical annualized return net of costs, realized volatility, net Sharpe ratio, maximum drawdown, and annualized cost;
- technical metrics and links to the underlying value series;
- prespecified advantages and limitations;
- data timestamp, configuration version, and backtest version.

Historical evidence shown at selection time must remain frozen. Live performance since selection is a separate monitoring artifact and must never overwrite the backtest summary.

Locally generated results are not version-controlled by default. To share a result required for the demonstration, add a small, documented, reproducible file that contains no personal data.

