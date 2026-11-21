# RiskMatch client profile

The questionnaire prepares a portfolio comparison for one financial goal. The client can review and correct the estimated risk tolerance, the risk their project can absorb, constraints and monitoring preferences before selecting an allocation. This is [Phase 1 of the implementation checklist](CHECKLIST.md#phase-1--understand-the-client).

## Factual intake

Use four screens before the card bank. Accept ranges, open goals and “I don’t know.”

1. What are you saving for, in which currency and by when? Record initial capital, planned contributions and any target amount. Separate the desired return from the return required to fund the target.
2. How much must be available, and from what date? Record planned withdrawals and how flexible the deadline is.
3. If income fell, how much of this investment would the household need for essential expenses? Consider available reserves, obligations and exposure to the employer.
4. Which activities must the portfolio exclude, and what would you prefer it to favor? Distinguish binding exclusions from preferences. State whether the available holdings data can verify an exclusion.

The versioned bank records wording, response options, triggers and theoretical indifference thresholds. Category boundaries and routing still require pilot validation. [English card bank](questions/bank.json)

## Card bank

Review the [swipe statements and routing tables](questions/CARD_REVIEW.md) by category. The team is reviewing the current bank before scheduling the participant pilot.

| Family | Bank | Common core | Use of variants |
|---|---:|---:|---|
| Comprehension | 2 | 1 | Rephrase the exercise after difficulty |
| Return–risk trade-offs | 20 | 8 | Narrow a boundary or check a choice at a different stake |
| Loss sensitivity | 14 | 4 | Start with two common pairs, then examine the effect of falling below the initial stake |
| Response to a decline | 10 | 2 | Clarify the reason for an investment decision |
| Financial circumstances and constraints | 8 | 0 | Clarify a need identified during intake or by a response |
| Monitoring preferences | 6 | 0 | Select one closing card suited to the route |
| **Total** | **60** | **15** | **45 conditional cards** |

The pilot targets roughly 20–25 cards on a typical route. A clear profile may finish after the common core and a closing card. Measure time and number of gestures separately. One scenario can require several gestures.

## Routing

- Prewrite each card and its transitions. Record its ID, version, family, common or conditional status, text, responses, trigger, information sought and effect on the profile. A response can trigger a card in another family.
- Present alternatives over the same horizon. State the initial stake, probabilities and final amounts. Show one first-person statement at a time. Right agrees and left disagrees on every card. Where several reasons are possible, a decline can open a different statement. Only an endorsed reason is recorded. Passing a trade-off opens an optional indifference check, with a further comprehension check if needed. The client can pass either clarification or go back.
- Cover the common core. Offer a second practice card if the first is unclear. If difficulty persists, return the factual profile and mark risk tolerance undetermined.
- After the core, show an unseen card only if it can distinguish categories, explain a discrepancy or clarify a constraint. After two unsuccessful probes on one issue, retain the uncertainty and move on. Finish with one monitoring card.
- For example, if a client would reduce exposure after a 15% decline, ask why. A near-term withdrawal triggers a question on the amount and date. Discomfort with an unchanged horizon triggers a smaller-decline scenario. A request for an explanation triggers a question about what the client wants to know before deciding.

## Scoring and client review

Only understood return–risk trade-offs inform risk aversion φ. For alternatives over the same horizon, compare mean–variance utility using **U(P) = E[R] − φ Var(R)/2**. Each preference constrains a range of φ. Treat indifference as a choice close to the threshold. An uncomprehended choice carries no score. Calibrate four tolerance bands (low, moderate, high and very high) during the pilot. Allow adjacent bands or insufficient evidence.

Assess loss-bearing capacity and compatible portfolio risk separately using the project’s withdrawal and liquidity constraints. An ambitious target opens a discussion about contributions, timing or the target amount. Occupation, age, household obligations, ethical exclusions and preferred review frequency do not score risk aversion.

Report at most two behavioral observations. Each needs a repeated pattern in two separate comparisons and the client’s confirmation of the interpretation. Test this rule in the pilot. Show which answers explain the result and allow corrections. Retain the requested monitoring preference. At a review, first ask what has changed in the goal, income, withdrawal plan or the client’s experience.

## Validation

Check the card counts by family and status, reachability of variants, common-core coverage on completed routes, termination and handling of unresolved ambiguity. Test corrections and independence between tolerance, capacity and behavioral observations. Compare core-only and adaptive routes for comprehension, one-week classification stability, information gained from each probe and observed duration. Psychometric thresholds and predictive performance remain to be established.

Before a participant answers, draw two of the twelve conditional trade-offs using a recorded rule and seed. Exclude both from routing and scoring. Freeze each predicted choice before presenting the held-out cards. Record “undetermined” when the estimated range crosses the item threshold. Report prediction coverage and agreement with participant-level uncertainty. Compare against the most common choice learned on a separate group. When participants choose between two portfolios, collect the reason in their own words. A preference driven by cost or a withdrawal date informs the mandate.

Local course references cover investment policy and biases, decisions under uncertainty, and household circumstances. [Portfolio management](<Theory/CFA/Portfolio-Management-explications copie.md>) · [Decision-making under uncertainty](<Theory/Methodology/Chapter_Guides_00-34/Guide_Ultime_Chapitre_16.md>) · [Household finance](<Theory/Methodology/Chapter_Guides_00-34/Guide_Ultime_Chapitre_34.md>)

### Transfer pilot and measurement bias

Ten of the twelve conditional trade-offs repeat the same lottery with a different certain payout. Held-out items from that family primarily test threshold consistency. In the pilot, also use the independent transfer items after freezing the profile and before giving feedback. Show two items with different probabilities and payoff ranges using a balanced rotation set before recruitment. Exclude these responses from scoring and routing. If a participant is unsure, rephrase the probability of loss or the amount available at maturity. Allow them to skip. [Transfer items](questions/transfer_validation.json)

For each participant and card family, record order, statement polarity, frozen prediction, abstentions, choice, comprehension, abandonment and duration. Compare coverage and agreement with a benchmark learned from other participants. Resample whole participants for intervals. Counterbalance the favored outcome and the sequence. Invite volunteers to repeat after a week and describe who misses the retest. Compare the core and full routes within participants. Report an inconclusive result for rarely visited branches. The notebook’s φ values and 12% risk cap are demonstration parameters.


## Implemented routing and funding rules

The web app records the direction and statement number of each gesture. It maps an endorsed or declined financial proposition to the canonical certain or uncertain outcome. Consecutive assigned pilot numbers see statements favoring opposite outcomes for each financial item and alternate two common-card sequences. Correcting a card collects that answer and its successors again. Editing factual inputs keeps the longest answer prefix still valid under the new mandate. Either change invalidates a previous confirmation. A saved file is validated and replayed from its initial facts and ordered events.

Pilot indifference allows ±10% around a card’s theoretical threshold. At least two understood trade-offs and a consistent interval are required to show tolerance bands. The provisional φ cut points are 2, 5 and 10. Lower φ means greater tolerance. Intervals can span multiple bands or have no finite upper bound. After the common cards, at most two unused financial probes can narrow an open endpoint or distinguish bands. Conflicting inequalities remain visible at review for correction. A hypothetical reaction to a loss cannot establish an actual household liability.

For ranges, use the lower starting capital, horizon, contributions, outside funding and agreed volatility ceiling, and the higher obligations and target. Protect the household reserve plus the withdrawal remaining after outside cash and dedicated savings expected by the earliest withdrawal date. Keep growth contributions separate. If reserve funding exceeds capital, report the shortfall and zero available growth capital. A hard exclusion stays flagged until holdings coverage can verify it. The required return uses the growth sleeve, end-of-month growth contributions and the growth target after reserves. A missing input can leave an amount or rate undetermined. Forecasting and portfolio matching require subsequent work.

## Running the pilot

1. Register pseudonymous participant IDs, recruitment criteria, invitation count and the baseline/evaluation split before collecting responses. Assign consecutive pilot numbers across participants. Use a fresh tab for each visit. Select the four validation cards on the fourth intake screen. Keep a separate private record of visit dates. Avoid identifying details in goal descriptions.
2. The interview freezes predictions for two reserved bank items and two transfer items before showing them. All four are excluded from the adaptive score. Binary answers, indifference, skips and incomprehension remain distinct in the event log. Card-response time includes time spent on repeated and validation cards. Measure total visit time separately, including intake, reading and breaks. A saved draft can be resumed. Record a missing export separately from an explicit early exit.
3. After review, download the profile locally. A correction after feedback invalidates the original confirmation and excludes the revised route from the independent prediction check. Retest volunteers after seven days under the same mandate. Keep missing visits, changed mandates and off-schedule retests in the denominators reported for follow-up.
4. Use `riskmatch.pilot.evaluate(records)` with one row per invited person. Each row has `id`, prespecified `split` (baseline or evaluation), `first` and optional `retest` Interview objects restored from local exports. Use `None` for missing visits. Supply ISO `first_date` and `retest_date` for a dated retest. Store identifiable records outside the repository. No participant records are supplied.
5. Report held-out bank and transfer results separately. Coverage is the fraction of planned items receiving a prediction. Agreement uses predicted items with a binary response. Compare core-only and adaptive scoring on the same participants. For the benchmark, learn each item’s most frequent binary answer only from baseline participants. Unseen items and ties produce no prediction. On mutually comparable items, resample whole evaluation participants for the paired accuracy difference. Report the number of people and treat small groups as inconclusive. Monitor branch counts, missed visits, response time and seven-day band transitions before revising the thresholds.

The regression suite can be run with `python -m pytest tests/test_client_profile.py` after installing pytest. The optional browser suite uses Playwright Chromium. Set `RISKMATCH_APP_URL` to the running local web app and, if needed, `RISKMATCH_CHROME` to the installed browser executable. Run `python -m pytest tests`. The browser suite exercises mobile touch, keyboard input, validation, confirmation, download and restore.
