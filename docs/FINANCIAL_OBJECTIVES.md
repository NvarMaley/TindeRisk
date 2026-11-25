# Chapter 12 — Financial objectives

The client mandate remains the source of truth. A typed goal specifies an objective ID, due date, nominal target converted into mandate currency, funding flag, priority and penalty. Separate the function being evaluated from eligibility, benchmark, risk measure and preference. No objective label is used as a portfolio strategy or as a prediction.

| Objective | Research measure | Additional input or limitation |
|---|---|---|
| OBJ01 Capital preservation | probability of nominal/real market loss and expected deficit relative to starting capital | separate cash-flow adjusted wealth |
| OBJ02 Income | dated withdrawals paid; total-return minus price-return distribution component, coverage and dispersion | proxy only; actual cash distribution timing, taxes and costs not certified |
| OBJ03 Conservative | annualized reference volatility, monthly ES95 and drawdown threshold exceedance | hard stress and liquidity tests separate |
| OBJ04 Balanced | mean annual path CAGR minus lambda/2 times CAGR variance, lambda sensitivity 1,3,10 | illustrative sensitivity, not client utility calibration |
| OBJ05 Growth | expected dated wealth and real annual market CAGR | avoid treating deposits as return |
| OBJ06 Aggressive growth | same growth measures with risk and leverage constraints | no leverage used in references |
| OBJ07 Inflation protection | real wealth and CAGR under inflation and +2 percentage point shock | historical CPI beta not certified |
| OBJ08 Absolute return | annual path CAGR minus contemporaneous BIL proxy CAGR; downside utility | BIL is not a risk-free cash deposit |
| OBJ09 LDI | dated liabilities paid, unpaid expected liability, funding deficit | PV/key-rate DV01 matching requires dated curve and holdings cash flows |
| OBJ10 Goal-based | probability of wealth >= target, expected deficit, quantiles | conditional scenario probability only |
| OBJ11 Capital protection | explicit target-floor shortfall and loss probability | no hedge certification or contractual guarantee |

## Math and conventions

Cash flows and goals use actual dates. Between events inside an anniversary month, compound `(1+r_month)^(elapsed_days/full_month_days)`, an interpolation assumption. At each event, add deposits, then pay liabilities and withdrawals from available wealth. Before funding, evaluate nonfunding targets; funded goals are paid in descending priority, ties in input order. Missing payments are recorded as deficits; no borrowing, double spending or retroactive recovery. Funding probability is measured immediately before payment. Nominal targets use `real_target*(1+inflation)^years` and explicit FX scenario from mandate. Zero-return gap and required dated annual return use the existing mandate checks. Required return is a hurdle, not a predicted or necessarily feasible return.

Expected deficit `mean(max(G-W,0))` is in base currency; probability is a fraction; normalized shortfall is deficit/G. Multi-goal penalty is `sum(priority/sum(priority)*penalty*normalized_shortfall)`. Missing targets are excluded and weight coverage is displayed rather than treated as zero loss. Risk metrics based on market wealth exclude external cash flows. Drawdown exceedance is a scenario diagnostic, not a verified mandate stress test. The standard error sqrt(p(1-p)/N) only measures conditional Monte Carlo sampling variability, not uncertainty about future returns.

## Actual local historical evaluation

Fixed monthly rebalanced mixes of SPY/SHY/BIL/TIP, respectively: 0/60/40/0%, 50/30/10/10%, 80/10/5/5%, 20/20/10/50%. All use the identical aligned historical returns and random draws in the requested base currency. CRSP monthly total and price returns, exact common start/end dates; 223 USD and 219 CHF monthly observations, June 2007–December 2025. Chronological 80/20 partition; 2,000 six-month moving-block scenarios from training only, seed 12. CHF gaps exclude blocks spanning breaks; no missing returns imputed. Holdout cumulative performance/drawdown withheld if noncontinuous. Source lacks original publication timestamps, so archive research is not certified point-in-time. Gross of transaction costs and taxes; fund expenses embedded in observed fund return. No recommendation, ranking, optimization or suitability certification. Known asset-class/weight/exposure/volatility constraints tested; unverified constraints explicitly marked. Inflation scenario is deterministic, +2 percentage point sensitivity with common draws.

For LDI the report additionally gives liability PV, starting capital minus PV and liability DV01 via symmetric one-basis-point shocks to an illustrative flat discount rate (historical training BIL geometric return); this is not a fitted liability discount curve. Asset DV01 and key-rate mismatches remain unavailable.

Use the confirmed mandate page, Chapter 12, in the local application. API `POST /api/objectives/evaluate` accepts the existing validated mandate JSON and returns aggregated scenario results, not raw licensed data. The example mandate is fictional. Do not commit user mandates, scenario outputs or source data. Independent acceptance, full instrument/portfolio income, asset-side LDI DV01 and hedge contracts, calibration and hard mandate stress feasibility remain open.
