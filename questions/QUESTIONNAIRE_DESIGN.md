# Why RiskMatch asks each question

**Design record · 22 November 2026.** The course project interprets hypothetical financial choices using published research, explicit model assumptions and synthetic routes. The 60 cards are implemented in English. The project collects no participant data. See [checklist chapter 2](../CHECKLIST.md#2-profile-the-client).

The [card-by-card guide](GUIDE_DES_CARTES.md) lists the response meanings, numerical bounds, eligible follow-ups and worked funding scenarios for this version.

## Research behind the design

| Primary study | Finding or method we draw on | RiskMatch design decision and limit |
|---|---|---|
| [Falk et al., The Preference Survey Module](https://doi.org/10.1287/mnsc.2022.4455) | A short adaptive sequence changes a certain payment in response to a person's earlier choice. The instrument combines quantitative choices and a self-assessment and was evaluated against incentivized decisions. | Keep common anchors for comparison, then adapt a small number of offers. Our split between fixed anchors and adaptive probes, swipe interface and hypothetical investments require their own evaluation. |
| [Dohmen et al., Individual Risk Attitudes](https://doi.org/10.1111/j.1542-4774.2011.01015.x) | Self-reported willingness to take risks has behavioral relevance, and responses vary across domains. | Include one financial self-description as a qualitative cross-check. A mismatch can trigger clarification. A binary endorsement is a coarser measure than the original scale. |
| [Tversky and Kahneman, The Framing of Decisions and the Psychology of Choice](https://doi.org/10.1126/science.7455683) | Equivalent decision problems can elicit different preferences when their presentation changes. | Keep the initial stake, horizon, probabilities and final balances explicit. In paired scenarios, record every balance that changes. A single reversal supports several explanations. |

## Part A. Four short factual screens

1. **Goal.** Ask what the money is for, the date, its flexibility and the spending currency. A fixed payment date determines how long capital can remain exposed.
2. **Resources.** Collect capital, planned contributions and their reliability. Allow ranges and unknowns.
3. **Protected money.** Ask about withdrawals, due dates, emergency reserves and confirmed external funding. Asking whether an income interruption would require a withdrawal gives more direct evidence of capacity than inferring it from an occupation.
4. **Expectations and constraints.** Separate desired return, strict exclusions and softer preferences. Calculate the goal-funding return separately when amounts and dates permit it.

These screens determine capacity and eligibility. Reserve the quantitative tolerance estimate for understood choices with explicit alternatives.

## Part B. Common core and adaptive branches

The bank contains **60 profile scenarios**, including **15 common scenarios**. The route stops after at most 25 active answers. The original 5–10 minute target is unmeasured. One scenario may need more than one gesture. Record both counts. Right always means yes, left means no, and pass records uncertainty. Each screen presents one statement.

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

Both balances are visible and the statement asks for a preference between them. “I would accept this investment” could be true of both placements. The common core also presents CHF 1,000 and CHF 1,040 against the same gamble. Adaptive probes can then narrow the remaining interval. Passing leaves the comparison unanswered. When testing acquiescence, balance versions that endorse the certain and uncertain options while keeping the gesture meanings fixed. Store the displayed wording and the underlying choice separately.

**Scoring check for authors.** Under the project's one-year mean–variance approximation, the risky returns here are −0.10 and +0.20, with mean 0.05 and variance 0.0225. The guaranteed return is 0.02. Equality occurs at φ = 2 × (0.05 − 0.02) / 0.0225 ≈ 2.67. Choosing the guarantee supplies a provisional lower bound under this model. Choosing the gamble supplies an upper bound. The unit is a decimal return on the stated stake. This example demonstrates a calculation. The threshold describes the trade-off in this one scenario. Actual choice stability is unknown.

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

**What the interval means.** A range supplied by the client describes their estimate. A bracket inferred from choices describes values compatible with the stated model. A statistical confidence interval requires a specified estimator, assumptions about response error and evidence about coverage. Keep those meanings explicit. The project reports compatible values and sensitivity to omitting an answer. It supplies no individual confidence probability.

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
| Validation and revision | Expected interpretation, competing explanation, synthetic check and revision decision. |

## Client review and corrections

Describe the tolerance band as conditional on the one-year model and the hypothetical choices. If a swipe reveals an overlooked withdrawal, ask the client to confirm the factual change before updating the dated reserve. A pure change in willingness to take risk can change sleeve preferences while leaving the funding calculation intact. The one-year card constrains an interpretation at that horizon. Explain any transfer to another horizon explicitly. Document the ambiguity each follow-up can resolve. Actual response time and predictive value for investors are unknown.

## How to interpret hypothetical answers in the report

The following questions refer to the shipped card IDs. The answers are invented examples. A response describes what someone says they would do under the stated conditions. Whether they would do it with their own money is unknown.

| Question and card | Hypothetical response and possible behavior | Other explanation or clarifying question | What RiskMatch may do |
|---|---|---|---|
| **Understanding · C01, P01.** If an investment can end at CHF 900 or CHF 1,200, is CHF 900 the smallest possible balance? | A wrong answer could mean the payoff description was misunderstood. | The person could also have swiped in the wrong direction. Explain the answer and try the second example, whose statement has the opposite polarity. | Leave tolerance undetermined if practice remains unresolved. |
| **Stated comfort · C02, B18.** Thinking about money you can leave invested for a year, do you feel comfortable taking financial risk? | Someone might say yes and still consistently prefer a guaranteed balance on the concrete cards. | “Comfortable” can depend on the goal or size of the potential loss. B18 asks about dependence on the goal after a pass. Dohmen et al. motivate distinguishing general willingness from domain-specific choices. | Retain the declaration as context. Only understood numerical trade-offs bound the model parameter. |
| **Certainty · C03–C07, T01–T20, B15.** With CHF 1,000 for one year, would you choose CHF 1,020 guaranteed over a 50/50 chance of CHF 900 or CHF 1,200? | Taking CHF 1,020 despite the gamble's CHF 1,050 average is compatible with valuing stability at this stake. | Near-indifference, misunderstanding the probabilities or a different utility model could explain it. Compare choices across guaranteed offers. B15 allows a qualitative statement of indifference on sensitive routes. Falk et al. motivate varying the certain amount. | After successful practice C03 gives a lower bound of about 2.67 for a guarantee, an upper bound for the gamble and no bound for a pass. Conflicting bounds leave the ranking unresolved. |
| **Starting balance · C08/C10, C09/C11, B14.** Starting with CHF 1,000, would you take CHF 1,080 guaranteed over an equal chance of CHF 1,000 or CHF 1,200? What if each final balance were CHF 100 lower? | Choosing the gamble first and the guarantee second, then switching the same way in the second pair, could indicate that finishing below CHF 1,000 matters. | Lowering all balances also changes final wealth. Tversky and Kahneman motivate checking how a decision is presented. These pairs change payoffs as well. B14 asks whether crossing the starting amount mattered. | Record the repeated switch and, separately, any confirmation. Neither supplies a loss-aversion coefficient or changes the numerical interval. |
| **Sale after a fall · C12, C13, B01–B08, B16–B17, B21–B23.** After a 15% drop with eight years left, would you sell some today? | Selling could protect cash for a near-term bill, express discomfort with fluctuations, or reflect an expectation of further losses. Several reasons can coexist. | Ask about a payment within twelve months (B01), preference for smaller fluctuations with expenses covered (B02), and expected further losses (B03). C13 varies both decline and context, so differences cannot isolate one cause. A pass leaves the reason open. | A cash need opens the payments review. Only confirmed changes to the factual schedule alter the reserve. Record discomfort and outlook separately. The sale adds no numerical bound or trade order. |
| **Goal flexibility · C14, B09–B11, B19, B24.** If the savings plan may fall short, could you move the goal date later? | A yes makes postponement a possible adjustment. A no may reflect a fixed payment date. | With a fixed date, could the target fall or contributions rise? Someone unsure may need to check the date. Willingness to save more establishes no amount or funding source. | Identify the scenario to discuss. Retain the original dated mandate until the person changes the facts. |
| **Monitoring · C15, B12, B13, B20.** If the portfolio drifts from its chosen allocation, would you want a notification? | A yes suggests a preference for a drift alert. | Someone who declines immediate alerts might prefer a scheduled review. Someone unsure might want an example first. | Record the communication preference. An alert request supplies no authority to trade and no information about the tolerance bound. |

**Example for the report.** Two fictional clients both select “sell” on C12. One endorses B01 because tuition is due this year. The other endorses B03 because they expect the decline to continue. The first answer justifies checking the amount and due date. The second records an expectation about the market. Giving both people a lower tolerance score would erase the distinction the follow-ups were designed to reveal. Notebook 2.3.2 replays both cases and a third one involving discomfort.

The published studies motivate the questions. Their results belong to their own instruments and populations. For RiskMatch, the evidence consists of the card wording, its stated interpretation and reproducible software behavior. Real-world prevalence, completion time and predictive accuracy remain unknown.

## Implemented interview · version 2.2.0

The [card bank](profile_v1.json) contains 15 shared scenarios, one remedial practice scenario, 20 numerical probes and 24 conditional follow-ups. Each item records the exact statement, response interpretation, authorized scoring effect, ambiguity and review prompt. Monetary choices use a hypothetical CHF stake for one year, independently of the client's actual spending currency. Every loss comparison uses equal probabilities. Within each pair, the certain and uncertain balances shift together, changing their relationship to the initial stake and the level of wealth. Interpret repeated switches descriptively and request confirmation.

The common route interleaves both loss pairs and all five common trade-offs. A missed or passed first practice gets feedback and a second example with reversed statement polarity. An unresolved second practice closes the interview. Once the core is complete, the router checks liquidity, explanations for selling, matched-pair responses and choice sensitivity. At most two additional numerical offers can narrow the active interval across the illustrative decision boundary. Twenty session forms vary their ordering; each form is chosen independently of the answers and kept on replay. Each answer records the eligible pool, selected card, form, statement, gesture mapping and revision. Each route ends by 25 active answers. Correcting an earlier answer archives the superseded suffix and reopens the dependent questions.

The profile displays the full-data interval and the alternative interpretations obtained by omitting each scored response. The two hypothetical sleeve examples are tied at φ = 2. These examples demonstrate sensitivity pending catalogue evaluation. A liquidity observation opens the factual payment review. Only the client's edits there change the reserve. The project makes no empirical claim about wording comprehension, duration or individual calibration.

Run `python tests/test_interview.py` with the app dependencies. For the optional browser replay, start the app, install Playwright and its Chromium browser, then run `python tests/browser_interview.py`. Set RISK_MATCH_URL for a different app port or CHROME_PATH to use a local Chrome executable.
