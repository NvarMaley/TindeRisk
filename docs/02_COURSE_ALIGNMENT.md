# Alignment Between the Courses and RiskMatch

## 1. QARM II — Primary Framework

| Chapter | Concept used | Location in RiskMatch | Mandatory control |
|---|---|---|---|
| LN1 | Return, covariance, frontier, constraints, tangency, Tobin | Estimation, Classical, target volatility | Consistent units, weights sum to one, long-only, target volatility achieved |
| LN2 | CAPM, beta, tracking error, information ratio | Diagnostics and comparison with 60/40 | TE calculated on active returns; IR correctly annualized |
| LN3 | Instability, shrinkage, constraints, turnover, costs | Ledoit-Wolf, bounds, net backtest | Compare sample/LW; measure stability and turnover |
| LN4 | Reverse optimization and Black-Litterman | Connected Portfolio | Document `x0`, `phi`, `P`, `Q`, `Omega`, `tau`; BL without views = prior |
| LN5 | Risk contributions, Euler, ERC, log barrier | Balanced Portfolio | Sum of RC = volatility; equal relative RC; rescaling |
| LN6 | Risk budgeting, coherent measures, concentration, diversification | Risk budget, Expected Shortfall, Herfindahl/Shannon | Do not confuse VaR and ES; test decompositions |
| LN7 | StockTwits, classification, polarity, event study, Mann-Whitney | Sentiment validation and BL views | Use the market-model abnormal component; timestamped signal, historical test, cost, no temporal leakage |

### QARM Rigor Requirements

- `phi` is risk aversion, and `gamma = 1 / phi` is tolerance in the gamma problem.
- The relationship `target volatility = Sharpe / phi` holds within the Tobin/CML framework with a tangency portfolio and a risk-free asset. In RiskMatch, it is an internal calibration assumption used to assign a risk band. The application displays the band and its reference volatility; the volatility actually obtained must then be recalculated after constraints and leverage capping.
- A BL portfolio anchored to ERC is not literally the market portfolio. The project must refer to a **neutral reference portfolio** and provide a sensitivity analysis using a 60/40 anchor or available market weights.
- The BL covariance and the view uncertainty matrix must be distinguished; if `omega` is constructed using standard deviations, they must be squared.
- StockTwits polarity becomes a return view only after prespecified historical validation.

## 2. Empirical Methods in Finance — Validity Controls

| Contribution | Selected use | Use excluded by default |
|---|---|---|
| Simple/log returns, total return, excess return | Simple returns for portfolio aggregation; log returns for diagnostics; adjusted prices | Mixing conventions within the same formula |
| Moments and stylized facts | Skewness, kurtosis, normality, autocorrelation, volatility clustering | Assuming normality without diagnostics |
| OLS/CAPM/factors | Alpha/beta with HAC robust errors, as diagnostics | Claiming alpha based on a simple naive t-statistic |
| Stationarity | Work with returns/changes; ADF/KPSS for macro levels where appropriate | Regression on non-stationary levels |
| GARCH/EWMA | Optional robustness check for target volatility | Adding GARCH before the rolling baseline works |
| Breaks and regimes | Stability across subperiods; HMM/Markov switching as a bonus | Using smoothed probabilities that contain future information |
| Transaction costs | Two-way turnover, spreads, 0/10/25 bps analysis | Gross performance as the primary result |
| Predictability | Walk-forward evaluation, historical benchmark, out-of-sample assessment | Searching for and then retaining the best model on the test set |

## 3. Advanced Data Analytics — Modeling Discipline

To be applied directly:

- simple baseline before a complex model;
- chronological train/validation/test split;
- walk-forward validation, never random k-fold validation for time series;
- regularization and the bias-variance trade-off;
- task-appropriate metrics;
- reproducibility, seed, configuration, and versioning;
- interpretability and error analysis.

Targeted optional contributions:

- PCA only as a diagnostic for redundancy among macro variables;
- GMM as a descriptive baseline before HMM;
- GPR as a research avenue for uncertainty, not as an MVP dependency.

Excluded from the MVP: deep learning, RNN/LSTM, trained Transformers, PINNs, and reinforcement learning. Their inclusion would increase overfitting risk and the burden of explanation without addressing a project requirement.

## 4. Finance, Regulation, Behavior, and ESG

| Course | Useful contribution | Safeguard |
|---|---|---|
| Regulation / suitability | Separate knowledge, capacity, tolerance, objectives, and constraints; retain a record of responses | Do not claim legal compliance without legal review |
| Behavioral finance | Neutral wording, controlled random order, mirror question, loss expressed as an amount and percentage | Avoid manipulative framing and false psychometric precision |
| ESG | Exclusions and preferences as explicit constraints | Do not turn an opaque ESG score into alpha; disclose data limitations and greenwashing risk |
| Macro/Fed analysis | Context, scenarios, and interpretation of regimes | Do not turn a macro narrative into a signal without out-of-sample testing |
| Geopolitics | Qualitative stress tests and limitations | No retrospective discretionary timing |
| Pension funds | Horizon, liquidity, risk budget, governance | Adapt to an individual client; do not copy an institutional mandate |
| Market analysis | Cycles, scenarios, communication | Narrative charts do not prove predictability |

## 5. Documents Not to Be Confused with the Project

The local file `cours  copie/literature.md` primarily describes another project based on equity anomalies, five signals, and volatility variants. It may provide general principles—costs, out-of-sample tests, multiplicity of trials—but must not be cited as a direct RiskMatch bibliography without verifying each reference.

## 6. Rule for Integrating a New Technique

A course technique is added only if the answers to all five of the following questions are positive:

1. Does it address a client need or an assessment criterion?
2. Do the available data permit an honest estimate?
3. Is there a simpler baseline to beat?
4. Can it be validated out of sample and explained in under one minute?
5. Can the team test and maintain it before the presentation?
