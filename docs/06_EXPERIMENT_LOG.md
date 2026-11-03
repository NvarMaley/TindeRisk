# Experiment Log

This log helps prevent data snooping and retrospective decision-making. Add an entry **before** running an important variant, then record the result without removing unfavorable experiments.

| ID | Date | Owner | Hypothesis | Data/period | Parameters set before testing | Primary metric | Result | Decision |
|---|---|---|---|---|---|---|---|---|
| E001 |  |  | LW covariance is more stable than sample covariance | Validation | 3-year window | Turnover and volatility error |  |  |
| E002 |  |  | ERC reduces risk concentration | Validation | Long-only | RC Herfindahl index and stability |  |  |
| E003 |  |  | StockTwits provides a useful sector view | Train/validation | Aggregation defined before testing | Net OOS performance / IC |  |  |

## Rules

- A hypothesis must identify the baseline it seeks to outperform.
- The primary metric is selected before the result is reviewed.
- The final test must not be used to select hyperparameters.
- A change inspired by the final test is marked as exploratory and does not replace the primary result.
- Abandoned variants remain documented along with the reason they were dropped.

