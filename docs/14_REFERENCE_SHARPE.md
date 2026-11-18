# Step 2.4 — Reference Sharpe for profiling

RiskMatch retains **0.35** as a fixed annual Sharpe assumption for the Tobin
calibration. Under the unconstrained cash-plus-risky-portfolio model of
README §3.8, the tolerance target is `reference_sharpe / risk_aversion`.
The profile then takes the minimum of this target and the capacity ceiling
before assigning a risk category. The resulting portfolio's achievable
volatility depends on later allocation and financing constraints.

The 0.35 assumption predates this sensitivity exercise. It is below the
historical gross Sharpe of SPY and the descriptive 60/40 reference in both
samples. IEF illustrates why that comparison cannot establish a floor.

| Descriptive reference | Main | Extended |
| --- | ---: | ---: |
| SPY | 0.66 | 0.77 |
| IEF | 0.78 | 0.10 |
| 60% SPY / 40% IEF | 0.93 | 0.82 |

The main sample covers 2010-01-04 to 2020-03-31. The extended sample covers
2009-01-02 to 2026-11-17 and overlaps the main sample. Step 2.1 calculates
the ratio from daily arithmetic excess returns using the DTB3 proxy,
normalized by the sample standard deviation of simple returns and annualized
with the square root of 252. The 60/40 reference is rebalanced daily and gross
of costs. These observations provide context for a modeling assumption.
They do not estimate the long-term Sharpe of a future tangency portfolio.

Sensitivity uses the notebook grid of eight risk-aversion values and five
Sharpe assumptions (0.25, 0.30, 0.35, 0.40 and 0.50). At risk aversion 4:

| Reference Sharpe | Tolerance target | Category before cap | Target at illustrative 8% capacity | Category after cap |
| ---: | ---: | --- | ---: | --- |
| 0.25 | 6.25% | Balanced | 6.25% | Balanced |
| 0.30 | 7.50% | Balanced | 7.50% | Balanced |
| 0.35 | 8.75% | Balanced | 8.00% | Balanced |
| 0.40 | 10.00% | Growth | 8.00% | Balanced |
| 0.50 | 12.50% | Aggressive | 8.00% | Balanced |

A move from 0.35 to 0.30 reduces every uncapped tolerance target by 14.29%.
The 8% ceiling illustrates how a capacity constraint changes the result.
It has no effect on the team's choice of capacity scoring rules.

Run `python -m src.build_descriptive` after the common sample build, then
`python -m src.build_reference_sharpe`. The second command checks the input
hashes and creates the evidence CSV, a 40-scenario sensitivity CSV and a
manifest in ignored `results/`. Existing notebook results remain exploratory.
