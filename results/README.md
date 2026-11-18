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

Step 2.1 asset diagnostics are generated with `python -m src.build_descriptive`
as `2_1_main_descriptive_stats.csv`, `2_1_extended_descriptive_stats.csv` and
`2_1_manifest.json`. These are historical gross asset/reference statistics,
not strategy backtests or portfolio-card evidence. The 60/40 row is a daily
reference, not the monthly production strategy. See
[the definitions and correction notes](../docs/10_DESCRIPTIVE_STATISTICS.md).

