# Official Framework and Scope of RiskMatch

## 1. Verified Official Requirements

The QARM II project requires students to:

- design an investment strategy;
- build a portfolio management web application with Streamlit;
- use quantitative optimization and the tools covered in the course;
- make the code available on GitHub and provide the application link;
- present and sell the strategy in 15 minutes, in groups of five, to the professor acting as the client.

Assessment covers three areas: content, presentation, and application. Content is evaluated on the complexity of the client and the data, the extent to which the client's needs are addressed, and, above all, the grounding in topics covered in the course. The application is assessed on its design, interactivity, completeness, and absence of technical issues.

## 2. Proposed Solution

RiskMatch addresses the following question: **how can a client's needs, capacity, and constraints be translated into comparable, transparent, and risk-controlled portfolios?**

The target client is an informed individual investor who specifies:

- an investment horizon and liquidity needs;
- a maximum tolerable loss;
- a risk tolerance;
- investment constraints;
- optional ESG exclusions;
- a preference among several investment philosophies.

The core proposition is to assign the client to a transparent **risk category**, then compare several prepared portfolios at the category's **same reference volatility**, so that the decision concerns the allocation method rather than a different amount of risk. The continuous estimate remains an internal calibration and audit measure; the client sees a stable range and a plain-language category.

## 3. Mandatory Scope — Assessed Core

The core must be completed before any extension:

1. A simple and reliable client questionnaire covering capacity, tolerance, knowledge, and constraints.
2. A documented multi-asset universe comprising equity sectors, bonds, and gold, plus cash and a benchmark.
3. Simulated real-time historical estimation, with no future information.
4. Sample covariance and Ledoit-Wolf covariance, with a stability demonstration.
5. A constrained tangency portfolio or prudent Markowitz portfolio.
6. An ERC / risk-budgeting portfolio.
7. A Black-Litterman portfolio driven by a validated StockTwits signal.
8. A 60/40 benchmark and, time permitting, a non-equal risk budget.
9. Mapping the profile to a documented risk band, then scaling each strategy to that band's reference volatility, with an explicit leverage cap.
10. A walk-forward backtest including costs, turnover, Sharpe ratio, drawdown, tracking error, information ratio, Expected Shortfall, and concentration, used to create precomputed strategy summaries rather than return promises.
11. A robust Streamlit application covering category assignment, simplified strategy comparison, selection, technical analysis, and post-selection monitoring.
12. Unit tests, an end-to-end test, GitHub documentation, and a 15-minute pitch.

## 4. Conditional Extensions

The following elements are permitted only after the core has been validated:

- adaptive Bayesian question selection;
- macro regimes using Markov switching/HMM with filtered probabilities;
- regime-dependent risk budgets;
- a FOMC tone index;
- block Monte Carlo simulation;
- a downloadable client report;
- external persistence.

They must remain supplementary. They must not obscure the expected QARM tools or make the demonstration fragile.

## 5. Elements Excluded from the MVP

Deep networks, team-trained Transformers, reinforcement learning, PINNs, large-scale automated variable selection, technical timing, and the proliferation of signals are excluded. The available data and time do not allow them to be validated properly, and they would divert the project from the core course content.

## 6. Compliance Matrix

| Official expectation | RiskMatch response | Expected evidence |
|---|---|---|
| Investment strategy | Three QARM allocations + benchmark, prepared for the same four risk bands | Tested functions and versioned catalogue |
| Quantitative optimization | Constrained Markowitz, BL, ERC/RB, Tobin allocation | Notebook, equations, invariant tests |
| Client needs | Capacity, tolerance, horizon, liquidity, exclusions | JSON profile with category, range, capacity cap, and applied constraints |
| Relevant data | ETFs, FRED, and StockTwits data provided by the course | Data dictionary and availability dates |
| Web application | Multipage Streamlit application | Public deployment and tested user journey |
| GitHub | Reproducible code, with large data excluded | README, environment, CI/tests |
| 15-minute pitch | Problem, demo, method, validation, limitations | Timed script and contingency plan |

## 7. Non-Negotiable Success Criteria

- A clean installation can run the tests and the application.
- Every data item has a source, a date, and an availability rule.
- At every backtest date, only data available on that date are used.
- Each strategy is compared within the same risk category, at the same reference volatility and over the same historical period; realized risk is also displayed.
- Costs and turnover are deducted from performance.
- Client cards show historical net return, realized volatility, net Sharpe ratio, maximum drawdown, and cost, plus evidence-based advantages and limitations.
- Historical results are never described as forecasts or used to declare a universally best strategy.
- No result depends on a choice made after observing the test period.
- Limitations and assumptions are visible in the application.
- The project does not claim to provide financial advice or to be legally compliant with MiFID II/FinSA.

## 8. Points to Confirm with the Professor

1. Available StockTwits data, coverage, and publication rights.
2. Expected backtest depth and presentation period.
3. Acceptance of a BL portfolio anchored to a strategic portfolio rather than to actual multi-asset market capitalizations.
4. Desired importance of the adaptive questionnaire relative to optimization.
5. Whether leverage is permitted or the portfolio must be capped at 100% invested.
