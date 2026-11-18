# Step 2.6 · Distribution and subperiod diagnostics

The diagnostics cover the 12 investable ETFs, SPY and the three monthly
baselines from Step 2.5. Run the standalone 2.6 notebook cell, or run
`python -m src.build_baselines` followed by `python -m src.build_diagnostics`.
The builder checks the input hashes and exact alignment of daily sessions.
The complete output is `results/2_6_diagnostics.csv`, with a hash manifest.

Each series is evaluated on its full common sample and on three fixed,
nonoverlapping calendar blocks within that sample. Missing calendar blocks
are omitted and every row records the actual start, end and session count.

| Calendar block | Main sample | Extended sample |
| --- | ---: | ---: |
| Through 2019 | 2,516 | 2,768 |
| 2020–2021 | 62, through 31 March 2020 | 505 |
| 2022 onward | — | 1,224 |

The tests use daily simple returns. Jarque–Bera tests normality via skewness
and kurtosis. AC(1) is the first-lag correlation. Ljung–Box checks lags 1–10
jointly, on returns and on squared returns. Dependence in squared returns
is consistent with changes in volatility. The 5% threshold is applied to raw
p-values for descriptive counts. Dependence and overlapping samples limit
formal inference from these counts.

Historical ES uses the Step 2.1 signed-return convention. Take the empirical
5th percentile and average daily returns at or below it, including ties.
The output records the observations in that tail. More negative values
indicate larger historical losses. The 62-session main block in 2020 has only
four tail observations per series, so comparisons involving that block are
especially sensitive to individual days. Blocks shorter than 12 sessions
show coverage alone.

In each full sample, Jarque–Bera and Ljung–Box on squared returns give raw
p-values below 5% for all 16 series. Ljung–Box on returns gives p-values
below 5% for 15 of 16. Those observations describe these histories.

| Extended sample block | SPY daily ES | SPY annualized volatility | GMV daily ES | GMV annualized volatility |
| --- | ---: | ---: | ---: | ---: |
| Through 2019 | −2.52% | 16.15% | −0.81% | 5.64% |
| 2020–2021 | −4.04% | 25.33% | −1.28% | 8.26% |
| 2022 onward | −2.51% | 17.37% | −1.13% | 8.34% |

SPY's daily loss tail deepened in 2020–2021 before returning close to its
earlier level. GMV's volatility stayed above its pre-2020 level in both
later blocks. These gross historical diagnostics provide context for the
later robustness and net-of-cost work in Step 6.
