# Step 2.5 · Monthly reference portfolios

The three reference portfolios use the same trading sessions within each
common sample. Run the independent 2.5 notebook cell to regenerate and view
the summary, or run `python -m src.build_baselines` from the project root.

| Portfolio | Target at each rebalance |
| --- | --- |
| Equal weight | 1/12 in each investable ETF |
| GMV | Minimum variance over the 12 investable ETFs, fully invested, long-only, with a 35% cap per asset at rebalancing |
| 60/40 | 60% in SPY and 40% in IEF, as defined for the benchmark |

GMV uses 756 daily simple returns through the decision close and Ledoit–Wolf
covariance with a constant-correlation target. The optimizer uses no estimate
of expected returns. The 35% limit is the portfolio setting in config and
applies to GMV target weights. Holdings can drift above a target between
rebalances. The fixed 60/40 benchmark follows its own stated weights.

The first target is set at the last NYSE close before the sample starts.
Later targets are set at actual NYSE month-end closes, with new weights
earning returns from the next session. Between closes, each holding grows
with its own return and weights drift accordingly. The extended sample
includes its final partial month with weights formed at the previous month-end.

| Period | Portfolio | Annualized return | Annualized volatility | Sharpe | Max drawdown |
| --- | --- | ---: | ---: | ---: | ---: |
| Main | Equal weight | 8.95% | 11.73% | 0.74 | −27.10% |
| Main | GMV | 8.73% | 5.79% | 1.38 | −12.35% |
| Main | 60/40 | 8.93% | 8.97% | 0.93 | −18.89% |
| Extended | Equal weight | 11.46% | 12.55% | 0.81 | −27.10% |
| Extended | GMV | 7.01% | 6.79% | 0.82 | −19.51% |
| Extended | 60/40 | 9.63% | 10.17% | 0.81 | −21.28% |

The main sample has 2,578 sessions and the extended sample has 4,497.
The results are gross of trading costs. Sharpe uses the Step 2.1 convention,
including the descriptive DTB3 proxy. The two samples overlap. Final
out-of-sample evaluation and execution assumptions belong to Step 6.

The builder verifies the source hashes and session coverage, then exports
`2_5_summary.csv`, dated targets, daily returns and wealth for each period,
and a hash manifest in `results/`. This 60/40 series uses monthly rebalancing.
Step 2.1 continues to use a daily rebalanced 60/40 illustration.
