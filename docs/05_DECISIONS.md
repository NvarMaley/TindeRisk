# Decision Register

Every important decision must have a date, an owner, and a rationale. When a decision is changed, its previous value must remain in the pull request history.

## Proposed Decisions

| ID | Topic | Proposed default | Status | To be confirmed by |
|---|---|---|---|---|
| D01 | MVP scope | Classic + ERC + BL + 60/40 | Proposed | Team/professor |
| D02 | Questionnaire | Fixed and transparent in the MVP; adaptive as an extension | Proposed | Team |
| D03 | Universe | 9 sectors + IEF + TLT + GLD; SPY as benchmark | Proposed | Data owner |
| D04 | Currency | USD, with currency risk disclosed | Proposed | Team |
| D05 | BL `x0` | Neutral strategic portfolio; sensitivity to 60/40/market weights | Open | Professor |
| D06 | Covariance | Ledoit-Wolf, 3-year window; sample covariance as baseline | Proposed | Optimization owner |
| D07 | Classic `mu` | Shrunk rolling mean or implied prior, with the choice frozen after validation | Open | Optimization owner |
| D08 | Leverage | No leverage by default; disclose when the target is unattainable | Proposed | Professor/team |
| D09 | Frequency | Monthly rebalancing; quarterly in robustness tests | Proposed | Backtest owner |
| D10 | Costs | 10 bps as the main assumption; 0 and 25 bps for sensitivity analysis | Proposed | Backtest owner |
| D11 | Sentiment | Only StockTwits LN7 in the core | Proposed | Signals owner |
| D12 | FOMC | Extension after core validation | Proposed | Team |
| D13 | Regimes | Extension; filtered probabilities only | Proposed | Team |
| D14 | ESG | Exclusions as constraints, not as alpha | Proposed | Team |
| D15 | Primary metric | Realized vs target volatility + net Sharpe + maximum drawdown | Open | Team |
| D16 | Test period | Frozen before the final comparison | Open | Backtest owner |

## New Decision Template

```text
ID:
Date:
Owner:
Context:
Options considered:
Decision:
Rationale:
Impact on data/code/tests/application:
Reconsideration condition:
```

## Assumptions to Display in the Application

- past performance is not guaranteed;
- covariance and return estimates are uncertain;
- target volatility is not a guaranteed maximum loss;
- liquidity and costs are simplified;
- a Swiss user is exposed to USD currency risk;
- the academic questionnaire has not been psychometrically validated;
- this is an educational tool, not financial advice.

