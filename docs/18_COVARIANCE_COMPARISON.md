# Step 2.8 · Sample covariance and Ledoit–Wolf

This comparison holds the GMV allocation problem fixed and varies its
covariance estimate. Both versions use 756 trailing daily returns through
each Step 2.5 decision close, the same twelve ETFs, long-only fully invested
weights and the configured 35% target cap. The Ledoit–Wolf target assumes
constant correlation. Its weights are checked against Step 2.5.

Each target starts earning returns the following session. Holdings drift
until the next rebalance. Two-way turnover is the sum of absolute differences
between the new target and drifted holdings after the closing returns. The
initial allocation has no turnover observation. Target distance between
estimators is half the sum of absolute weight differences at a common close.
Asset-level weights and their signed differences are exported.

Forecast volatility is the square root of the covariance projected onto
the new weights, in annualized units. Realized volatility is the sample
standard deviation of the following month's daily gross portfolio returns
multiplied by √252. The error is forecast minus realization. The final
partial month of the extended sample is exported with its weights and
timing, and omitted from the summary. There are 122 and 213 scored turnover
events for the main and extended samples respectively.

| Sample | Estimator | Complete months | Median condition number | Mean monthly two-way turnover | Volatility MAE | Volatility RMSE |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Main | Sample | 123 | 509.5 | 4.283% | 1.734 pp | 2.791 pp |
| Main | Ledoit–Wolf | 123 | 442.8 | 4.282% | 1.758 pp | 2.801 pp |
| Extended | Sample | 214 | 512.6 | 4.288% | 1.740 pp | 2.567 pp |
| Extended | Ledoit–Wolf | 214 | 443.4 | 4.282% | 1.748 pp | 2.563 pp |

On average, moving from one estimator to the other reallocates 0.74% of the
portfolio in the main sample and 0.97% in the extended sample. Shrinkage
improves conditioning in both samples. The turnover and forecast error
differences are small. This comparison uses overlapping historical samples
before transaction costs, with no holdout claim.

Run the independent notebook cell, or run `python -m src.build_baselines`
then `python -m src.build_covariance_comparison`. The summary, monthly
diagnostics, allocations, asset-level differences and hash manifest are
saved in `results/`. The regression test checks drift, close-to-next-session
timing, forecast variance and partial-month handling on hand-calculated data.
