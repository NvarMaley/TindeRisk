# Chapter 26 — Dynamic portfolio management

Research implementation on the frozen chapter 25 USD Match return series. Each policy adjusts the allocation between the user-selected strategy basket and an explicit cash reserve. Strategy budgets inside the invested basket remain fixed at each rebalance. The underlying sleeve backtests already include their own execution costs. Additional transfers between sleeves and cash are charged 10 basis points by default. The ledger records beginning-of-period contributions and withdrawals, fees, drift, target and executed weights, ending wealth and time-weighted returns. Decisions use observations ending at least one month before execution.

| Policy | Implemented research specification |
|---|---|
| Hidden Markov model | Two fixed Gaussian states; recursive belief update with symmetric 8% transition probability; invested fraction = 1 − adverse-state probability |
| Bayesian updating | Beta(1,1) prior on negative excess-return frequency; posterior defensive allocation |
| Dynamic risk budgeting | Invested fraction capped by 10% annual volatility divided by trailing excess-return volatility |
| Stochastic optimization | Grid maximization of empirical scenario expected quadratic utility net of estimated trading cost |
| Multi-period optimization | Joint grid search over three successive allocations with transaction penalties |
| Dynamic programming | Three-step Bellman recursion with regime, allocation state and switching costs |
| Model predictive control | Three-step plan with decaying short-term return forecast; execute first decision and re-estimate |
| Reinforcement learning | Illustrative two-state tabular Q-learning trained on the prior window, with learning rate .15 and discount .8 |
| Ensemble | Equal average of the nine research policies |
| Robust control | Grid maximization of utility with a standard-error penalty on expected excess return |

All policies share an eleven-point allocation grid where applicable, a maximum invested fraction constrained by the conservative maximum individual sleeve scenario loss, and the same historical evaluation dates. The static and drift-threshold policies are baselines. The ledger uses self-financing transaction accounting. No leverage, derivatives, short selling or actual execution is enabled. Cash returns use the frozen Chapter 23 cash baseline. Stress estimates are retrospective proxy scenarios, not verified current exposures.

The policy formulations are pedagogical reduced-form implementations, especially the multi-period, MPC and Q-learning variants. They require further calibration and validation for multi-asset state spaces. Full dated liabilities, current factor drift, settlement, liquidity, margin, market closures and execution freshness are outside the available sleeve data. The API rejects unsupported mandate configurations. This is a simulation and all confirmations remain paper-only.

## Reproducible example

100,000 USD, 60% Mean Reversion and 40% Black-Litterman sleeves, 10 bp additional transfer fee, monthly decisions, no external flows. All twelve policies computed over the 45-month previously examined interval. Static CAGR was 3.96%, drift threshold 3.84%, HMM 3.98%, MPC 4.08% and Q-learning 2.90%. MPC fees were about USD 731 compared with USD 144 for static. These comparisons are descriptive, and the best observed policy is not independently validated. The API additionally returns the doubled-cost and quarterly-rebalance sensitivity for each main policy.
