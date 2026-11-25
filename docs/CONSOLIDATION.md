# RiskMatch V3 consolidation — 2026-11-25

The checklist's 1,230 identified tickets distinguish mathematical specifications, code, data availability, implementation tests and independent acceptance. The 27-chapter prototype exists but this does not imply all catalog methods are certified.

## Evidence resolved

- The [method contracts](METHOD_SPECIFICATIONS.md) specify all 22 optimizers, 19 strategies, 13 factors, 10 dynamic policies and 23 metrics, including units and eligibility assumptions. The 11 objective specifications are in [FINANCIAL_OBJECTIVES.md](FINANCIAL_OBJECTIVES.md), implemented in typed goal objects and tested against cash-flow fixtures. G01 is closed for structural specification, not empirical psychometric validation.
- Chapter 8 now has a monthly USD RF comparator separate from the frozen model archive. The core research matrix contains 223 continuous months, of which 41 are test observations for the cash comparator. Historical release times are still unverified.
- Chapter 11 loss units, confidence validation, fractional ES, configurable downside threshold and historical loss-budget comparison are documented and tested. Threshold comparison remains an illustrative observed-period measure.
- Chapter 14 mathematical programs, numerical feasibility, explicit input constraints, diagnostic exports and analytical tests are reviewed. Actual issuer/sector look-through, liquidity, historical eligibility and permitted short financing remain limitations. Chapter 14.09 remains open pending G04.
- Chapter 25 monthly net sleeve allocation now charges 10 bp on executed additional inter-sleeve transfers with self-financing reconciliation. On the 45-month 60/40 test, annualized volatility reconciled to 4.727%, aggregate monthly-NAV-relative additional transfer fee fractions total approximately 0.0442%, and net CAGR was 3.984%. The optimizer target is still trained on gross covariance; net results are evaluated separately.
- The 11-goal evaluator is connected to a confirmed Match through common 1,000-path block bootstrap comparisons. This is a conditional USD research projection and cannot certify actual distribution income, liability DV01 or hedging.
- The [API route contract](API_ROUTES.md) defines local routes and the future resource API. Multi-user authorization remains undeployed.

## Remaining immediate formal blockers

| Ticket | Required evidence |
|---|---|
| CH04.03 | Product-specific data-use rights, institutional entitlement, permitted derived results and redistribution. |
| UNIV.01 | Dated complete and independently verified Treasury ETF holdings, and genuine classification of underlying exposure. Existing synthetic eligibility tests fail closed; current historical holdings cannot be assumed complete. |
| CH02.16 | Preregistered behavioral protocol and 30–50 consenting volunteers under reviewed research procedures. The synthetic protocol and local consent remain available. |
| CH27.08 | Future multi-user resource authorization and persistence; local fictional browser saves do not establish account-level server authorization. |

The remainder depends on these tickets or later validation gates. Technical research can continue on the existing data with explicit limitations. Do not mark a research result as approved merely because it is numerically computed.
