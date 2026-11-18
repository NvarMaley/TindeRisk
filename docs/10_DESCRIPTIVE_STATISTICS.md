# Step 2.1 — Reproducing Raf's asset diagnostics

Raf's notebook already implemented the descriptive table. The reusable
[statistics module](../src/descriptive.py) retains its columns and conventions:

| Column | Definition |
|---|---|
| `ann_return` | Geometric annualization `(product(1+r)) ** (252/n) - 1`; not arithmetic mean |
| `ann_vol` | Sample daily standard deviation (`ddof=1`) × sqrt(252) |
| `sharpe` | Mean daily excess return / sample standard deviation of asset returns × sqrt(252), as in Raf's notebook |
| `skew`, `ex_kurtosis` | SciPy's default moment estimators; excess kurtosis is zero for the normal reference |
| `max_drawdown` | Signed minimum wealth/previous peak minus one, including initial unit wealth |
| `VaR95_daily`, `ES95_daily` | Signed 5th-percentile daily return and mean of returns at/below that threshold |
| `JB_pvalue`, `AC1`, `LB10_pvalue`, `LB10_sq_pval` | Existing normality and dependence diagnostics; deeper interpretation remains Step 2.6 |

All returns must be finite, strictly above -100%, aligned with the risk-free
series and sorted without duplicate dates. Constant series have undefined
Sharpe/moment diagnostics, represented by NaN rather than infinity. CAGR uses
the 252-session convention; calendar-year CAGR may differ. VaR and ES are
negative-tail **returns**, not positive-loss labels.

## Correction and comparison scope

The original drawdown function started its running maximum at the first
post-return wealth. A first-day loss was therefore omitted if it remained the
largest drawdown. The shared function includes wealth 1 before the first
return; `[-20%, +10%]` correctly produces a maximum drawdown of -20%.

The numerical formulas are tested against independently written product,
sample-standard-deviation, moment and excess-return calculations. The local
tables use the prepared **main and extended common samples**, not the old
2006-to-latest notebook outputs. Their values should not be expected to match
those old outputs after changing both the dates and drawdown initialization.

The 60/40 row is `0.6*SPY + 0.4*IEF` each day, a **daily-rebalanced gross
reference**. It is not the production monthly-rebalanced baseline from 2.5,
and excludes trading/financing costs. These are asset/reference diagnostics,
not evidence that a portfolio strategy is superior or a forecast of returns.
The [DTB3 proxy limits](08_DATA_CONVENTIONS.md#risk-free-proxy-explicit-approximation)
also apply to excess returns and Sharpe.

## Reproduce

1. Generate the common samples: `python -m src.build_common_sample`.
2. Run `python -m src.build_descriptive`.
3. Run `python -m pytest -q`.

The builder verifies input hashes and writes ignored local results:

- `results/2_1_main_descriptive_stats.csv`;
- `results/2_1_extended_descriptive_stats.csv`;
- `results/2_1_manifest.json`, identifying periods, input manifest and output
  hashes, the daily-reference convention and the correction to Raf's version.

The notebook Step 2.1 source uses the same function and main sample. Its saved
historical outputs are retained and explicitly labelled stale until the cell
is rerun. Later notebook cells were not re-executed or certified by this task.
