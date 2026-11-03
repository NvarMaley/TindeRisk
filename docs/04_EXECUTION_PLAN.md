# Detailed Execution Plan

This document defines the order of work. The checklist tracks daily progress; here, each phase has an entry condition and a definition of done.

## Phase 0 — Scope and MVP Freeze

### 0.1 Review and Confirm

- Review the official framework and course alignment.
- Ask the professor the five questions.
- Set the presentation date and confirm team members and availability.

### 0.2 Decide

- Select the reference BL portfolio.
- Select the leverage rule.
- Select the primary strategy for the pitch.
- Classify each feature as core or extension.

### 0.3 Organize

- Assign an owner and reviewer to each workstream.
- Configure branches, pull requests, and the shared environment.
- Create the decision register and experiment log.

**Done when:** the professor has approved the topic, the MVP fits on one page, and every critical task has an owner.

## Phase 1 — Data Contract

### 1.1 Inventory

- List assets, benchmarks, FRED series, and StockTwits data.
- Define columns, frequency, units, currency, and dates.
- Define `observation_date` and `available_date`.

### 1.2 Reproducible Collection

- Write separate download functions.
- Save raw data without modification.
- Generate metadata and checksums where necessary.

### 1.3 Cleaning

- Adjusted prices, a common calendar, and quality checks.
- Simple, log, and excess returns.
- Lag macroeconomic series according to their publication dates.

### 1.4 Validation

- Coverage report.
- Schema and temporal leakage tests.
- Lightweight demonstration dataset.

**Done when:** someone outside the data workstream can rebuild `data/processed/` from the authorized sources.

## Phase 2 — Baselines and Diagnostics

### 2.1 Statistics

- Moments, drawdowns, ES, normality, and autocorrelations.
- Static and rolling correlations.

### 2.2 Reference Portfolios

- Equal-weighted.
- GMV.
- 60/40.

### 2.3 Estimated Risk

- Sample covariance.
- Ledoit-Wolf.
- Conditioning and stability comparison.

**Done when:** the baselines are tested and the main charts are reproducible.

## Phase 3 — MVP Client Profile

### 3.1 Specify

- Define dimensions, rules, and the JSON schema.
- Draft 10–15 neutral questions.
- Define capacity, tolerance, and constraints separately.

### 3.2 Implement

- Transparent scoring.
- Conversion into a volatility ceiling and target.
- Edge cases and user messages.

### 3.3 Validate

- Team review.
- Comprehension testing with 5–10 people.
- Simple test-retest assessment.

**Done when:** the same profile produces the same result, all rules can be explained, and the JSON schema is stable.

## Phase 4 — QARM Engine

### 4.1 Classic

- Conservative `mu`, LW covariance, and constraints.
- GMV as a control.
- Solver tests and sensitivity analysis.

### 4.2 ERC

- Contributions, Euler decomposition, log barrier, and rescaling.
- Analytical and numerical tests.

### 4.3 Black-Litterman

- Prior, reverse optimization, views, and confidence.
- No-view identities and sensitivity analysis.

### 4.4 Target Volatility

- Cash, leverage cap, and exclusions.
- Requested target volatility and achieved volatility.

**Done when:** each strategy satisfies its invariants and produces a reasonable result on a test date.

## Phase 5 — LN7 Sentiment

### 5.1 Reproduce the Lab

- Load StockTwits data.
- Calculate polarity and sector mapping.
- Reproduce a simple result from the course.

### 5.2 Validate the Signal

- Prespecified event study or regression.
- Mann-Whitney test or robust standard errors, depending on the test.
- Train/validation/test split.

### 5.3 Build the Views

- Dated `P`, `Q`, and `Omega`.
- Sign, magnitude, and confidence checks.

**Done when:** the team can explain why a view exists, its magnitude, and what happens if the signal does not work.

## Phase 6 — Walk-Forward Backtest

### 6.1 Engine

- Monthly rebalancing.
- Weight drift.
- Costs and cash.
- Detailed decision log.

### 6.2 Evaluation

- Gross/net, risk/return, downside, and benchmark metrics.
- Target versus realized volatility.
- Stability and turnover.

### 6.3 Robustness

- 2/3/5-year windows.
- Monthly/quarterly frequency.
- Costs of 0/10/25 bps.
- With/without shrinkage.
- Prespecified subperiods.

**Done when:** an anti-look-ahead test passes, all results can be regenerated, and the conclusion does not depend on a single variant.

## Phase 7 — MVP Application

### 7.1 User Journey

- Home page and disclaimer.
- Client profile.
- Comparison at the same risk level.
- Technical analysis.
- Monitoring/local export.

### 7.2 Robustness

- Demonstration dataset included.
- Graceful error handling when an artifact is missing.
- Caching, load time, and mobile support.
- Test on a clean computer.

**Done when:** twenty simulated user journeys complete without exceptions and the public link works on a phone.

## Phase 8 — Extensions

Approved order: adaptive questionnaire, unequal risk budgets, filtered regimes, FOMC, Monte Carlo, and report. An extension must be dropped if it threatens application stability or pitch preparation.

## Phase 9 — Presentation

### 9.1 15-Minute Script

1. Client problem — 1 min.
2. Application walkthrough — 4 min.
3. QARM optimization — 4 min.
4. Validation and results — 3 min.
5. Limitations and conclusion — 1 min.
6. Buffer/Q&A — 2 min.

### 9.2 Contingency Plan

- Screenshots or a short video.
- Preloaded local results.
- Prepared client profile.
- Answers to questions about `mu`, BL, costs, look-ahead bias, and target risk.

**Done when:** two rehearsals meet the 15-minute limit, each team member can answer questions about their workstream, and an offline demonstration is available.

## Phase 10 — Final Audit and Release

- Run CI and all tests locally.
- Repeat the installation from a fresh clone.
- Check for secrets, restricted data, licenses, and excluded course materials.
- Freeze the exact artifacts used by the application and pitch.
- Create a presentation tag after cross-review.

**Done when:** the same commit reproduces the same results, launches the application, and supports the offline demonstration.

## Absolute Priority Order

`Data -> baselines -> simple profile -> QARM engines -> sentiment -> backtest -> application -> extensions -> pitch`

Never start an extension to compensate for an incomplete core.

