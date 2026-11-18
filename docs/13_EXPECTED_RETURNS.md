# Step 2.3 — Conservative expected-return implementation

## Choice and scope

The Classic implementation default is **regularized Bayes–Stein-style
shrinkage toward the GMV mean**, adapted from Raf's step 2.3 notebook. This
implements the shrunk-mean option in README §2.3. It keeps Classic distinct
from Black–Litterman without requiring an unvalidated ERC optimizer here.
An implied-return prior remains an alternative for later robustness analysis;
it is not silently implemented with an equal-weight proxy for the approved ERC
anchor. ERC and production Classic optimization remain separate tasks.

This is an implementation decision based on explicit structure, not a claim
that it wins a predictive or portfolio-return comparison. The final holdout
is still unset (0.11); legacy notebook outputs already contain full-period
next-12-month comparisons, so those periods cannot be described retroactively
as untouched confirmatory tests. We do not reuse those scores to choose this
method or fit a hyperparameter.

## Formula and units

At each completed NYSE month-end close, use T = 756 trailing observations
(including that close, usable only afterward) for the 12 investable ETFs.
SPY is excluded from the estimate. The shared 3-year window comes from config.

Let m be the vector of **daily arithmetic mean excess returns**, calculated
using the project's existing DTB3 proxy. Let S be the **daily** Ledoit–Wolf
constant-correlation covariance of simple asset returns, with the same ddof=1
convention as step 2.2. Calculate with linear solves, never an explicit inverse:

```
a = solve(S, 1)
w_ref = a / sum(a)
m0 = w_ref' m
d = m - m0 * 1
q = d' solve(S, d)
k = (p + 2) / (p + 2 + T * q)
mu_daily = (1 - k) * m + k * m0 * 1
mu_annual_excess = 252 * mu_daily
```

Here p is the number of investable assets and k is the **mean** shrinkage
intensity; it differs from Ledoit–Wolf covariance shrinkage. If all means are
equal, q = 0, k = 1 and the means are unchanged. Covariance must be finite,
symmetric and positive definite; labels must match exactly.

The rule is inspired by Raf's Jorion (1986) / Bayes–Stein implementation, but
uses a regularized asset-risk covariance. It is explicitly a **regularized
variant**, not an exact finite-sample theorem for Jorion's original estimator.
Unlike the old notebook, S is computed on simple asset returns, consistent
with step 2.2, rather than on rate-subtracted returns. This choice separates
asset risk from the varying cash proxy; subtracting a time-varying rate is not
an identity transformation of covariance.

`w_ref` is an **unconstrained mathematical GMV reference**, potentially with
negative weights. It is not the production long-only GMV allocation, not the
ERC anchor, and not a portfolio made available to the client. Its weighted
mean may lie outside the range of individual sample means.

“Conservative” here means reducing cross-sectional differences in estimated
means. For every pair i,j, the difference is multiplied by (1-k), and the
cross-sectional standard deviation is also multiplied by (1-k). This does
not necessarily reduce every asset's mean, the overall level, losses or
portfolio risk. Means may remain negative. There is no zero floor, ad-hoc
return cap, guaranteed positive Sharpe or promised return.

The output is **annual arithmetic excess return in decimal units**, not CAGR
and not total return. The future optimizer must consume excess means directly
or add the appropriate cash rate once if it explicitly requires total means.
Covariance and mean must use the same asset order and decision date.

## Reproduction and outputs

Run after `python -m src.build_common_sample`:

```
python -m src.build_expected_returns
make check
```

The builder verifies the full excess-return source hash and both per-period
return/warm-up hashes against the common-sample manifest. It extracts excess
returns on those exact dates, checks alignment, and excludes partial final
months using the NYSE calendar. No future returns or next-year scores are used.

For each main/extended period it writes ignored local artifacts:

- `results/2_3_<period>_mu.csv`: selected shrunk annual excess estimates;
- `results/2_3_<period>_raw_mean_control.csv`: raw means for diagnostics only;
- `results/2_3_<period>_diagnostics.csv`: exact windows, count, target, two
  shrinkage coefficients, covariance-metric distance and dispersion;
- `results/2_3_<period>_diagnostics.png`: latest comparison and shrinkage history.

`results/2_3_manifest.json` records configuration, input-manifest/source and
output hashes, versions, units, timing and unresolved validation limits.
The notebook's saved step 2.3 outputs remain explicitly labelled legacy and
its later cells are not certified by this builder.

## Validation and remaining gates

Tests cover a hand-calculable diagonal covariance; equal means; translation,
unit scaling and asset permutation; invalid/singular covariance and mismatched
labels; daily-to-annual conversion; exact trailing windows; future-data
perturbations; source checksums and partial-month exclusion.

DTB3 same-date timing and cash accrual are still unresolved before final
backtesting. Shrinkage does not eliminate source revision issues. Fix the
train/validation/test protocol before comparing forecasting or portfolio
performance. No allocation backtest, cost model or implied-ERC implementation
is certified by this step.

## Verified build — 2026-11-18

| Diagnostic | Main | Extended |
|---|---:|---:|
| Estimation dates | 123 | 214 |
| Last estimate | 2020-03-31 | 2026-10-30 |
| Mean shrinkage intensity | 62.56% | 63.80% |
| Minimum / maximum intensity | 40.19% / 88.53% | 40.19% / 90.18% |
| Cross-sectional dispersion reduced | Every date | Every date |

These are implementation diagnostics, not predictive scores. All 337 windows
were separately checked using the inverse-matrix expression of the same rule
(the implementation uses solves), and their raw means were checked directly
against the exact source windows. Output hashes were verified and both PNGs
visually inspected. `make check` passes **96 tests**, including 11 new tests.
