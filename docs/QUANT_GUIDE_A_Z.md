# ULTIMATE GUIDE — Quantitative Multi-Asset Management Platform

## 0. Mission and Principles
Build a Python platform that converts a client mandate into tailored US allocations, compares competing models, simulates net-of-cost results and manages exposures over time. Returns are not guaranteed. Data, assumptions, models and outputs must be reproducible and versioned.

Pipeline: mandate → universe → point-in-time data → estimation → strategy → optimization → validation → selection → simulated execution → monitoring. Client objectives, strategies, estimators and optimizers are distinct, composable objects. Do not run indiscriminate combinations without statistical controls.

## 1. Client Mandate (Investment Policy Statement)
Build ClientProfile: capital, base currency, horizon, dated contributions/withdrawals, nominal and real goals, liabilities, desired income, tax assumptions, liquidity needs, benchmark, risk capacity and willingness, tolerable losses, ESG/sector/security exclusions, concentration, short selling, leverage, derivatives, turnover, costs and rebalancing frequency. Distinguish hard constraints from soft preferences. Drawdown tolerance is not a guaranteed maximum loss.

Calibrate risk aversion λ using questionnaires and hypothetical lottery/allocation choices; check consistency with financial capacity. Do not automatically map a psychometric score to λ. Mean-variance utility: U = μp − λσp²/2. CRRA utility: U(W) = W^(1−γ)/(1−γ), or log(W) if γ=1. Document units and horizon. Multiple goals have priority, date, amount and shortfall penalty.

Deliverable: validated client_profile.json, readable mandate, feasibility check and incompatible-constraint report.

## 2. US Investment Universe
Start with liquid, representative ETFs, then extend to individual securities and derivatives. Example tickers are candidates to verify, not recommendations.

| Group | Target universe | Example instruments/series |
|---|---|---|
| Equities | US large/mid/small caps, sectors, styles; include delisted securities | Russell 3000 or CRSP US; SPY, IWM, sector ETFs |
| US Treasuries only | T-Bills, Treasury Notes, Treasury Bonds, TIPS | nominal/real curves; Treasury-only ETFs SHY, IEF, TLT, TIP (verify holdings) |
| Real estate | US listed REITs | VNQ, individual REITs |
| Futures | Equity indexes, rates, commodities, currencies | ES, NQ, RTY, ZT, ZF, ZN, ZB, CL, GC; verify specifications |
| Cash | T-bills, interest-bearing cash, collateral | money-market rates and funding costs |
| Hedges | FX/rate/equity futures; options only in an authorized extension | USD/CHF exposure for a Swiss client, liquid instruments |

**Hard restriction:** only debt issued directly by the US Treasury (T-Bills, Notes, Bonds, TIPS) and bond ETFs whose bond exposures are exclusively Treasuries are eligible. No IG/HY corporate debt, MBS, agencies, municipals, foreign sovereign debt or mixed bond ETFs. Verify historical holdings, issuer and type before selection; reject unclassified instruments. Preserve raw data. Original Credit factor is replaced by Treasury Curve (slope/curvature); other catalog identities are unchanged.

MVP: 15–30 equity/Treasury ETFs plus risk-free rate. Phase 2: 300–3000 point-in-time equities and individual Treasuries. Phase 3: per-expiry futures and combined portfolio. Ideal history is 20–30 years where available, daily for risk and monthly for selected signals. Do not invent history before an instrument launched. Identify index proxies explicitly and do not present them as tradable returns.

## 3. Data and Providers
| Dataset | Minimum fields | Candidate sources (verify access, licenses and coverage) |
|---|---|---|
| Equities/ETFs | OHLCV, dividends, splits, delisting returns, persistent IDs, historical membership | CRSP/WRDS, Bloomberg, FactSet, price vendors; SEC EDGAR for statements |
| Fundamentals | actual publication time, period, revisions, earnings, cash flow, debt, market cap | SEC EDGAR, point-in-time Compustat |
| Treasuries | CUSIP, issuer, type, coupon, maturity, clean/dirty price, accrued interest, yield, cash flows, TIPS CPI index ratio, bid/ask | US Treasury and verified price/curve provider |
| Futures | contract, expiry, settlement, multiplier, tick, volume, open interest, margin, roll schedule | CME, ICE, contract-level history provider |
| Macro | GDP, CPI, unemployment, nominal/real rates, curve slope, revisions, availability dates | FRED/ALFRED, BEA, BLS, US Treasury |
| Factors | market, SMB, HML, RMW, CMA, momentum, frequency and units | Kenneth French Data Library; internally constructed factors |
| FX/funding | USD/CHF, cash rate, borrow and margin funding costs | central banks, brokers, market data provider |

Starting links: https://fred.stlouisfed.org/ ; https://www.sec.gov/edgar ; https://wrds-www.wharton.upenn.edu/ ; https://www.cmegroup.com/ ; https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html . These are indicative links, not verification of current offerings.

### 3.1 Pipeline
- Store immutable raw, normalized cleaned data and versioned features in Parquet; DuckDB catalog, UTC timestamps and local market calendars.
- Schema: security_master(id, ticker, asset_class, currency, valid_from, valid_to, multiplier); prices(id, timestamp, open, high, low, close, volume, availability_time); corporate_actions; fundamentals; contracts; curves; macro_vintages; benchmark_membership.
- As-of joins require availability_time ≤ decision time. Keep historical membership, bankruptcies and ticker changes. Do not forward-fill nontradable assets; distinguish market holidays from missing data.
- Equity total return: (P_t + D_t)/P_(t−1) − 1 with correct split treatment; do not double-count dividends on adjusted prices.
- Futures P&L = contract quantity × multiplier × price change of held contract; continuous series only for signals, actual contract P&L and roll. Prices may be negative; do not require log returns.
- Treasuries: dirty price = clean price + accrued interest; total return = dirty-price change plus coupons received, divided by initial value; handle maturity redemption and TIPS indexation without double counting. Date curves and cash flows.
- Client currency return: (1+r_USD)(1+r_FX)−1 with FX expressed as client currency per USD. Distinguish hedged and unhedged exposure.

Tests: uniqueness, timestamps, gaps, splits, outliers, historical coverage, P&L reconciliation and no look-ahead leakage.

## 4. Quantitative Analytics and Estimation
Conventions: r_t=P_t/P_(t−1)−1, log r=ln(1+r), CAGR=(V_T/V_0)^(1/years)−1 without external cash flows, arithmetic mean for mean-variance, annual volatility ≈ daily σ√252 under standard assumptions. Covariance Σ=Cov(r), correlation ρij=Σij/(σiσj). Do not mix frequencies or nominal/real returns. Historical estimates alone are not reliable forecasts.

| Module | Methods to implement | Calculation and validation |
|---|---|---|
| Returns | historical mean, EWMA, CAPM, Black-Litterman | μ_EWMA=Σ a_k r_(t−k), decreasing a_k; CAPM rf+β×market premium; compare OOS errors |
| Forecasting | Ridge, Lasso, Elastic Net, Random Forest, XGBoost, neural networks | y=future return; lagged features; MSE, rank IC, calibration, net performance |
| Volatility | historical, EWMA, GARCH, EGARCH, GJR-GARCH | EWMA h_t=αh_(t−1)+(1−α)ε²_(t−1); GARCH h=ω+aε²+bh_prev; EGARCH log(h) and asymmetry; GJR adds negative-shock indicator |
| Covariance | empirical, Ledoit-Wolf, OAS, DCC-GARCH | shrinkage Σ̂=(1−δ)S+δF; DCC combines conditional volatilities and dynamic correlations; check PSD |
| Factors | CAPM, Fama-French, PCA, multifactor | r−rf=α+β'f+ε; Σ=BΣ_f B'+Σ_ε; PCA on standardized matrix or covariance depending on objective |
| Tail risk | VaR, ES, EVT, copulas | L=−r; VaRα=quantileα(L); ESα=upper-tail mean (integral definition for atoms); peaks-over-threshold EVT and tail dependence via copulas |
| Regimes | HMM, Markov switching, clustering | latent state, transition Pij, filtered probabilities (not smoothed with future data) |
| Uncertainty | block bootstrap, Bayesian, Monte Carlo | parameter intervals, predictive distributions, correlated scenarios and heavy tails |
| Treasuries | Macaulay/modified/effective/key-rate duration, convexity, DV01, slope/curvature, real yields and inflation breakeven | D_mod=−(1/P)∂P/∂y; ΔP/P≈−D_modΔy+0.5CΔy²; DV01≈P×D_mod×0.0001; curve bumps for key rates |
| Futures | momentum, carry, roll, basis, volatility, margin | exposure N×mult×price/NAV; daily variation margin; annualized carry per contract convention; actual roll and costs |

Black-Litterman: π=δΣw_market; views Pμ=q with uncertainty Ω; μ_BL=[(τΣ)^−1+P'Ω^−1P]^−1[(τΣ)^−1π+P'Ω^−1q]. Document prior, confidence and excess versus total returns. Test conflicting views and weak/strong confidence.

## 5. Catalog of Client Objectives (11)
| Objective | Decision function / control |
|---|---|
| Capital Preservation | minimize nominal/real loss risk over horizon |
| Income | net income and distribution stability |
| Conservative | strict volatility and loss budget |
| Balanced | multi-asset risk-return trade-off |
| Growth | terminal wealth and real return |
| Aggressive Growth | high growth subject to explicit risk budget |
| Inflation Protection | real return, inflation sensitivity and TIPS |
| Absolute Return | net return relative to cash, downside risk |
| Liability-Driven (LDI) | minimize asset-liability shortfall and DV01 mismatch |
| Goal-Based | maximize probability of funding dated goals |
| Capital Protection | explicit hedge, conditional floor, gap risk and cost; no guarantee without contractual mechanism |

## 6. Catalog of 22 Construction Methods
Notation: w funded weights, μ expected-return vector, Σ covariance, σp=√(w'Σw), rp=w'r, rf risk-free rate, b benchmark, L losses, T threshold. All methods receive the same mandate and return status, weights, objectives, active constraints and diagnostics.

| Method | Objective / algorithm | Caveat |
|---|---|---|
| Equal Weight | w=1/N (project onto constraints if needed) | turnover |
| Market Cap Weighted | w_i=cap_i/Σcap | concentration; primarily equity benchmark |
| Minimum Variance | min w'Σw | covariance and concentration |
| Maximum Sharpe | max (w'μ−rf)/σp | uncertain returns; reformulation or frontier search |
| Maximum Utility | max w'μ−λw'Σw/2 | λ calibration |
| Efficient Frontier | minimum variance per target return | infeasible targets |
| Black-Litterman | posterior μ then chosen optimizer | views and confidence; not standalone optimizer |
| Risk Parity | RC_i=w_i(Σw)_i/σp; RC_i=b_iσp | negative contributions and leverage |
| Hierarchical Risk Parity | distance √((1−ρ)/2), clustering, recursive inverse-variance allocation | dendrogram stability |
| Hierarchical Equal Risk Contribution | clusters then hierarchical risk budgets | cluster choice |
| Maximum Diversification | max (w'σ)/σp | unstable correlations |
| Minimum CVaR | min z+Σp_s max(L_s−z,0)/(1−α) | tail size and scenarios |
| Maximum Sortino | max (E[r]−T)/√E[min(r−T,0)²] | threshold and frequency |
| Maximum Omega | max E[(r−T)+]/E[(T−r)+] | zero denominator |
| Minimum Drawdown | min max_t(1−V_t/max_{u≤t}V_u) or CDaR | path dependence; possible nonconvexity |
| Robust Optimization | max_w min_{μ,Σ in set} U(w) | uncertainty-set calibration |
| Resampled Efficient | bootstrap parameters, optimize, aggregate weights and validate constraints | resampling bias |
| Distributionally Robust | minimize worst risk over distribution set (e.g. Wasserstein) | radius and numerical cost |
| Kelly | max E[log(1+r_p)] | ruin risk, fractional Kelly, bounded losses |
| Entropy-Based | max −Σw_i log(w_i) with risk/return constraints | directly applies to positive weights |
| Tracking Error Min | min (w−b)'Σ(w−b) | appropriate benchmark |
| Maximum Information Ratio | max (w−b)'μ/√((w−b)'Σ(w−b)) | costs and alpha estimation error |

### 6.1 Common Constraints
Σw=1 for funded assets; asset/class/sector limits, liquidity, turnover Σ|w−w_old|, beta and factors, target return, volatility, duration/DV01 and curve risk budgets, short and gross/net exposure, transaction costs. Futures use separate integer q (or relaxation then validated rounding), notional=q×mult×price; initial/maintenance margin, cash reserves and margin stress. Do not add futures notional to funded weight sums as if fully funded. Daily cash ledger, funding and collateral. Test feasibility before optimization; never silently relax hard constraints.

## 7. Catalog of 19 Investment Strategies
Each defines signal, eligible universe, horizon, target portfolio, positioning/exit rules, benchmark, costs and risks. It can use multiple optimizers from chapter 6.

| Strategy | Reference implementation | Specific validation |
|---|---|---|
| Passive | replicate index with historical weights or sampling | net tracking error |
| Active Long Only | alpha score then w≥0 constraints | alpha vs benchmark |
| Long/Short | buy high scores, short low scores | borrow, gross/net, squeeze |
| Market Neutral | long/short with β≈0, optional dollar neutrality | realized beta and residual factors |
| Global Macro | growth/inflation/rate signals, futures/ETF allocation | PIT macro surprises |
| Managed Futures / CTA | multi-market time-series momentum, volatility scaling | roll, margin, whipsaw |
| Multi-Strategy | combine sleeves with risk budgets | crisis correlations |
| Statistical Arbitrage | stationary spreads/cointegration, z-score | stability, costs, relationship breakdown |
| Factor Investing | value/quality/momentum/etc. scores | exposures and net premia |
| Smart Beta | transparent cap-weight alternative | concentration, turnover |
| Carry | net carry ranked by instrument | crash risk, funding |
| Momentum | past 12–1 month returns or time-series trends | lookback, costs, reversals |
| Mean Reversion | deviation from mean/spread, entry/exit thresholds | structural break |
| Tactical Asset Allocation | bounded strategic-allocation deviations | value added vs fixed allocation |
| Core-Satellite | index core and active satellites | active-risk budget |
| Volatility Targeting | exposure ≈ σ_target/σ_forecast, capped | procyclicality, leverage |
| All Weather | balance growth/inflation and rate shocks | changing scenarios and correlations |
| Regime Switching | allocations conditional on filtered probabilities | transitions and regime uncertainty |
| Tail Risk Hedging | conditional hedge; futures reduce linear exposure, options for convexity if authorized | carry cost and gap risk |

## 8. Catalog of 13 Factors
Market (β), Value (book-to-market/earnings yield), Size (market cap), Momentum (12–1 months), Quality (profitability, leverage, stability), Low Volatility (low volatility/beta), Profitability (RMW or operating profitability), Investment (asset growth/CMA), Carry (net carry), Term (duration/term premium and yield level), Treasury Curve (10Y−2Y slope and 2×5Y−2Y−10Y curvature), Liquidity (bid-ask, Amihud), Inflation (CPI-surprise sensitivity). Construct cross-sectional winsorized, normalized and optionally sector/size-neutralized scores. Use only data available at the date and handle missing values. Estimate beta with OLS/rolling/ridge, robust errors for significance, and BΣ_fB' for risk contributions. Check collinearity and double counting, especially Term and Treasury Curve. Evaluate IC, turnover, stability and OOS factor returns.

## 9. Institutional Backtesting
Event-driven or vectorized engine reconciled to the ledger: at t observe available data → signal → optimize → order → execute at t+1 or realistic delay → costs → P&L → NAV. No fills at prices observed before decision. Model commissions, bid-ask, slippage, market impact (size/ADV), borrow, funding, applicable taxes, roll, variation margin, coupons and dividends. Do not use present-day index membership historically.

Walk-forward: e.g. five-year train / one-year validation / one-year test, then roll; lock final holdout. Apply purging/embargo for overlapping labels; tune only on train/validation; final test once. Benchmarks: cash, S&P 500 total return, 60/40, mandate benchmark, 1/N; same currencies and dates. Log all experiments and trials; control multiple testing (Deflated Sharpe, bootstrap, reality check as appropriate). Test missing data, crises, doubled fees, latency, parameter changes and capacity.

## 10. Required Calculations for Each Portfolio
| Metric | Formula / definition |
|---|---|
| Cumulative return | product(1+r_t)−1 |
| CAGR | (NAV_final/NAV_initial)^(1/years)−1 without flows; TWR with flows, MWR/IRR for client experience |
| Volatility | sd(r_t)√K; state assumptions |
| Sharpe | mean(r−rf)/sd(r−rf)×√K |
| Sortino | return above MAR / downside deviation, consistent annualization |
| Calmar | CAGR / abs(MDD) |
| Omega | E[(r−T)+]/E[(T−r)+] |
| Drawdown | NAV_t/historical max NAV−1; MDD=min drawdown; time below peak and recovery |
| VaR / ES | loss quantile and tail mean, 95/99%, specified horizon |
| Beta / Alpha | excess-return regression on benchmark/factors; annualized alpha with convention |
| Tracking Error | sd(rp−rb)√K |
| Information Ratio | mean(rp−rb)√K/sd(rp−rb) |
| HHI / effective number | Σw² and 1/HHI for normalized long weights; distinguish effective bets based on risk contributions |
| Risk contribution | w_i(Σw)_i/σp; marginal contribution (Σw)_i/σp |
| Exposures | gross/net, sectors, factors, FX, duration, DV01/key-rate DV01, futures notionals and margin |
| Costs | commissions + spread + impact + borrow + funding + roll; turnover per convention |
| Liquidity | liquidation days ≈ position/(ADV×allowed participation), liquidity stress |
| Robustness | cross-window weight variance, parameter sensitivity, OOS performance and intervals |
| Client goals | P(W_T≥G), E[(G−W_T)+], conditional shortfall, liability/income coverage |

Produce performance attribution (allocation/selection, factors, carry, roll, FX, costs), risk attribution by asset/class/factor, gross/net reports and benchmark comparisons. VaR is not a guaranteed maximum loss.

## 11. Scenarios, Stress Testing and Monte Carlo
Replay dot-com, 2008, COVID 2020 and 2022 rate increases when covered. Hypothetical scenarios: US recession, persistent inflation, rates +200 bps, curve steepening/flattening, real-yield and breakeven shocks, equities −30%, simultaneous equity/Treasury falls, reduced liquidity, USD/CHF shock and higher margins. Revalue positions/derivatives, calculate losses, shortfall, margin, concentration and liquidation capacity. Distinguish historical realized and hypothetical stress.

Monte Carlo: multivariate normal paths as reference; Student-t, block bootstrap, regimes or copulas as alternatives. Simulate client flows, inflation, costs, rebalancing, sovereign-rate risk, FX and collateral. W_(t+1)=(W_t+flow_t)(1+r_(t+1))−cost_t per timing convention. Report 5/25/50/75/95 percentiles, success probability and shortfall; parameter sensitivity as well as process uncertainty. Seed reproducibility; assess convergence by Monte Carlo error.

## 12. Personalized Selection and Portfolio Improvement
1. Generate candidates (objective × strategy × estimator × optimizer), retain simple benchmarks.
2. Exclude infeasible candidates, insufficient data, mandate or margin violations.
3. Rank on client goals and net OOS performance; compare return-volatility, return-ES, return-drawdown, alpha-TE, wealth-shortfall and liability-coverage frontiers.
4. Normalize multicriteria score using client weights, soft penalties and sensitivity; avoid double-counting Sharpe/volatility. Present a Pareto frontier rather than opaque score.
5. Retain 3–5 candidates: conservative, efficient, robust, goal-driven and optionally active. Provide positions, reasons, costs, risks, scenarios, uncertainty and benchmark differences.
6. Improve through shrinkage, regularization, concentration/turnover limits, factor diversification, improved forecasts, robust optimization, ensembles, hedge overlays and regime adaptation. Measure incremental gain on identical OOS windows; retain simpler model if improvement is not robust.
7. Ablation: remove each module and compare net performance, risk and stability. Never select a model solely for maximizing historical Sharpe.

Separate scientific improvement from final matching (IMP.01–02 before MATCH.01); use the dependency roadmap for delivery.

## 13. Ten Dynamic Management Methods
| Method | Development rule |
|---|---|
| Hidden Markov Model | filtered regime probabilities, probability-weighted allocation |
| Bayesian Updating | update posterior with new data; retain prior and uncertainty |
| Dynamic Risk Budgeting | recompute RC and budgets by mandate/regime |
| Stochastic Optimization | maximize expected utility on nonanticipative scenario tree |
| Multi-Period Optimization | successive w_t decisions, costs, flows, intertemporal constraints |
| Dynamic Programming | wealth/time/regime state; Bellman V_t(s)=max_a E[reward+V_(t+1)] |
| Model Predictive Control | optimize horizon H, apply first decision, repeat |
| Reinforcement Learning | state, action, net risk-penalized reward, simulator and guardrails; compare simple rules |
| Ensemble Models | aggregate forecasts/weights with OOS-validated weights |
| Robust Control | optimal policy under bounded perturbations/adversity |

Rebalancing: monthly/quarterly schedule or drift threshold, cost vs expected gain. Daily monitoring of NAV, risk, margins and constraints. Stop simulated orders on stale data, errors or violations; human validation and audit log. Paper trading before any real execution.

## 14. Software Architecture of the Ten Engines
```text
quant_asset_management/
├── configs/                 # mandates, universe, models, costs
├── data/{raw,clean,features}/
├── src/
│   ├── client/              # 01 Client Profiling Engine
│   ├── data/                # 02 Market Data Engine
│   ├── analytics/           # 03 Quantitative Analytics Engine
│   ├── forecasting/         # 04 Forecasting Engine
│   ├── risk/                # 05 Risk Engine
│   ├── optimization/       # 06 Portfolio Optimization Engine
│   ├── backtest/            # 07 Backtesting Engine
│   ├── simulation/         # 08 Scenario & Simulation Engine
│   ├── selection/          # 09 Portfolio Selection Engine
│   ├── management/         # 10 Dynamic Management Engine
│   ├── execution/          # paper broker, ledger and orders
│   └── reporting/          # dashboard and reports
├── tests/{unit,integration,regression}/
├── experiments/             # immutable configurations and results
├── notebooks/               # research, not production logic
├── app/                     # user interface
├── pyproject.toml
└── README.md
```

Candidate stack: Python, NumPy, Pandas/Polars, PyArrow, DuckDB, SciPy, CVXPY (Clarabel/OSQP depending on formulation), PyPortfolioOpt, Riskfolio-Lib, QuantLib, statsmodels, arch, scikit-learn, XGBoost, pytest, Pydantic, Plotly/Streamlit, FastAPI for separate UI. Verify versions, licenses and solvers; pin environment and seed. For production: authentication, secrets outside repo, backups, access rights, logs, monitoring and human review.

### 14.1 Module Contracts
| Engine | Input | Persisted output |
|---|---|---|
| Client | questionnaire and goals | ClientProfile, ConstraintSet |
| Data | providers, dates, universe | MarketSnapshot, availability timestamps |
| Analytics | cleaned series | FeaturePanel, FactorExposure |
| Forecast | features, history, model | ForecastBundle(μ, distribution, horizon, confidence) |
| Risk | positions, Σ, scenarios | RiskReport, risk contributions |
| Optimization | ForecastBundle, constraints, current positions | PortfolioCandidate, solver diagnostics |
| Backtest | strategy and sequential snapshots | NAV, fills, ledger, OOS metrics |
| Simulation | candidate, flows, scenarios | wealth distribution and stress |
| Selection | candidates, diagnostics, mandate | shortlist, Pareto front, explanations |
| Management | current portfolio, new data | target weights, proposed orders, alerts |

Every output carries as_of, run_id, model_version, data_version, units, warnings. No implicit data later than as_of. Infeasible or failed results produce no orders.

## 15. Executable Roadmap (Dependency Order)
This original sequence preserves scope. Follow the [collaborative roadmap](ROADMAP.md) and [dependency registry](TASK_DEPENDENCIES.csv) for detailed operational prerequisites, separating minimal backtest, scientific improvement and final matching.

| Step | Work | Acceptance criterion |
|---|---|---|
| 01 | Define conventions, US scope, currency, typical mandate, schemas | valid mandate, incompatible constraints detected |
| 02 | Install environment, scaffold, tests and data catalog | reproducible clean-machine run |
| 03 | Collect 15–30 ETFs, cash, benchmarks and macro | reconciled total returns, availability control |
| 04 | Build returns/covariance/volatility engine | two-asset analytical cases, PSD Σ |
| 05 | Implement 1/N, cap-weight benchmark, minimum variance, max utility, max Sharpe, frontier | verified weights/constraints, known solution comparison |
| 06 | Backtest fixed then rebalanced portfolios | reconciled ledger, costs, no-look-ahead |
| 07 | Add metrics, stress, Monte Carlo and client goals | signs, units, convergence, reproducible scenarios |
| 08 | Add other construction methods, HRP/HERC and robust risk models | unit tests and common benchmark per method |
| 09 | Add individual securities, factors, long-only signals and PIT fundamentals | delistings included, leakage tests and exposures |
| 10 | Add individual Treasuries, curves, cash flows, LDI | price and DV01 verified by curve bump |
| 11 | Add futures, margin, roll and collateral | exact contract P&L and verified margin reserve |
| 12 | Implement remaining 19 strategies | specific tests and net OOS results |
| 13 | Add ML, advanced Black-Litterman, regimes and ensembles | beat or complement baseline without final-test tuning |
| 14 | Add 10 dynamic techniques starting simple | constraints each period and fixed-policy comparison |
| 15 | Build selection engine, report and client interface | explainable shortlist, scenarios and exclusion reasons |
| 16 | Paper trading, monitoring and independent validation | reconciliation, alerts, failure tests, human approval |

Unvalidated stages block dependent work. The objective is not 75 labels but financially correct, tested and comparable modules.

## 16. Minimum Testing Plan per Model
- Unit tests: synthetic data, zero volatility, perfect correlation, incompatible constraints, missing returns, negative futures price, Treasury near maturity, zero weights and denominators.
- Optimizer tests: weight sum, bounds, budgets, constraint residuals within documented tolerance, convergence, analytical comparison where possible. Do not claim global optimum for nonconvex solutions without proof.
- Integration: snapshot → forecast → allocation → simulated orders → ledger → report. Reconcile NAV and flows at every date.
- Regression: changing data after t must not change decision at t; zero then positive costs; identical seed/version reproduce results.
- Economic validation: net performance, risk, capacity, robustness, model drift, interpretability and strategy limitations.

## 17. Final UI and Deliverables per Client
Screens: (1) profile/mandate; (2) universe and availability; (3) asset analytics; (4) strategy/optimizer configurator; (5) interactive efficient frontier; (6) portfolio comparison; (7) exposures/attribution; (8) stress tests and wealth fan chart; (9) recommendations with active constraints; (10) monitoring and simulated orders.

Export per candidate: weights.csv, positions.csv, trades.csv, nav.csv, metrics.json, exposures.csv, scenarios.csv, assumptions.json, audit_log and readable report. Show dates, currency, benchmark, historical period, OOS performance and costs. Visualizations: asset/class/sector allocation, correlation, risk contributions, NAV and drawdown, rolling Sharpe/volatility, frontier, loss distribution, fan chart, scenario comparison and turnover.

## 18. Definition of Project Success
- [ ] All 11 objectives can be expressed in a mandate and evaluated.
- [ ] All 22 construction methods are documented, tested and accessible (Black-Litterman as estimator combined with optimizer).
- [ ] All 19 strategies have reproducible rules and benchmarks.
- [ ] All 13 factors are measurable with dated data.
- [ ] All 10 dynamic methods are separate, comparable modules.
- [ ] Equities, Treasuries and futures are accounted for without double counting.
- [ ] OOS tests include costs, PIT data and extreme scenarios.
- [ ] Select multiple genuinely compatible candidates or explain why none is feasible.
- [ ] Every recommendation includes uncertainty and audit trail.
- [ ] No real orders without authorization and validation of applicable operational and regulatory controls.

## 19. First Concrete Task
Create repository, ClientProfile schema, reference ETF universe, total-return pipeline, three baselines (1/N, 60/40 and cash), then constrained mean-variance engine. Produce first walk-forward backtest with fees and standardized report. Only then extend progressively. This is a specification, not completed implementation or empirical strategy validation.

## 20. RiskMatch Extension — Behavioral Discovery and Matching
The financial mandate remains the source of truth for constraints. Upstream, RiskMatch Discovery offers simulated choices (like/dislike/unsure/skip) to estimate an exploratory 1–30 risk-aversion score and separate preferences. Downstream, RiskMatch Explore offers only compatible, independently evaluated candidates with comparable metrics, uncertainty, scenarios and costs. Likes create a shortlist, not trades; explicit confirmation is required for paper selection.

Complementary specifications: [behavioral protocol](RISKMATCH_BEHAVIORAL.md), [matching](PORTFOLIO_MATCHING.md), [architecture](ARCHITECTURE.md), [roadmap](ROADMAP.md), [security](DATA_SECURITY.md). These extend the 75-entry financial catalog rather than replacing it.
