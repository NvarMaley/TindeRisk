# Historical returns and risk · section 4.1

## Measurement protocol

Use the registered January 2020–October 2026 retrospective comparison, starting at the 31 December 2019 close and ending at the 30 October 2026 close. Retain all 13 funds in the return summary. The detailed portfolio has one third each in SPY, IEF and GLD, reset daily as in the fixed-weight risk target. All three are denominated in USD. Wealth is a gross, hypothetical index with an initial value of 100, no deposits, and no transaction or FX charges. Fund expenses are already reflected in adjusted returns. The prepared v1 snapshots and the original period had already been inspected. These are retrospective descriptions.

At each venue close, translate accumulated USD wealth using that day's CHF per USD. A missing fixing leaves that CHF mark unknown. Subsequent observed marks recover the intervening USD performance and currency movement. Daily CHF returns require quotes on **both adjacent sessions**. Compounding observed daily returns across a gap would describe a different investment. Report daily arithmetic means, log returns, one-session USD excess over the prepared bill proxy, actual-calendar CAGR and coverage independently. CHF excess is unavailable because the 3.1 catalogue contains no CHF cash history.

Use daily positive loss (minus simple return), historical VaR at 95% and 99% via the inverse empirical distribution, and mean loss in the worst 5% or 1% with fractional boundary mass. Record strict exceedances, threshold ties, tail observations and runs of adjacent breaches; independence of episodes is unknown. Percentile intervals resample joint blocks of five venue sessions, retaining gaps and asset dependence, with 2,000 draws and fixed seed 4102. Show sensitivity to 20-session blocks for the portfolio. The intervals describe estimation uncertainty under this resampling rule. A tail mass below 20 observations is flagged as sparse.

For a chronological diagnostic, freeze a 252-session trailing historical forecast with at least 240 valid returns, calculated only through the previous venue close. Keep unavailable forecasts and missing outcomes in the ledger. Count a breach only when loss exceeds VaR. Report exact two-sided binomial coverage under independent trials, block uncertainty, Kupiec coverage and Christoffersen transition/conditional coverage where expected cell counts are at least five and estimation is interior. Gaps interrupt transitions. For any subsequent paired VaR/ES model comparison use the lower-is-better FZ0 score on positive-loss units with positive ES: log(ES) − 1 + VaR/ES + max(loss − VaR, 0)/(tail probability × ES). Use the same verified origins and the same units. This section scores one baseline. [Patton, Ziegel and Chen, equation 6](https://public.econ.duke.edu/~ap172/Patton_Ziegel_Chen_JoE_2019.pdf)

Report 252-session IID-scaled volatility and compare 21-session additive log-return variance under the IID rule with all 20 sample autocovariances, using actual lagged pairs on the venue grid. Also measure complete compounded 21-session simple returns. Drawdown and recovery durations use observed wealth and calendar days; missing marks may conceal a deeper trough or an earlier recovery. Count an ongoing episode through the final observed mark. Rolling correlations use 63 venue sessions and at least 60 jointly observed returns. Decompose volatility and variance using common CHF observations over the full comparison and the final 63, 252 and 756 sessions. Record window coverage, eigenvalues, condition number, marginal and weighted contributions, risk shares, diversification ratio and effective holdings. Bootstrap whole joint return vectors, using the same draws for all three assets. The same procedures apply if a holding contributes negatively to portfolio risk.

## Results in Swiss francs

| Portfolio measure | Historical estimate |
|---|---:|
| Initial and final value, per CHF 100 invested | 100.00 → 166.19 |
| Annual compound growth | 7.72% |
| Mean one-session return | 0.0315% |
| Annualized daily volatility, IID convention | 10.66% |
| Largest observed decline from a peak | 13.83% |
| Daily loss threshold, 95% / 99% (VaR) | 1.01% / 1.91% |
| Average loss in the worst 5% / 1% (ES) | 1.61% / 2.71% |

From the 31 December 2019 base to 30 October 2026, the USD portfolio grew by 95.41% and the same investment measured in CHF grew by 66.19%. On the CHF series 17 missing FX marks interrupted 34 one-session returns. The 1,683 observed daily returns contain zero total losses. USD excess averaged 0.0295% per session over the USD cash proxy. [All fund and portfolio returns](results/returns.csv)

The deepest decline lasted from the 20 February 2020 peak to the 16 March trough, with recovery on 29 April (69 calendar days from peak). The longest time below a peak was 673 days, from 4 May 2022 to 7 March 2024, with an 11.87% loss at the trough. The final observation was 4.20% below the 25 August 2026 peak after 66 days. At 21 sessions the IID estimate of log-return volatility is 3.08%, compared with 2.54% after accounting for measured serial dependence and 2.67% for the observed compounded simple returns on 1,353 complete paths. [Drawdowns](results/drawdown_episodes.csv) · [Horizon estimates](results/horizon_risk.csv) · [Wealth and coverage figure](results/wealth_drawdown.png)

At 95%, five-session block intervals place daily VaR between 0.90% and 1.12%, and ES between 1.39% and 1.84%. The 99% ES uses only 16.83 observations of tail mass. When each threshold is recalculated using only earlier dates, losses breached the 95% threshold 92 times against 84.15 expected, and the 99% threshold 26 times against 16.83 expected. The exact binomial p-values assuming independent observations are 0.371 and 0.036. For the 99% threshold the five-session block interval for the breach rate is 0.94%–2.15%, which includes 1%. Sparse transition counts limit inference about clustering. [Historical losses and intervals](results/historical_tails.csv) · [Rolling threshold diagnostics](results/var_backtest.csv)

SPY, IEF and GLD contributed 50.67%, 11.95% and 37.38% of portfolio variance, respectively. Those shares sum to 100% and correspond to 5.40, 1.27 and 3.98 percentage points of annualized portfolio volatility before rounding. The 63-session shares were 28.10%, 5.75% and 66.15%. Gold's share increased over this shorter window despite its unchanged one-third capital weight. The full-sample annual covariance matrix is positive definite with condition number 6.45. [Attribution and bootstrap intervals](results/risk_contributions.csv) · [Correlation figure](results/correlations.png)

## Reproduce

From the repository root, with the committed prepared v1 files and Python 3.12, run:

```sh
python -m pip install -r requirements-descriptive.txt
python tests/test_descriptive.py
python research/descriptive/build.py
```

The builder checks the input hashes, rebuilds in a temporary directory and verifies the existing release byte for byte. Use `--output /path/to/new-directory` for a separate build, for example when using a different font or graphics stack. CSV and Parquet ratios are decimal fractions. Read the per-session observations, rolling estimates and file digests in the [results directory](results/).
