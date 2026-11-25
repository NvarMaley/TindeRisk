# Method contracts — consolidation

The following specifications define the intended research method independently of data eligibility and empirical acceptance. A weight is a fraction of funded NAV; asset returns are decimal simple total returns in a common currency and period. For daily, weekly and monthly regular observations use respectively 252, 52 and 12 periods per year; scale mean by K and covariance by K, and use geometric compounding for realized wealth. All estimators use data available before the decision. Incomplete observations and unsupported instruments fail closed. Unless a signed method explicitly specifies otherwise, weights are nonnegative and fully funded, and enforce the mandate and costs. A mathematical specification does not certify an implementation.

## Portfolio optimizers

Here μ is annualized expected return, Σ annual covariance, b benchmark weights, rf annual risk-free return, λ nonnegative risk aversion, and C the feasible set. Scenario returns use their original common period, with probabilities summing to one.

| ID | Objective or construction | Specific assumptions |
|---|---|---|
| OPT01 | Project equal weights 1/N onto C by minimum squared distance | Valid dated eligible assets |
| OPT02 | Project cap_i / sum(cap) onto C | Positive dated market caps, absent caps excluded |
| OPT03 | min w′Σw | PSD covariance, feasible budget |
| OPT04 | max (w′μ−rf)/sqrt(w′Σw) | Positive volatility and comparable RF, handle zero risk separately |
| OPT05 | max w′μ−λ w′Σw/2 | λ declared before evaluation |
| OPT06 | min w′Σw subject to w′μ ≥ target | Grid over attainable targets, report infeasibility |
| OPT07 | BL posterior μ=(τΣ inverse + P′Ω inverse P) inverse [ (τΣ) inverse π + P′Ω inverse q ]; π=δΣb | P view matrix, q annual return views, Ω view covariance, τ>0; optimize posterior on C |
| OPT08 | RC_i=w_i(Σw)_i/σp; minimize deviation from b_i σp | Positive normalized risk budgets, σp>0 |
| OPT09 | Distance sqrt((1−ρ)/2); hierarchical tree, recursively split cluster weights by inverse cluster variance | Fixed linkage and ordering; volatility from annual covariance |
| OPT10 | Hierarchical tree with cluster-level risk budgets and within-cluster allocation | Declared cluster count, normalized budgets |
| OPT11 | max w′sqrt(diag Σ)/sqrt(w′Σw) | Positive denominator |
| OPT12 | min z+Σ_s p_s max(−w′r_s−z,0)/(1−α) | Per-period loss scenarios; alpha in (0,1) |
| OPT13 | max (E[rp]−MAR)/sqrt(E[min(rp−MAR,0)^2]) | MAR same period as scenarios, handle zero downside |
| OPT14 | max E[max(rp−T,0)]/E[max(T−rp,0)] | T same period as scenarios, handle zero denominator |
| OPT15 | min maximum drawdown or conditional drawdown-at-risk | Ordered scenario path, declared additive or compounded convention |
| OPT16 | max_w min_(μ,Σ)∈U utility | Declared mean/covariance uncertainty set, preserve C |
| OPT17 | Solve utility for each training bootstrap draw; average feasible weights | Common feasible set, fixed bootstrap seed and block length |
| OPT18 | max_w min_Q∈ambiguity set E_Q[utility] | Declared distance/radius, e.g. Wasserstein |
| OPT19 | max E[log(1+rp)], fractional Kelly mixes feasible solution with feasible reference | Positive scenario wealth; per-period simple return |
| OPT20 | max −Σ w_i log w_i, optionally net utility with entropy penalty | Long-only, 0 log 0=0; penalty specified |
| OPT21 | min (w−b)′Σ(w−b) | Exact dated benchmark, active risk annual |
| OPT22 | max (w−b)′μ/sqrt((w−b)′Σ(w−b)) | Positive tracking error, benchmark weights fixed |

## Investment strategies

Signals are dimensionless ranks or forecasts in declared return units. Targets are computed at decision time and executed with the documented lag. Each strategy has an explicit benchmark, trading cost and turnover convention; derivative margin and short borrow evidence are required when applicable.

| ID | Signal and portfolio construction |
|---|---|
| STR01 | Replicate benchmark weights, or minimize tracking error under sampling constraints. |
| STR02 | Rank historical/forecast alpha, select upper ranks, normalize funded weights, constrain active risk. |
| STR03 | Long top ranks, short bottom ranks; impose gross sum(abs(w)), net sum(w), borrow and funding constraints. |
| STR04 | Optimize ranked long/short targets subject to beta′w≈0 and declared net target, with residual tolerance. |
| STR05 | Macro surprise = released value−prior expectation; preset signed signal-to-exposure map using dated releases. |
| STR06 | Time-series trend sign on prior returns; target notional scaled by estimated volatility; explicit futures rolls/margin. |
| STR07 | Aggregate sleeve budgets α≥0, sum α=1; w=Σ α_k w_k, use joint covariance and shared holdings. |
| STR08 | Fit pair hedge coefficient on training log prices, z-score stationary residual, enter/exit at declared thresholds; borrow both legs. |
| STR09 | Rank standardized factor scores with dated eligible universe; equal or score-weighted selected holdings. |
| STR10 | Alternative fundamental/risk score weighting versus cap-weighted benchmark; normalize positive scores. |
| STR11 | Rank expected annualized carry net of funding, roll, borrow and transaction costs, comparing like currency/horizon only. |
| STR12 | Cross-sectional prior 12–1 month compounded momentum and time-series trend variants; skip most recent month for 12–1. |
| STR13 | Prior-window price/spread z=(x−mean)/sd, contrarian signal at preset thresholds, exit on mean reversion. |
| STR14 | Strategic weights plus bounded tactical signal tilt, projected to C; scheduled rebalance. |
| STR15 | Core benchmark budget plus active sleeves, aggregate exposures and active risk constraints. |
| STR16 | Scale risky weights by min(cap, target annual vol / predicted annual vol); remainder cash, no implicit borrowing. |
| STR17 | Allocate across macro scenario sleeves with declared risk budgets and covariance; no perfect regime hindsight. |
| STR18 | Mix preset regime allocations using filtered probabilities conditional on past observations. |
| STR19 | Conditional downside hedge with funded premium or verified futures margin; evaluate gap risk, carry and net costs. |

## Factors

All cross-sectional scores are evaluated on dated eligible observations, standardized with declared robust clipping and sign. Return exposures use decimal same-period excess returns, dimensionless regression betas, and confidence intervals. Prices, accounting currency, share counts and release dates must agree.

| ID | Definition |
|---|---|
| FAC01 | beta = Cov(asset excess return, market excess return)/Var(market excess return). |
| FAC02 | Book equity/market equity or earnings/market cap, dated filed values, positive denominator. |
| FAC03 | log positive market capitalization; small-minus-big factor return difference. |
| FAC04 | Compound prior months t−12 through t−2; high score = positive momentum. |
| FAC05 | Composite normalized profitability, balance-sheet strength and stability scores, declared signs and weights. |
| FAC06 | Negative trailing annualized volatility or negative beta; high score = lower risk. |
| FAC07 | Operating profitability divided by positive book equity, robust-minus-weak factor. |
| FAC08 | Prior annual asset growth (assets_t/assets_(t−1)−1), low investment score positive; conservative-minus-aggressive factor. |
| FAC09 | Annualized net carry after funding and rolls, instrument-specific cash-flow conventions. |
| FAC10 | Exposure to yield level/term premium; first-order bond price response −duration × yield shift. |
| FAC11 | Monthly curve slope y10−y2 and curvature 2y5−y2−y10, yields in decimal annual units; separate level. |
| FAC12 | Illiquidity = mean(abs daily return / USD volume); spread in basis points; inverse score. |
| FAC13 | CPI surprise = first release minus prior forecast; regress period excess returns on same-unit surprises, documented publication lag. |

## Dynamic portfolio policies

State includes positions, funded cash, time, outstanding flows, previous action, regime information and risk limits. One decision precedes execution. Horizon in monthly periods unless otherwise declared. Reward combines net cash-flow-adjusted return or terminal utility and risk/cost penalties; the policy may act only within verified constraints.

| ID | Contract |
|---|---|
| DYN01 | Filter p_t(s)∝likelihood(r_t∣s)Σ_j transition(j,s)p_(t−1)(j), normalize; no smoothing using future observations. |
| DYN02 | Posterior ∝ likelihood × prior; specify prior and updated return/risk belief, report uncertainty. |
| DYN03 | Re-estimate conditional covariance and RC_i=w_i(Σw)_i/σp; choose target risk budgets and maintain stress limits. |
| DYN04 | Max E[U(W_T)] on a scenario tree with identical actions at nodes sharing observed history; net funding and costs. |
| DYN05 | Joint optimize w_1,…,w_H subject to intertemporal wealth, cash flows, turnover and constraints. |
| DYN06 | Bellman V_t(s)=max_a E[reward(s,a,s′)+V_(t+1)(s′)], finite state/action grid or validated approximation. |
| DYN07 | Receding horizon solve H-step feasible plan, execute first action; update forecast and repeat. |
| DYN08 | Q(s,a)←Q+η(reward+γ max Q(s′,a′)−Q); train on separated history, guardrails and OOD fallback required. |
| DYN09 | Aggregate validated policy outputs with nonnegative normalized weights estimated on validation only; handle missing models. |
| DYN10 | Maximize worst-case conditional reward/terminal wealth over declared bounded uncertainty, recover nominal when radius=0. |

Chapter 26 currently implements reduced-form cash-overlay versions. Full contracts above define remaining extension work.

## Performance, risk and monitoring metrics

Let r denote net period simple return, b matched benchmark return, K regular periods per year, NAV a flow-adjusted wealth index, and L=−r signed loss. Ratios are dimensionless unless specified; undefined denominators produce unavailable values.

| ID | Definition and conventions |
|---|---|
| MET01 | Cumulative return Π(1+r)−1, decimal over observed interval. |
| MET02 | CAGR=(NAV_T/NAV_0)^(1/years)−1, decimal/year; positive wealth. |
| MET03 | TWR=Π subperiod(1+r)−1, partition at cash flows; no flow treated as gain. |
| MET04 | Money-weighted XIRR solves Σ C_i/(1+x)^((date_i−date_0)/365.25)=0, signed investor flows; report no/multiple roots. |
| MET05 | Sample sd(r)√K, annual decimal volatility. |
| MET06 | Sharpe=mean(r−rf)/sd(r−rf)√K, RF matched period/currency. |
| MET07 | Sortino=mean(r−MAR)/sqrt(mean(min(r−MAR,0)^2))√K, MAR period rate. |
| MET08 | Calmar=CAGR/abs(max drawdown), same interval. |
| MET09 | Omega=mean(max(r−T,0))/mean(max(T−r,0)), T period threshold. |
| MET10 | Drawdown NAV/expanding peak−1; MDD min drawdown, duration/recovery in periods; report unrecovered. |
| MET11 | VaR_α=quantile_α(L), signed decimal loss per observed horizon; money loss=VaR×capital. |
| MET12 | ES_α=(1/(1−α))∫_α^1 quantile_u(L)du, fractional boundary mass/ties; signed decimal or base currency. |
| MET13 | Regress asset excess return on benchmark excess return; beta unitless, alpha annualized as intercept×K. |
| MET14 | Tracking error=sd(r−b)√K, matched annual decimal active volatility. |
| MET15 | IR=mean(r−b)√K/sd(r−b), same aligned periods. |
| MET16 | HHI=Σw_i² and effective count=1/HHI only for normalized nonnegative weights. |
| MET17 | RC_i=w_i(Σw)_i/σp, sums to annual portfolio volatility; marginal=(Σw)_i/σp. |
| MET18 | Gross=sum absolute exposures, net=sum signed exposures; FX/sector/factor weights; DV01 dollars per bp, futures notional and margin dollars, separately. |
| MET19 | One-way turnover=Σ abs(Δw)/2 per rebalance, distinguish executed dollar transfers and actual fee ledger. |
| MET20 | Liquidation days=position dollars/(ADV dollars/day × participation), positive dated inputs. |
| MET21 | Weight dispersion and value sensitivity across prespecified perturbations; OOS rank IC=Spearman(prediction, realized return) across same-date assets. |
| MET22 | Reconcile return attribution to allocation, selection, factors, carry, roll, FX and costs over aligned periods; residual explicitly shown. |
| MET23 | P(W_T≥G), E[max(G−W_T,0)] in base currency, funding ratio E[W_T]/G; common dated target and paths. |
