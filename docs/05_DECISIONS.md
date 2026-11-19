# Decision Register

Every important decision must have a date, an owner, and a rationale. When a decision is changed, its previous value must remain in the pull request history.

## Decision Summary

| ID | Topic | Proposed default | Status | To be confirmed by |
|---|---|---|---|---|
| D01 | MVP scope | Classic + ERC + BL + 60/40 | **Approved** (professor, 2026-11-17) | — |
| D02 | Questionnaire | Fixed and transparent in the MVP; adaptive as an extension | Proposed | Team |
| D03 | Universe | 9 sectors + IEF + TLT + GLD; SPY as benchmark | Proposed | Data owner |
| D04 | Currency | USD, with currency risk disclosed | Proposed | Team |
| D05 | BL `x0` | ERC portfolio as anchor, with an explicit optimality justification (see DR-02); 60/40 anchor as sensitivity only | **Approved** (professor, 2026-11-17) | — |
| D06 | Covariance | Ledoit-Wolf, 3-year window; sample covariance as baseline | Proposed | Optimization owner |
| D07 | Classic `mu` | Regularized Bayes–Stein-style rolling excess mean toward GMV mean (DR-05); implied ERC prior reserved for later sensitivity | Implementation default (2026-11-18); final OOS validation remains open | Optimization owner |
| D08 | Leverage | Allowed up to 1.5x, borrowing cost = DTB3 + 100 bps (see DR-03) | **Approved** (professor, 2026-11-17) | — |
| D09 | Frequency | Monthly rebalancing; quarterly in robustness tests | Proposed | Backtest owner |
| D10 | Costs | 10 bps as the main assumption; 0 and 25 bps for sensitivity analysis | Proposed | Backtest owner |
| D11 | Sentiment | Core: LN7 Moodle dataset (19 tickers). Upgrade: raw StockTwits dataset (≈90M messages) once the LN7 pipeline works (see DR-01) | **Approved** (professor, 2026-11-17) | Signals owner |
| D12 | FOMC | Extension after core validation | Proposed | Team |
| D13 | Regimes | Extension (HMM on FRED macro); filtered probabilities only; never part of the core | **Approved** (professor, 2026-11-17) | Team |
| D14 | ESG | Exclusions as constraints, not as alpha | Proposed | Team |
| D15 | Scientific primary metrics | Realized vs risk-band reference volatility + net Sharpe + maximum drawdown | Proposed | Team |
| D16 | Test period | Main backtest Jan 2010 – Mar 2020 (all strategies incl. BL); extended 2009 – latest without sentiment views; frozen before the final comparison (see DR-04) | **Approved** (professor, 2026-11-17); exact dates to freeze | Backtest owner |
| D17 | Risk categories | Conservative 4%–6% (5% ref.); Balanced 6%–9% (8%); Growth 9%–12% (10%); Aggressive 12%–15% (14%) | Proposed | Team/professor |
| D18 | Client card metrics | Historical net annualized return, realized volatility, net Sharpe, maximum drawdown, annualized cost | Proposed | Team |
| D19 | Comparison rule | Same risk-band reference, common period, net of costs first; never rank on return alone | Proposed | Team |
| D20 | Live follow-up | Daily latest-price monitoring after selection; no brokerage or tick-level claim | Proposed | Team |

## Professor Feedback — 2026-11-17

Summary of the professor's answers to the team's scoping email:

1. **Topic:** approved; the 2024 guidelines remain valid.
2. **StockTwits data:** two datasets are available.
   - *Moodle dataset* (used in Lab 7): aggregated daily sentiment per ticker, 19 tickers filtered for high message volume, 2010 – March 2020.
   - *Raw dataset*: ≈90 million messages, 2010–2020, many more tickers, exact text, user label (bullish / bearish / neutral), user metadata (number of messages, followers, etc.). Obtained by bringing a USB key to the professor.
   - The team may publish anything on GitHub.
3. **Leverage:** allowed.
4. **BL anchor:** a neutral strategic portfolio is accepted, provided the report mentions and briefly justifies that the anchor portfolio is optimal.
5. **Backtest:** no specific requirement on period or validation depth; free choice.
6. **HMM regimes:** welcome as an extension, provided they are not the core of the project.

## Decision Records

### DR-01 — Sentiment data

```text
ID: DR-01 (updates D11)
Date: 2026-11-17
Owner: Signals owner (workstream 3)
Context: Two StockTwits datasets are available (Moodle aggregated, 19 tickers; raw, ≈90M messages).
Options considered: (a) Moodle only; (b) raw only; (c) Moodle first, raw as upgrade.
Decision: (c). Build and validate the full pipeline on the Moodle dataset (reproduces Lab 7). Request the raw dataset now (USB key), process it only once the LN7 pipeline works.
Rationale: Moodle data keeps the core aligned with the course and unblocks BL quickly; raw data raises data complexity (sector coverage, user-credibility weighting) without putting the core at risk.
Impact on data/code/tests/application:
  - Check which GICS sectors the 19 Moodle tickers cover; BL views are formed only on covered sectors (P need not span the universe).
  - Raw data processed out-of-core (DuckDB/Polars, Parquet), reduced to sector × day counts; raw messages never committed.
  - Derived sector-level sentiment series may be published on GitHub (professor's approval).
Reconsideration condition: raw-data processing threatens the core schedule -> stay on Moodle data.
```

### DR-02 — Black-Litterman anchor portfolio

```text
ID: DR-02 (updates D05)
Date: 2026-11-17
Owner: Signals owner (workstream 3), reviewed by optimization owner
Context: No reliable multi-asset market capitalizations; the professor accepts a neutral anchor if its optimality is justified.
Options considered: ERC; 60/40; equal weight.
Decision: ERC portfolio (estimated with the same rolling Ledoit-Wolf covariance) as anchor x0.
Rationale:
  - ERC is the maximum-Sharpe portfolio when all assets have the same Sharpe ratio and correlations are constant (Maillard, Roncalli & Teiletche, 2010): it is the optimal portfolio of an investor with no differential views.
  - Reverse optimization pi = delta * Sigma * x0 makes x0 optimal by construction under the implied returns; BL departs from ERC only to the extent justified by the sentiment views.
  - 60/40 has no comparable optimality argument; it remains the benchmark, not the anchor.
Impact on data/code/tests/application:
  - Test: with no views, BL weights = ERC weights (identity test).
  - One slide / one report paragraph presents the optimality argument.
  - 60/40 anchor reported as a sensitivity analysis.
Reconsideration condition: none expected.
```

### DR-03 — Leverage

```text
ID: DR-03 (updates D08)
Date: 2026-11-17
Owner: Optimization owner (workstream 2)
Context: Leverage is allowed by the professor; dynamic profiles may require a target volatility above that of the unlevered portfolios.
Options considered: no leverage; cap 1.5x; cap 2x.
Decision: Gross exposure capped at 1.5x; borrowed amount charged DTB3 + 100 bps per year.
Rationale: 1.5x reaches the highest risk categories while remaining realistic for a private investor; a borrowing cost prevents artificially favourable results for levered profiles.
Impact on data/code/tests/application:
  - config.yaml: portfolio.leverage_limit = 1.5, portfolio.borrowing_spread_bps = 100.
  - Test: exposure never exceeds 1.5x; financing cost deducted from net returns.
  - Application: display leverage used and its cost; warn if the target volatility remains unattainable at 1.5x.
Reconsideration condition: results driven mainly by leverage -> report unlevered variant alongside.
```

### DR-04 — Backtest period

```text
ID: DR-04 (updates D16)
Date: 2026-11-17
Owner: Backtest owner (workstream 1)
Context: Free choice of period (professor); sentiment data stop in March 2020; GLD starts in Nov. 2004; 3-year estimation window.
Options considered: (a) 2010-2020 only; (b) 2009-latest only; (c) both.
Decision: (c).
  - Main backtest: Jan 2010 - Mar 2020, all strategies including BL with sentiment views.
  - Extended backtest: Jan 2009 - latest available date; BL reverts to its ERC anchor when no views exist (after Mar 2020), clearly disclosed.
Rationale: The main period matches sentiment coverage and ends with the COVID crash, a natural stress test; the extended period checks robustness of the non-sentiment strategies.
Impact on data/code/tests/application: config.yaml backtest section; application shows which period is displayed.
Reconsideration condition: exact dates frozen before the final comparison, never after observing results.
```
### DR-05 — Classic expected-return implementation default

```text
ID: DR-05 (updates D07)
Date: 2026-11-18
Owner: Codex implementation; optimization owner for final validation
Context: Step 2.3 in Raf's notebook implements raw, Bayes–Stein-style and implied-ERC estimates. No final holdout is frozen; notebook future-return comparisons are exploratory.
Options considered: shrunk rolling historical excess mean; implied ERC prior.
Decision: Implement the regularized Bayes–Stein-style GMV-mean shrinkage rule as the Classic default. Use 756 daily observations at completed month-end closes; daily LW constant-correlation asset covariance; annualize only the final daily excess-mean estimate. Exact formula and boundaries: docs/13_EXPECTED_RETURNS.md.
Rationale: Reduces cross-sectional mean dispersion by construction, reuses Raf's rule and validated covariance, introduces no return-based hyperparameter search, and keeps Classic structurally distinct from no-view BL. Does not require implementing ERC prematurely.
Impact: config.expected_returns declares the method, target, units and provisional validation status. src/build_expected_returns.py exports two-period estimates and diagnostics. Raw means are controls only. The unconstrained GMV mean is a mathematical target, not an approved investable allocation or the BL anchor.
Limits: Regularized variant, not exact Jorion finite-sample optimality; shrinking differences need not lower every return, overall return level or portfolio risk. DTB3 timing/accrual and final holdout remain open. No predictive superiority claimed.
Reconsideration: Freeze the evaluation protocol before comparing predictive or portfolio performance. An implied ERC alternative may be tested after ERC is independently validated; changes require a logged rationale, not a search on the final test.
```

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
- leverage (up to 1.5x) amplifies losses and bears a financing cost;
- sentiment views are available only until March 2020;
- a Swiss user is exposed to USD currency risk;
- the academic questionnaire has not been psychometrically validated;
- this is an educational tool, not financial advice.

### DR-06 — StockTwits coverage

Decision on 2026-11-19 for Step 4.9. Use StockTwits as a historical
demonstration through 31 March 2020. In the available source, the final
message date is 23 March 2020 and the last availability session is
24 March 2020. The rest of March remains sparse. Keep every later market
session in the extended calendar and leave StockTwits inputs missing.
Black–Litterman uses the no-view ERC specification over these sessions.
Step 5.3 verified the portfolio fallback on 214 month-end decisions.

The common sample enforces both the message and availability cutoff. A
validated view must also expire by that cutoff, including a monthly
snapshot that would first become available in April. Expanding coverage
requires a separate validated source with documented historical availability.
