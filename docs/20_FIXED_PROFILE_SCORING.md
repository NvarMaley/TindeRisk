# Step 3.0c · Fixed profile scoring

The fixed questionnaire uses explicit academic calibration rules. The
scoring function accepts the fourteen question IDs and their choice IDs from
`questions/fixed_mvp.json`. Missing, unknown and contradictory selections
are rejected. The notebook shows each intermediate result.

## Financial capacity

Each capacity answer sets an annualized volatility ceiling. Take the
minimum of the four ceilings and keep every question that ties for the
minimum so the decision can be explained.

| Item | Answers listed in order | Ceilings in the same order |
| --- | --- | --- |
| F01 · Investment horizon | <2 years, 2–<5, 5–<10, ≥10, unsure | 5%, 8%, 12%, 15%, 4% |
| F02 · Withdrawals within two years | None, >0–<25%, 25–<50%, ≥50%, unsure | 15%, 10%, 6%, 4%, 4% |
| F03 · Cash buffer outside the investment | <1 month, 1–<3, 3–<6, ≥6, unsure | 4%, 6%, 10%, 15%, 4% |
| F04 · Loss that would impair a payment | <5%, 5–<10%, 10–<20%, ≥20%, no dependent payment, unsure | 3%, 5%, 9%, 12%, 15%, 4% |

These thresholds are design choices to review with users in 3.0e. Short
horizons, near-term withdrawals, thin cash buffers and fragile payment
commitments each tighten the ceiling. The 15% upper limit follows the top
displayed band. The 3% ceiling allows the result to flag a client whose
capacity falls below the range of the catalogue. The loss in F04 is a
constraint on the client's finances. A volatility ceiling cannot guarantee
that losses stay below that threshold.

## Risk tolerance

Normalize each tolerance answer to a point value between zero and one.

| Item | Choices in increasing tolerance order | Points |
| --- | --- | --- |
| F05 · Response to a 10% decline | Reduce risk, keep allocation, increase risk | 0, ½, 1 |
| F06 · Willingness to accept a temporary loss | <5%, 5–<10%, 10–<20%, ≥20% | 0, ⅓, ⅔, 1 |
| F07 · Risk/growth trade-off | Smaller swings, middle ground, larger swings | 0, ½, 1 |

Take the mean of all three points, count an explicit unsure as zero and
record it for clarification. With mean score s, the calibration uses
`risk_aversion = 7 − 4.5 × s` and `tolerance_volatility = reference_sharpe /
risk_aversion`. The endpoints place full low and high tolerance at the
5% and 14% catalogue references when the Sharpe assumption equals 0.35.
Equal item weights keep the score explainable. The intercept and slope
are calibration choices for this draft, without a psychometric estimate.

## Result and reference gate

Take the smaller of tolerance volatility and the capacity ceiling. Below
4% the result is outside the prepared categories. At 4% or above, use
the existing band boundaries. Clear a category reference for the risk
check only when it fits the effective limit and there is no unresolved
answer in F01–F07 or F12–F14. An unsure capacity answer uses 4% for the
provisional computation. Unsure responses on constraints prevent automatic
use of the reference even when the numerical risk check would pass.
The later eligibility check still has to enforce the recorded constraints.

F08–F11 provide explanation and goal context and do not change the score.
F12–F14 retain their roles as portfolio constraints. The shared serialized
profile and achieved portfolio volatility are covered by 3.0d and 3.8.

| Worked example | Tolerance | Capacity | Effective | Result |
| --- | ---: | ---: | ---: | --- |
| High tolerance, 2–<5-year horizon | 14% | 8% | 8% | Balanced, reference fits |
| High tolerance, upcoming withdrawal unknown | 14% | 4% | 4% | Conservative, clarify F02 before using a reference |
| High tolerance, loss below 5% threatens a payment | 14% | 3% | 3% | Below catalogue range |
