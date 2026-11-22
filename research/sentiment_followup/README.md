# H06 follow-up · Do the messages improve a decision?

## Rules recorded before running the comparisons

The original classroom replay left only five fully observed signed-view months. Event polarity also helped define the supplied event labels. This follow-up uses raw daily counts of bullish and bearish messages and total activity for AAPL and SPY. It tests two distinct uses with one specification each. January 2018–February 2020 has already been inspected in H06. Use 2011–15 for development and 2016–17 for validation. Preserve both validation and historical results regardless of sign. The archived data have session dates and unverified publication times. A session's messages are assumed usable the following exchange session.

1. **Allocation.** Keep the 50/50 AAPL/SPY anchor, USD, month-end decision, next-session close trade, drifted holdings, missing-return handling, 2% annual tracking-error ceiling and 0/10/25 bp charges from H06. For each ticker pool its signed counts over the latest five completed sessions. Polarity is (bullish − bearish)/(bullish + bearish). Require all five rows and a positive count of classified messages for each ticker. Compare Apple polarity relative to SPY with the mean and standard deviation of the prior 63 sessions' five-session spreads (at least 50, ending before the latest five-session window). Clip the resulting z-score at ±2 and divide by two. Update the equilibrium AAPL-minus-SPY view by at most ±1% monthly, proportionally to that score. Set view error variance equal to its prior projection variance. This makes a neutral score give exactly the anchor. Use the anchor on unavailable inputs. Compare monthly net quadratic utility with the no-view anchor and report the old signed-event rule on the same months. The primary threshold remains 0.0005 per month at 10 bp.
2. **Risk.** Forecast the next session's squared AAPL-minus-SPY return separately. The reference uses the last 21 sessions' average squared spread return (at least 18 observed) and a multiplicative scale estimated on training data. The challenger adds the latest relative message activity, log(1+AAPL messages) minus log(1+SPY messages), normalized against the prior 63 sessions (at least 50), clipped to ±3. For return day t, use messages through t−2 and returns through t−1. Freeze both scale calibrations at each month-end using strictly earlier completed daily outcomes, with 252 matched training days minimum. Fit the reference and challenger on identical rows by minimizing log variance plus squared realized return divided by variance. Bound the activity slope between −1 and 1. On a missing signal use the reference. Report reference-minus-challenger loss, matched and fallback counts. The diagnostic economic threshold is 0.02 QLIKE, as in H02; no trade follows from this forecast.

Use three-month moving blocks on the original monthly calendar for interval estimates, with one- and six-month sensitivities. For risk, average paired daily improvements within month first. Require both a positive lower bound (one-sided 5% divided between the two endpoints) and the prespecified minimum. Report the two calendar splits separately. Neither test supplies independent confirmation or a verified live publication time. No tuning after inspecting these outcomes.

## Results

On the 20 scoreable months of January 2018–February 2020, the continuous signal was available on all 20. In the original event-based rule, only five scoreable months had a positive or negative event. Six of the 26 scheduled outcomes still lack complete returns. Calculations use identical months, missing-data handling and costs for all three arms.

| Mean monthly metric on those 20 months | 50/50 anchor | Original event view | Continuous view |
|---|---:|---:|---:|
| Net USD return at 10 bp per traded notional | 2.204% | 2.106% | 2.189% |
| Standard deviation of monthly net returns | 5.687% | 5.613% | 5.556% |
| Net quadratic utility (return − 2 × return²) | 0.014922 | 0.014183 | 0.015062 |
| Utility difference versus anchor × 10,000 | 0.00 | −7.39 | +1.40 |

The new view improved mean monthly net return by 0.083 percentage points versus the old view. Relative to the anchor, it earned 0.015 percentage points less per month and had lower dispersion. The small positive utility difference was below the predetermined threshold of 5 units on the ×10,000 scale. Its three-month block interval was −21.70 to +19.47 on that scale. Ten of the 20 months favored the new rule on utility. On the separate 2016–17 validation split the utility difference was −12.10 on the same scale (20 paired months). At 25 bp trading costs the historical gain was −0.50. Utility differences are score differences; the net returns are shown separately. [Monthly weights, returns and reference comparisons](results/allocation.parquet)

The activity-only risk forecast improved mean monthly QLIKE by 0.0078 during the historical replay (499 daily outcomes across 24 months, including four reference fallbacks). Its three-month block interval was −0.0239 to +0.0364. On validation it lost 0.0072 relative to the risk reference. The 0.02 threshold and the positive-bound rule both failed in the historical comparison. This test concerns day-ahead risk in AAPL relative to SPY and supplies no portfolio profit estimate. [Daily risk forecasts](results/daily_risk.parquet) · [Both periods and block sensitivities](results/comparison.csv)

**Decision.** Preserve the 50/50 no-view anchor and the reference risk forecast. Archive the continuous view as an exploratory candidate. A positive historical utility estimate on 20 months does not establish an investable edge. A future evaluation would need independently time-stamped message counts, decisions sealed before fills, and observations outside the inspected period.

## Reproduction

From the project root with Python 3.12 and the chapter 5 dependencies installed, run

```sh
python research/sentiment_followup/run.py
python tests/test_sentiment_followup.py
```

The build verifies the classroom fixture, prepared samples and chapter 5 comparison hashes. Tests cover the publication lag, missing counts, neutral views, variance calibration and chronological separation. [Release hashes](results/manifest.json)
