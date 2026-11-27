# RiskMatch Explore — Portfolio Matching

Current full-mandate matching uses the [personalized construction engine](PERSONALIZED_MATCHING.md).
It replaces the shared five-ETF deck as the normal client route, while
preserving that deck for legacy research. The specification below describes
the intended complete research workflow and outstanding acceptance criteria.

## Pipeline
1. Generate candidates from mandate, strategies and construction methods in the A–Z guide. Retain versioned models, data and assumptions.
2. Filter hard constraints (liquidity, concentration, leverage, derivatives, financial capacity, currency, horizon). If required risk is incompatible, explain the funding gap and offer to reconsider horizon, contributions or goal; never raise risk automatically.
3. Evaluate out of sample, costs, stress, scenarios and uncertainty. Eliminate invalid or dominated models on relevant criteria. Never guarantee historical drawdown limits.
4. Feature up to six compatible allocations ranked by mandate fit, with at least 5% of capital reallocated between any pair. Keep the full compatible deck and same-period comparison accessible from the first card. The test-period return does not determine the featured rank.
5. Like/dislike/skip and undo. Optional reason: loss, income, horizon, complexity, ESG, fees. Do not infer new risk tolerance from likes alone.
6. Compare shortlist, benchmark and simple reference. If no compatible preference, ask for clarification rather than force a match.
7. Open My Matches to combine one or more liked strategies into a single funded allocation, manually or with RiskMatch optimization. Recheck aggregate mandate, data and costs before explicit choice.

## My Matches — allocation across strategies

Consolidation: the full fictional USD mandate can now be evaluated against the confirmed Match allocation through `/api/matching/goals`. It uses 1,000 common six-month block-bootstrap paths from the historical development sample and the existing typed financial-objective engine, paired with the 60/40 benchmark. Dated flows, priorities, target probability and expected deficit are evaluated when defined. Actual income distributions, contractual hedge costs and liability DV01 are still unavailable for abstract sleeve paths; results are conditional, not a guarantee or suitability approval.

Combined monthly allocations now charge a further 10 bp on executed transfers between sleeves, starting from the specified allocation. A self-financing ledger reconciles each period; net sleeve P&L components sum to net return and their covariance contributions reconcile to the combined volatility. The minimum-variance optimizer still uses development gross sleeve covariance for the target proposal; the evaluation uses net transfer costs. Goal projections sample the development net blend. This does not change the frozen deck identity or the individual sleeve ledgers.

A like expresses a preference, not an investment order or a new risk tolerance. Model each eligible liked strategy as a sleeve with versioned holdings and a capital budget `alpha_k >= 0`, with `sum(alpha_k) = 1`. The consolidated funded holdings are `w_global = sum(alpha_k * w_k)`. Consolidate overlapping securities by stable identity rather than treating repeated names as diversification. Derivative notionals, collateral, financing and cash require separate accounting; unsupported instrument combinations remain unavailable.

- Manual mode: editable percentages, total and currency amounts, with clear validation and no automatic override of client preferences.
- Optimized mode: propose budgets among liked eligible sleeves only, using a documented client-objective utility or risk objective and explicit aggregate constraints. Never force a match or relax a hard constraint.
- Recompute risk using common dated return paths and consolidated exposures (including cross-sleeve covariance, concentration, liquidity, FX, stress and tail risk). CAGR, drawdown and ES are not weighted averages of individual reported metrics. Compare costs, turnover, goal success and common-period net out-of-sample results against a reference portfolio. Specify sleeve rebalancing and execution assumptions.
- Display strategy budgets, actual underlying exposure, concentration overlap, correlations, risk contributions and mandate fit. Infeasible or unverified aggregate allocations cannot be confirmed. Changing mandate, likes or candidate versions invalidates the prior allocation; store and revalidate it before paper-only confirmation.

Implementation and acceptance are tracked by CH25.22–28; the existing synthetic shortlist is not evidence of a validated multi-Match allocator.

## Standard Card
Name, objective, asset classes, allocation and futures notionals, expected return with interval and assumptions, volatility, ES, historical drawdown and stress, estimated goal probability, costs, turnover, currency, FX risk, liquidity, benchmark, OOS period and calculation date. Distinguish realized, simulated and forecast data. Show loss percentages and currency, fit reasons and limitations.

## Ranking
After hard filtering, normalize criteria on documented stable scales. Example S=Σ w_j u_j(x_j), weights from explicit client goals, sum=1. Criteria may include success probability, ES, costs, robustness, simplicity and preferences. Test weight sensitivity and display tradeoffs. Likes are soft preferences, never overrides of hard guardrails. Construction methods are not 22 indistinct products.

## Proposed States and API
candidate → validated → presented → liked/disliked/skipped → shortlisted → allocated → aggregate_validated → reviewed → selected_for_paper_trading. API POST /profiles, GET /sessions/{id}/cards, POST /sessions/{id}/responses, GET /profiles/{id}/risk-report, POST /portfolio-runs, GET /portfolio-runs/{id}/candidates, POST /candidates/{id}/swipes, proposed POST /match-allocations/evaluate and POST /match-allocations/optimize, POST /selections. Authentication, ownership checks, idempotency, minimal sensitive logging. No real-order endpoint in MVP.
