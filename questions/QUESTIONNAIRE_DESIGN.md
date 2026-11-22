# Why RiskMatch asks each question

**Design record · 22 November 2026 · pre-pilot.** Use this document to write the English card bank and explain the questionnaire in the project report. It records the team's intended design. The counts, duration target, thresholds and routing choices need participant evidence. Implementation and validation tasks are in [checklist chapter 2](../CHECKLIST.md#2-profile-the-client).

## Research behind the design

| Primary study | Finding or method we draw on | RiskMatch design decision and limit |
|---|---|---|
| [Falk et al., The Preference Survey Module](https://doi.org/10.1287/mnsc.2022.4455) | A short adaptive sequence changes a certain payment in response to a person's earlier choice. The instrument combines quantitative choices and a self-assessment and was evaluated against incentivized decisions. | Keep common anchors for comparison, then adapt a small number of offers. Our split between fixed anchors and adaptive probes, swipe interface and hypothetical investments require their own evaluation. |
| [Dohmen et al., Individual Risk Attitudes](https://doi.org/10.1111/j.1542-4774.2011.01015.x) | Self-reported willingness to take risks has behavioral relevance, and responses vary across domains. | Include one financial self-description as a qualitative cross-check. A mismatch can trigger clarification. A binary endorsement is a coarser measure than the original scale. |
| [Tversky and Kahneman, The Framing of Decisions and the Psychology of Choice](https://doi.org/10.1126/science.7455683) | Equivalent decision problems can elicit different preferences when their presentation changes. | Keep the initial stake, horizon, probabilities and final balances explicit. In pilot comparisons change the intended feature deliberately and record what else differs. A single reversal supports several explanations. |

## Part A. Four short factual screens

1. **Goal.** Ask what the money is for, the date, its flexibility and the spending currency. A fixed payment date determines how long capital can remain exposed.
2. **Resources.** Collect capital, planned contributions and their reliability. Allow ranges and unknowns.
3. **Protected money.** Ask about withdrawals, due dates, emergency reserves and confirmed external funding. Asking whether an income interruption would require a withdrawal gives more direct evidence of capacity than inferring it from an occupation.
4. **Expectations and constraints.** Separate desired return, strict exclusions and softer preferences. Calculate the goal-funding return separately when amounts and dates permit it.

These screens determine capacity and eligibility. Reserve the quantitative tolerance estimate for understood choices with explicit alternatives.

## Part B. Common core and adaptive branches

Plan a bank of **60 profile scenarios**, including **15 common scenarios**. Target about **20–25 scenarios in 5–10 minutes** for a typical completed route. One scenario may need more than one gesture. Record both counts. Right always means yes, left means no, and pass records uncertainty. Each screen presents one statement.

| Core family | Count | Question for the researcher | Permitted use |
|---|---:|---|---|
| Comprehension | 1 | Can the participant identify the lowest possible ending balance? | Explain a mistake and offer a second practice item. Continued difficulty leaves tolerance unresolved. |
| Declared financial tolerance | 1 | How does the person describe their willingness to take financial risk? | Compare with concrete choices and clarify discrepancies. |
| Security versus uncertainty | 5 | What certain payments would the person take in place of specified uncertain outcomes? | Common anchors for the quantitative aversion interval. |
| Sensitivity to falling below the initial stake | 4 | Does preference change repeatedly in two matched pairs when an outcome crosses the starting balance? | Describe the observed pattern and ask the participant to confirm its interpretation. |
| Reaction to a decline | 2 | What action would the participant consider after a stated fall at a stated horizon? | Trigger follow-ups on liquidity, discomfort or market expectations. |
| Goal flexibility | 1 | Which goal condition can change if funding is insufficient? | Explore the date, target or contributions. |
| Monitoring preference | 1 | Which event warrants a notification or review? | Tailor follow-up. |

For a completed route, use the common core to anchor comparisons. Reserve up to two additional risk probes when a feasible answer could narrow an open interval or resolve a relevant band boundary. Use other branches when they could correct a funding assumption or clarify the meaning of an action. Stop when further answers would leave the decision unchanged. A participant may stop early or pass without acquiring a risk label.

## Worked choice and routing example

> You have CHF 1,000 to invest for one year. Placement A pays CHF 1,020 for certain. Placement B gives you an equal chance of CHF 900 or CHF 1,200.  
> **Between these two, I choose the guaranteed payment.**  
> Left · No  Right · Yes  Pass · Unsure

Both balances are visible and the statement asks for a preference between them. “I would accept this investment” could be true of both placements. A yes can lead to a later CHF 1,000 guaranteed offer against the identical gamble. A no can lead to CHF 1,040 guaranteed. Passing leaves the comparison unanswered. When testing acquiescence, balance versions that endorse the certain and uncertain options while keeping the gesture meanings fixed. Store the displayed wording and the underlying choice separately.

**Scoring check for authors.** Under the project's one-year mean–variance approximation, the risky returns here are −0.10 and +0.20, with mean 0.05 and variance 0.0225. The guaranteed return is 0.02. Equality occurs at φ = 2 × (0.05 − 0.02) / 0.0225 ≈ 2.67. Choosing the guarantee supplies a provisional lower bound under this model. Choosing the gamble supplies an upper bound. The unit is a decimal return on the stated stake. This example demonstrates a calculation. Pilot evidence must establish which thresholds are useful and how stable people's choices are.

## Worked behavioral branch

> Your investment has fallen 15% since you bought it. You planned to keep it for another eight years. **Today, I would sell some of it.**

A yes opens a clarification. Multiple explanations can be endorsed when each affects the decision.

| Follow-up statement | Interpretation if endorsed | Consequence |
|---|---|---|
| I will need some of this money within twelve months. | A cash need may be missing from the intake. | Revisit the withdrawal and reserve with the client. |
| Even with my upcoming expenses covered, I would prefer a more stable investment. | The decline changes the person's stated preference for stability. | Compare with the trade-off cards and discuss an exposure they could maintain. |
| I would sell because I expect this investment to fall further. | The answer expresses a market belief. | Record the belief separately from tolerance. |

A no on the initial card leaves the reason for holding open. A pass supplies no directional evidence. A sale alone contributes no points to the aversion estimate.

## When an answer is approximate or could be mistaken

Treat each swipe as an observation made in a particular scenario. Record the wording, offer and response, and allow correction. The person may be nearly indifferent, unsure of an amount, interpreting the horizon differently or simply moving the card by accident. Swipe speed alone cannot distinguish these explanations.

| What we observe | Clarification if it could change a decision | How the evidence enters the profile |
|---|---|---|
| “I may need CHF 10,000–15,000.” | Ask whether the upper amount must be available by the payment date. | Keep both endpoints. With CHF 50,000 and no other claims or funding, investable capital spans CHF 35,000–40,000. Identify allocations that remain feasible throughout that range. |
| Two close offers elicit different choices. | Check whether the switch is consistent with a preference threshold. If it already brackets the decision adequately, stop. If it crosses a relevant boundary, offer a closer comparison. | Keep the interval between compatible bounds. An ordinary switch can be informative. |
| A pass, conflicting answers or a borderline classification. | Offer a neutral, optional probe such as “Both alternatives would work equally well for me.” Allow the person to review the original scenario or correct a gesture. | A pass adds no directional bound. Record confirmed indifference qualitatively until a numeric tolerance for it has been calibrated. Retain unresolved alternatives after the probe limit. |

**Sensitivity check.** Recompute the plausible band and resulting options with each potentially decisive trade-off omitted in turn. If one answer alone changes the eligible options, mark the conclusion as sensitive and use a clarification only if it can help. Do not discard an inconvenient answer to obtain a preferred classification. When the remaining options are equally suitable across interpretations, stop asking and explain the common result. When interpretations still imply materially different allocations, show the uncertainty and defer the personal ranking.

**What the interval means.** A range supplied by the client describes their estimate. A bracket inferred from choices describes values compatible with the stated model. A statistical confidence interval requires a specified estimator, assumptions about response error and evidence about coverage. Keep those meanings explicit. Before attaching probabilities to an individual's band, evaluate response variability through retests and independent choices. Report sampling uncertainty for pilot metrics by resampling participants. Such intervals describe the pilot metric and do not confer an individual confidence level.

For every new card, document the ambiguous response it could produce, the decision that ambiguity could affect, one neutral clarification, and what remains unknown if it is passed.

## What the client receives

1. **A model-dependent tolerance interval.** Combine comparable, understood trade-offs. Show open bounds, contradictions or insufficient evidence explicitly. Band cutoffs remain provisional.
2. **Financial capacity.** Show reserve, investment horizon, dated withdrawals and unresolved funding gaps.
3. **Behavioral observations.** Use wording the client can verify, such as “In two comparisons, your choice changed when one outcome fell below your starting capital.” Invite correction.
4. **Evidence quality.** Report usable choices, comprehension issues, conflicts and interval width. A calibrated confidence percentage would require separate empirical evidence.

## Card authoring record

Complete one row per wording version before adding it to the bank. Keep the ID stable when logging a revision. Preserve prior wording for comparisons.

| Field | What the author records |
|---|---|
| ID, version and role | Core, branch, practice or held-out evaluation. Identify paired items. |
| Primary construct and rationale | The single question being investigated, relevant study and specific design assumption. |
| Exact display | Situation, horizon, amounts, probabilities, statement and gesture mapping. |
| Interpretation | Separate entries for yes, no and pass. Record at least one plausible competing explanation. |
| Routing and stopping | Eligibility, response that triggers the next item, maximum probes and exit condition. |
| Effect on profile | Bound, factual correction, descriptive observation, preference or no score. Show any threshold calculation. |
| Validation and revision | Expected comprehension, known framing risks, pilot metric, observed issue and revision decision. |

## Client review and corrections

Display the tolerance band as experimental until its human calibration has been evaluated. If a swipe reveals an overlooked withdrawal, ask the client to confirm the factual change before updating the dated reserve. A pure change in willingness to take risk can change sleeve preferences while leaving the funding calculation intact. The one-year card constrains an interpretation at that horizon. Explain any transfer to another horizon explicitly. Evaluate the extra predictive value and time of the probes separately from investment performance under a frozen mandate.

## How to justify the design in the report

Start by drafting the 15 core scenarios and three branches covering an uncertain risk boundary, a decline and a withdrawal contradiction. Test synthetic routes, corrected answers, response-side mapping and termination. For cognitive interviews, ask participants to explain in their own words what each option meant and why they swiped. A technically valid route can still contain a misunderstood item.

For the later human pilot, freeze the core and adaptive scoring rules and four held-out choices before displaying any result. Compare core-only and adaptive predictions on the same held-out choices within each participant. Record repeatability, time, comprehension, passes, abandonment, branch frequency and confirmed corrections to financial constraints. Participants reaching a branch are already selected by earlier responses. Treat branch comparisons accordingly.

In the report, trace each claim from **source → design choice → item ID/version → pilot observation → retain, revise or remove**. For example, the literature motivates adapting a certain offer. A pilot that improves held-out agreement would support our particular probe. Until such data exist, describe the probe and the planned comparison as a design hypothesis. Use the same distinction for the duration target, category boundaries and sensitivity to losses.


## Bias checks for interpreting the pilot

Record who was assigned, started, reached each branch, answered the held-out choices and returned at retest. Publish both prediction coverage and agreement conditional on a verifiable response. For example, 48 matches among 60 verified participants out of 100 assigned gives 80% observed agreement and 60% coverage. All-assigned agreement could range from 48% to 88% if the other 40 had been verified. These are missing-outcome bounds. Estimate sampling uncertainty separately at participant level.

Where every participant follows the same deterministic routing rule, the core-only versus adaptive comparison measures incremental predictive information within the observed routes. Estimating the effect of offering a probe requires a comparison group among equally eligible participants. For a pilot investigating that effect, randomize probe versus no probe within eligibility and log assignment probabilities. Examine wording polarity, comprehension, stake sensitivity and test–retest changes before treating tolerance bands as portable across contexts.

## Implemented interview · version 2.2.0

The [card bank](profile_v1.json) contains 15 shared scenarios, one remedial practice scenario, 20 numerical probes and 24 conditional follow-ups. Each item records the exact statement, response interpretation, authorized scoring effect, ambiguity and review prompt. Monetary choices use a hypothetical CHF stake for one year, independently of the client's actual spending currency. Every loss comparison uses equal probabilities. Within each pair, the certain and uncertain balances shift together, changing their relationship to the initial stake and the level of wealth. Interpret repeated switches descriptively and request confirmation.

The common route interleaves both loss pairs and all five common trade-offs. A missed or passed first practice gets feedback and a second example with reversed statement polarity. An unresolved second practice closes the interview. Once the core is complete, the router checks liquidity, explanations for selling, matched-pair responses and choice sensitivity. At most two additional numerical offers can narrow the active interval across the illustrative decision boundary. Twenty session forms vary their ordering; each form is chosen independently of the answers and kept on replay. Each answer records the eligible pool, selected card, form, statement, gesture mapping and revision. Each route ends by 25 active answers. Correcting an earlier answer archives the superseded suffix and reopens the dependent questions.

The profile displays the full-data interval and the alternative interpretations obtained by omitting each scored response. The two hypothetical sleeve examples are tied at φ = 2. These examples demonstrate sensitivity pending catalogue evaluation. A liquidity observation opens the factual payment review. Only the client's edits there change the reserve. The human wording review, timing, response-side pilot and individual calibration remain pending.

Run `python tests/test_interview.py` with the app dependencies. For the optional browser replay, start the app, install Playwright and its Chromium browser, then run `python tests/browser_interview.py`. Set RISK_MATCH_URL for a different app port or CHROME_PATH to use a local Chrome executable.
