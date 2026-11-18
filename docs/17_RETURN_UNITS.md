# Step 2.7 · Return and risk units

Run the independent 2.7 notebook cell or `python -m src.check_return_units`
with the prepared common samples. The command verifies source hashes and
date and ticker alignment, then saves `results/2_7_return_units.json`.
It uses local data and the existing 252-session reporting convention.

| Quantity | Check |
| --- | --- |
| Simple daily return | Recover it as `expm1(log_return)` or as `daily_excess + daily_cash`. |
| Annual arithmetic excess mean | Multiply the daily excess mean by 252. Dividing it by annualized volatility reproduces the reported Sharpe. |
| Annual geometric return | Compound with `expm1(mean(log_return) × 252)`. Alternating +2% and −2% gives a zero arithmetic mean and a negative geometric return. |
| Variance and volatility | Multiply daily variance or covariance by 252 and daily volatility by √252. The annual covariance diagonal equals annual volatility squared. |
| Portfolio risk | Compare √(w′Σw) with the annualized sample standard deviation of the daily weighted simple returns. The audit uses constant equal weights across all 13 columns, including SPY, as an algebraic check. |
| Ledoit–Wolf | The annualized matrix is 252 times the daily matrix and both use the same shrinkage intensity. |

| Sample | Asset-day entries | Maximum simple/log error | Maximum simple/excess error |
| --- | ---: | ---: | ---: |
| Main | 33,514 | 9.61 × 10⁻¹⁶ | 1.73 × 10⁻¹⁸ |
| Extended | 58,461 | 9.66 × 10⁻¹⁶ | 3.47 × 10⁻¹⁸ |

The samples overlap. The errors are expressed in decimal return units and
are within floating-point rounding. Regression tests cover signed
compounding, portfolio variance and volatility, and deliberately corrupted
input units and labels. The square-root scaling is the project's reporting
convention, while the serial dependence documented in 2.6 matters for
interpreting risk over longer holding periods. The daily cash input uses the
existing DTB3 proxy.
