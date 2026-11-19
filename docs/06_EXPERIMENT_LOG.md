# Experiment Log

This log helps prevent data snooping and retrospective decision-making. Add an entry **before** running an important variant, then record the result without removing unfavorable experiments.

| ID | Date | Owner | Hypothesis | Data/period | Parameters set before testing | Primary metric | Result | Decision |
|---|---|---|---|---|---|---|---|---|
| E001 |  |  | LW covariance is more stable than sample covariance | Validation | 3-year window | Turnover and volatility error |  |  |
| E002 |  |  | ERC reduces risk concentration | Validation | Long-only | RC Herfindahl index and stability |  |  |
| E003 |  |  | StockTwits provides a useful sector view | Train/validation | Aggregation defined before testing | Net OOS performance / IC |  |  |
| E004 | 2026-11-18 | Codex | Reproduce Raf's regularized Bayes–Stein mean rule; verify mathematical shrinkage, not predictive superiority | Main/extended common calendars; historical diagnostics only | 756 trailing sessions; month-end close; LW constant-correlation asset covariance; GMV-mean target; intensity (p+2)/(p+2+T*d'Σ⁻¹d) | Formula identities, smaller cross-sectional dispersion, future-perturbation invariance | 96 tests pass (11 new); 337 windows independently checked; dispersion reduced at every date; mean intensity 62.56% main / 63.80% extended; no predictive scores computed | Implementation default; no future-return ranking; holdout still open |
| E005 | 2026-11-18 | Codex | Measure sensitivity of the Tobin profile calibration | Step 2.1 common-sample diagnostics | Existing 0.35 baseline, notebook grid, illustrative 8% capacity | Volatility and category before and after the cap | 40 scenarios; at risk aversion 4, raising Sharpe from 0.35 to 0.40 takes uncapped volatility from 8.75% to 10%; both capped at 8% | Retain 0.35 for profiling |
| E006 | 2026-11-18 | Codex | Reproduce the LN7 SPY reference | 4–8 January 2010 | Recalculate close-to-close and compare at six decimals | Matches to the lab | 5/5 | Course reference verified; event reproduction pending |
| E007 | 2026-11-18 | Codex | Resolve historical identifiers for LN7 companies | 13 symbols from 2010 to March 2020 | Match dated CRSP and CCM identifiers before GICS | Matched company-days | 37,955/42,154; historical GICS absent | Company-derived aggregation pending |
| E008 | 2026-11-18 | Codex | Direct ETF polarity improves on training-mean forecast | 2010–2015 train; 2016–2017 validation | Pooled monthly tags, following-month spread over SPY, frozen Huber fit, Mann–Whitney with Holm adjustment | Validation MAE; adjusted rank p-values | Lower MAE on 4/9 ETFs; 0/8 adjusted rank comparisons below 5% | Exploratory evidence; zero approved views |
| E009 | 2026-11-18 | Codex | Offline FOMC baseline improves on the majority classifier | Annotated train 1996–2019 and test 2020–2022; 86 historical statements | TF–IDF/logistic; exclude exact train/test repeats | Accuracy and macro-F1 | 62.8% vs 55.0% majority accuracy; 0.507 macro-F1; 1,603 statement sentences scored | Descriptive baseline; official model pending |
| E010 | 2026-11-18 | Codex | Verify view construction, calibration and uncertainty | Synthetic cases | Relative P; chronological Q against zero; Ω from validation MSE and prior floor | Alignment, stability and sensitivity | Stable Q 3.36% in one fixture; in another, view weight falls from 28.2% to 9.0% | Implementation checks; zero real views |
| E011 | 2026-11-18 | Codex | Select HMM state count with BIC | Latest-vintage, 2005–2015 and endpoint sensitivity through 2014 | Standardize training; diagonal Gaussian HMMs; 3/4 states, 12 starts each | Lowest BIC | 4 states in both windows; 1,243.94 vs 1,357.70 in main train | Provisional structure |
| E012 | 2026-11-19 | Codex | Produce expanding, forward-filtered regime estimates | Exploratory months 2016–2017 | Six starts per fit, match state IDs to first fit | Chronology and dominant state counts | Probabilities unchanged by future perturbation in tests; one state led all 24 months | Historical vintages needed before backtesting |
| E013 | 2026-11-19 | Codex | Assign economic descriptions to the fitted states | Reference fit 2005–2015 | Inspect fitted means, dominance counts and self-transitions | Profile contrast and persistence | Four profiles documented; low-inflation state effectively absorbing in reference fit | Exploratory labels; static/GMM comparison pending |
| E014 | 2026-11-19 | Codex | Company-derived raw polarity forecasts a positive following-month sector spread | Pending dated GICS and fixed chronological split | Use [Signal protocol v1](24_SIGNAL_PROTOCOL.md#next-stocktwits-comparison), with a zero-spread comparator | Mean realized high-minus-low spread in later validation | Pending | Preregistered; no view unless validated |
| E015 | 2026-11-19 | Codex | Direct ETF tags produce a positive high-minus-low spread | 2010–2015 train; 2016–2017 reused exploratory validation | Nine configured sector ETFs. Select unique extremes of pooled monthly polarity before seeing returns. Hold from the next month's first NYSE close to its last. Zero-spread comparator. | Mean realized high-minus-low spread in validation | +0.623% train (65/71 priceable); −0.879% validation (24/24 priceable, 10 positive) | Direction reversed; keep direct-ETF views disabled |
| E016 | 2026-11-19 | Codex | Transition dynamics improve next-month macro density relative to a static mixture | Initial train 2005–2015; reused exploratory 2016–2017 | Expanding windows; identical train-only scalers; four diagonal states/components and six starts; HMM forward probabilities | Mean predictive log-score difference; months won | HMM wins 21/24 months, +0.686 nats/month on average; +1.025 in 2016 and +0.347 in 2017 | Retain as an exploratory macro benchmark comparison; no allocation results |
| E017 | 2026-11-19 | Codex | Cross-check the rolling market model against displayed AAPL residuals | Yahoo Finance AAPL/SPY closes; Lab LN7 rows for 3–7 January 2011 | Standard lab regression with intercept and SPY beta, 365 calendar days including date of residual | Matches at six decimals and maximum absolute difference | 0/5 exact; maximum difference 1.105 bp | Public-input comparison recorded; Moodle price reproduction remains open |
| E018 | 2026-11-19 | Codex | Verify the historical StockTwits cutoff | Extended market calendar through 18 November 2026 | 31 March 2020 inclusive for message arrival and view eligibility; preserve market calendar | Later sessions and labelled StockTwits arrivals | 1,668 later market sessions retained; 0 with labelled sentiment | Historical-only StockTwits; no later views |

E006–E013 were backfilled from existing notebook runs and merge history.
They record exploratory evidence and implementation checks.

## Rules

- A hypothesis must identify the baseline it seeks to outperform.
- The primary metric is selected before the result is reviewed.
- The final test must not be used to select hyperparameters.
- A change inspired by the final test is marked as exploratory and does not replace the primary result.
- Abandoned variants remain documented along with the reason they were dropped.

