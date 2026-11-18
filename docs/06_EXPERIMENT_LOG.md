# Experiment Log

This log helps prevent data snooping and retrospective decision-making. Add an entry **before** running an important variant, then record the result without removing unfavorable experiments.

| ID | Date | Owner | Hypothesis | Data/period | Parameters set before testing | Primary metric | Result | Decision |
|---|---|---|---|---|---|---|---|---|
| E001 |  |  | LW covariance is more stable than sample covariance | Validation | 3-year window | Turnover and volatility error |  |  |
| E002 |  |  | ERC reduces risk concentration | Validation | Long-only | RC Herfindahl index and stability |  |  |
| E003 |  |  | StockTwits provides a useful sector view | Train/validation | Aggregation defined before testing | Net OOS performance / IC |  |  |
| E004 | 2026-11-18 | Codex | Reproduce Raf's regularized Bayes–Stein mean rule; verify mathematical shrinkage, not predictive superiority | Main/extended common calendars; historical diagnostics only | 756 trailing sessions; month-end close; LW constant-correlation asset covariance; GMV-mean target; intensity (p+2)/(p+2+T*d'Σ⁻¹d) | Formula identities, smaller cross-sectional dispersion, future-perturbation invariance | 96 tests pass (11 new); 337 windows independently checked; dispersion reduced at every date; mean intensity 62.56% main / 63.80% extended; no predictive scores computed | Implementation default; no future-return ranking; holdout still open |

| E005 | 2026-11-18 | Codex | Measure sensitivity of the Tobin profile calibration | Step 2.1 common-sample diagnostics | Existing 0.35 baseline, notebook grid, illustrative 8% capacity | Volatility and category before and after the cap | 40 scenarios; at risk aversion 4, raising Sharpe from 0.35 to 0.40 takes uncapped volatility from 8.75% to 10%; both capped at 8% | Retain 0.35 for profiling |

## Rules

- A hypothesis must identify the baseline it seeks to outperform.
- The primary metric is selected before the result is reviewed.
- The final test must not be used to select hyperparameters.
- A change inspired by the final test is marked as exploratory and does not replace the primary result.
- Abandoned variants remain documented along with the reason they were dropped.

