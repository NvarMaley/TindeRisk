# Quantitative and econometric methods of the V2 library

The updated fact sheets include the supplementary ECB exchange rates, individual sensitivities to WTI and rates, three crises and comparison of volatility forecasts. [Econometric results](reports/econometrie/README.md)


The actual measurements as at 23 November 2026, their units and the missing data by class are shown in [catalogue matrix](reports/04-catalogue/METHODS.md).

American investment universe, customer performance in CHF. The methods apply according to the active class, historical depth and question asked. The candidate models are subjected to a chronological test. The sheet systematically indicates the method, dates, currency, frequency, strength and limits. The [implementation plan](CHECKLIST.md) sets the order of business.

## 1. Core measures for each eligible instrument

| Tool | Application and control | Course notes |
|---|---|---|
| Simple and logarithmic returns, distributions, currency conversion | Build the total return in USD and CHF with dividends, coupons or security events. Use simple return for portfolio and capitalization for wealth. Check an example of handflow. | EMiF 1 · Guide 01 |
| Average, compound return, variance and volatility | Windows 1/3/5/10 years depending on the coverage. Show frequency and strength. Compare estimates to multiple frequencies if autocorrelation makes daily annualization fragile. | EMiF 1–2 · Guide 01 |
| Asymmetry, Excess Kurtosis, Quantiles and Chart Q–Q | Identify thick tails, asymmetries and price errors. A normal law can serve as a benchmark. Verify sensitivity to extreme observations. | EMiF 2, 10 · Guide 05 |
| Maximum reduction, recovery time, Expected Historical Shortfall | Describe the highest drop from a top, duration to return to the top and average loss in the chosen tail. Publish the tail force. Mark an unfinished recovery at the cut-off date. | Guide 05, §5.3 · EMiF 2 and 13 |
| Pearson and Spearman correlations, covariance and mobile correlations | Work on comparable dates. Calculate an overall measurement and then slippery windows and stress states. Document the cover and do not equate an absent price with a zero return. | EMiF 2 and 11 · QARM2 LN3 |
| Volume, spread, participation, costs and trading dates | Assess whether a position of the proposed size is negotiable. Play at least one case of fee and execution. A bond investment sleeve takes into account batches and settlement dates. | Guide 06 · Notes on transaction costs |
| Contribution to risk, concentration and overlap | For each portfolio, bring together capital weight, concentration per issuer and contribution to volatility. Aggregate indirect positions of ETF when data are available. | QARM2 LN5–LN6 · EMiF 11 |

**Python tools planned.** NumPy and pandas for calculations, PyArrow for historical and SciPy for statistics. The sheet also sets out the missing data and the date of eligibility.

## 2. Econometrics and tools by class

| Tool | Where we use it and what it delivers | Course notes |
|---|---|---|
| CAPM, beta and alpha regression | First reading of shares and equity funds. To estimate sensitivity to a reference market and report uncertainty. Estimate U.S. factors in USD with a consistent risk-free rate. Measure separately the exchange exposure for the customer CHF. | QARM2 LN2 · EMiF 3 and 8 · factor model Guide |
| Fama–French and momentum | Test for additional stock exposures. Start with the market, compare 3 then 5 factors, test the momentum according to the question. Publish coefficients, intervals, residues and stability between windows. | Notes on factor models · QARM2 LN2 · [Official data Kenneth French](https://mba.tuck.dartmouth.edu/pages/faculty/Ken.french/data_library.html) |
| Multifactor OLS, HAC errors and block bootstrap | Quantify sensitivity to oil, dollar, rates and market. Retain factors and units by question. Compare several windows and leave contiguous blocks for uncertainty. Bring together, staff and potential instability. | EMiF 3 and 5–6 · Guides 05 and 12 |
| Events and stress studies | Compare the reaction before and after a dated shock and distinguish up/down. Test for example WTI +5 USD or rate +100 bp. Compare observed return and return for a predetermined reference. | Guide 01, case of dividend · Guides 05 and 12 |
| Diagnosis of time series | ACF and Ljung–Box for dependencies, ARCH-LM for conditional variance, ADF/KPSS if the stationarity hypothesis is determinant. Test residues before retaining a model. | EMiF 2, 4, 7 and 9 |
| Cash flow, full/clean price, maturity yield, duration, DV01, convexity | For fixed-rate bonds, calculate maturities and revalue the securities after a rate shock. For corporate credit, also test the spread. Compare theoretical sensitivity and complete reclamation. | Guides 03 and 11 · CFA Notes |
| Spot, curve, bearing and total return | For a raw material vehicle, document what comes from the underlying, fee and bearing when it applies. The WTI spot can be used as a factor even when no oil vehicle is eligible. | Guides 03 and 11 |
| Portfolio Sorts and Cut Regressions | Test action signals, e.g. momentum or asset growth. Classify titles with the information then available and compare subsequent group returns. Check turnover, costs, exits and sector impact. | Notes on tris and the assembly growth · Notes on aggregate predictability |

**Python tools planned.** statsmodels for regressions and diagnostics, NumPy/SciPy for resampling and recovery. [Statsmodel Documentation](https://www.statsmodels.org/stable/index.html)

## 3. Methods to be tested once the base has been checked

| Question | Approaches to be compared and expected evidence | Course notes |
|---|---|---|
| **What volatility do you expect?** | Mobile historical volatility and EWMA as references, then GARCH(1.1), Student innovations or asymmetric model if the residues and data warrant. Compare chronologically to 21 then 63 sessions depending on coverage, with QLIKE and variance error. | EMiF 9–10 and 13 |
| **How to estimate the risk of a great universe?** | Empirical covariance as reference, Ledoit–Wolf to stabilize, then factor covariance if necessary. Test DCC-GARCH on a small representative group if correlations move significantly. Compare weight stability and off-sampling volatility. | QARM2 LN3 · EMiF 11 |
| **Is diversification in crisis?** | Start with moving correlations and betas, then test Chow for a specified date or Markov breakages/regimes if the sample is sufficient. In anticipation of using the filtered probabilities that can be calculated at the decision date. | EMiF 11–13 |
| **What's the trajectory after a shock?** | Test a parsimonious RAV with impulse responses on a few aggregate variables. Document the identification of the impact and sensitivity to the order of variables. Reserve VECM to the relationships between levels with plausible and tested co-integration. | EMiF 5–7 · Guide 12 |
| **What signals improve the expected performance?** | Average stabilized as reference. Test regularized regressions, macro predictors and sentiment. An encrypted and validated view can enter Black–Litterman with its uncertainty. Also monitor the net effect of costs on decisions. | QARM2 LN3–LN4 and LN7 · Guide 19 · Advanced Data Analytics 4 |
| **Are there any redundant exhibits?** | PCA or clustering on a common universe to detect candidate concentrations. Then check with economic positions, factors and exposures. | Advanced Data Analytics 11–12 |
| **How to compare the risk of allocations?** | Minimum volatility, mean–variance under ceiling, contributions from Euler and comparison ERC or risk parity. Check net returns, extreme losses and concentration under the same mandate. | QARM2 LN1, LN3, LN5–LN6 · EMiF 11 |

**Python tools planned.** `arch` for GARCH and bootstrap by blocks, statsmodels for VAR and some diet models, scikit-learn for Ledoit–Wolf, Ridge, PCA and clustering, CVXPY/CLARABEL for allocations. The [checklist](CHECKLIST.md) also describes the overheating work, time tests and display conditions of a probability. [Documentation arch](https://arch.readthedocs.io/en/latest/)

## 4. Signal interpretation and evidence-based weighting

1. **Show the message of each signal.** Show family, date, raw measure, horizon, meaning, intensity and validation status. The VIX is a market signal, the rate curve a macro signal, the momentum a quantitative signal and messages a sentiment signal. An indicator may be relevant for several targets. Each test keeps its own line and decision.
2. **Compare only signals that answer the same question.** For example, for the portfolio variance over 21 sessions, express the meaning and intensity of each signal allowed on a common scale fixed from training. A negative score suggests a lower risk than the reference and a positive score a higher risk. The following month's return and the risk of a client's deficit keep their own opinions.
3. **Estimate the weight with results, then freeze it.** Start with a combination of equal weights of the permitted signals. Then test for normalized positive weights based on predictive gain and stability in validation windows. Reduce the weight of redundant information or retain a single series if the second signal does not contribute to the forecast. Keep the final block to judge the combination against the reference and the best signal alone. An exploratory signal remains visible with zero weight.
4. **Display the synthesis and its limitations.** For each notice, publish individual signal directions, effective weights, contribution of each line, coverage and disagreement. If data is missing, apply the predefined fold rule and display the change. If coverage or validation is insufficient, keep reference and indicate that the evidence is insufficient. The score expresses a sense and intensity. A probability requires a defined event and a separate calibration control.

**Historical landmarks.** V1 has already tested stabilized covariance, conditional volatility, rate curve, SPY distributions, equity styles, sentiment and a rebalancing rule. These results shed light on the first models to compare. Admission to V2 depends on the universe, target, horizon and new validations. [Studies V1](https://github.com/NvarMaley/TindeRisk/blob/c3a1fdb/research/robustness/README.md) · [Tracking the V1 sentiment](https://github.com/NvarMaley/TindeRisk/blob/c3a1fdb/research/sentiment_followup/README.md)

## Expected output

Each instrument profile answers four questions. How did it perform in USD and CHF? How much risk did it carry? How did it respond during past shocks? What is the quality of the estimate on the date of the mandate? The portfolio statement adds the contribution of each line, common risks, scenario results and fees. The notes cited can be found in local QARM2, EMiF, Advanced Data Analytics, CFA and numbered methodological guides.

## Methods implemented on the complete universe

As of October 30, 2026, the multi-asset study submitted 3,322 securities, including 3,255 individual stocks, 54 direct Treasuries and 13 ETFs. Previous comparisons of 13 ETFs are used as a control. The catalogue measures returns in CHF, full prices and coupons for Treasury securities, and covariance between series on common dates. The border uses a factor model on the simultaneous universe. The replay holes retain a pattern. [Data and calculations](reports/univers-complet/README.md)

Section 12 applied this rule to 52 model–target–horizon combinations. The dated registry keeps all tested signals visible with zero recommendation weight. [Forecasts and funded tests](reports/12-forecasts/README.md)
