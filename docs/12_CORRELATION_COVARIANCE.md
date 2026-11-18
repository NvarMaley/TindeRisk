# Steps 2.1b and 2.2 — Correlations and rolling covariance

Run `python -m src.build_dependence` after generating the common samples. The
builder verifies the return and warm-up file hashes against the common-sample
manifest. It exports separate main/extended outputs under ignored `results/`.
No downloading or application interaction is required.

## 2.1b: descriptive dependence

- Pearson correlation of daily simple returns, 12 ETFs plus SPY.
- Heatmap with a fixed [-1, 1] color scale for comparison across periods.
- Trailing 252-session SPY/IEF, SPY/TLT and SPY/GLD correlations. Gold is a
  diversifier, not a bond. Each period is computed separately: the initial
  251 rows are undefined and are retained in the CSV.
- Full-period correlations are retrospective diagnostics. They must not be
  substituted for rolling estimates when allocating a historical portfolio.
  Positive stock/bond correlation can reduce diversification; correlation
  alone does not measure portfolio risk or guarantee diversification benefits.

## 2.2: covariance estimation

The universe contains the 12 investable ETFs; SPY is excluded. At the close
of each **completed NYSE month**, the estimators use the final 756 daily
returns through that close. Estimates are usable only afterward. A partial
last month does not become a rebalancing date. Historical warm-up comes from
that period's separate common-sample warm-up file.

Three estimators are exported:

1. Unbiased sample covariance (`ddof=1`).
2. Ledoit–Wolf constant-correlation shrinkage, the LN3 target. Each asset
   retains its sample variance; off-diagonal correlations shrink toward their
   cross-sectional average.
3. Scikit-learn Ledoit–Wolf scaled-identity target as a distinct comparator.
   It must not be described as the constant-correlation estimator.

All outputs are annualized by 252. Shrinkage moments are estimated using the
population denominator n, then the resulting whole covariance is rescaled by
n/(n-1) for comparable `ddof=1` output. The constant-correlation implementation
corrects the previous mixing of centered fourth moments with an n-1 moment
denominator. When the sample already equals the target (including the
2-asset case), shrinkage returns that same covariance without division by zero.
Constant assets, invalid returns, duplicate labels and invalid dates are rejected.

The algorithm follows Ledoit & Wolf (2004), *Honey, I Shrunk the Sample
Covariance Matrix*, Appendix B, already referenced in LN3. A separately written
scalar-moment calculation checks the implementation on heterogeneous correlations,
with an interior shrinkage intensity. Other tests cover scaling, symmetry,
positive semidefiniteness, diagonal preservation and future-data perturbations.

Diagnostics include the exact estimation window, observation count, minimum
and maximum eigenvalues, spectral condition number and shrinkage intensity.
A lower condition number indicates easier numerical inversion; it does not
establish better out-of-sample portfolio performance.

## Outputs

For each of `main` and `extended`:

- `2_1b_<period>_correlation.csv` and `_heatmap.png`;
- `2_1b_<period>_rolling_correlation.csv` and `_rolling.png`;
- `2_2_<period>_covariances.parquet`: index `(date, estimator, asset)`, asset columns;
- `2_2_<period>_diagnostics.csv` and `_diagnostics.png`.

`2_1b_2_2_manifest.json` records input-manifest and configuration hashes, output
hashes, runtime versions, windows, periods, estimation dates and descriptive
summaries. Image metadata and the build timestamp need not be byte-identical
across builds; numerical outputs on identical inputs must agree.

The builder integration test checks generated hashes and verifies that a
partial final month is omitted. Correlation and covariance tests verify past
estimates are invariant to changes in future returns. Run `make check`.

## Boundaries

No production GMV portfolio, turnover, cost model or out-of-sample performance
claim is added here. Those belong to 2.5 and 2.8. Step 2.2b's instability exercise
is also separate. Existing notebook outputs use older inputs and remain legacy
explorations until rerun; the reproducible reference for these two steps is the
builder above, not the saved notebook tables. The notebook's later experimental
cells have not been executed or certified by this work.

## Verified local build — 2026-11-18

| Diagnostic | Main | Extended |
|---|---:|---:|
| Month-end estimation dates | 123 | 214 |
| Last estimation date | 2020-03-31 | 2026-10-30 |
| Mean pairwise sector correlation | 0.727 | 0.633 |
| Median sample condition number | 509.5 | 510.6 |
| Median constant-correlation LW condition number | 442.8 | 443.1 |
| Median identity LW condition number | 277.3 | 249.7 |

On these samples the shrinkage estimates are better conditioned by this
numerical diagnostic; this is not a selection based on strategy returns.
The SPY/IEF rolling correlation is negative on all defined main-period dates
and about 80% of defined extended-period dates, illustrating the importance
of period choice and the absence of a permanent negative-correlation guarantee.

All exported matrices were checked for symmetry and positive eigenvalues;
every sample estimate was separately compared with its exact trailing-window
covariance. Output hashes were verified. All six figures were visually inspected.
`make check` passes **85 tests**, including 11 added tests. Local incomplete
SciPy/scikit-learn/narwhals installations were repaired at their existing
versions, and Matplotlib was installed from the declared dependency range.
This is not a new clean-environment installation certification.

The two checklist rows remain unchecked pending peer review, as required by
`CONTRIBUTING.md`: “A task is complete only after another person has reviewed
the code, tests, documentation, and reproducible evidence.”
