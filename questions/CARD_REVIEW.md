# Swipe questionnaire review

**Review copy · bank 1.1-swipe-en.** The app draws from 60 profile scenarios. The common core contains 15, including the first practice card. Four transfer scenarios belong to the optional research pilot. One scenario may take several swipes. This document covers the current implementation for team review. Participant testing is deferred.

| Read by category | What the answer can establish |
| --- | --- |
| [C · Comprehension](#comprehension) | Whether the person can identify the lowest possible balance in a practice example |
| [A · Risk and return](#risk-and-return) | A range for risk aversion φ under the one-year mean–variance model |
| [L · Loss comparisons](#loss-comparisons) | A repeated change of preference when a balance below the starting stake becomes possible |
| [B · Decisions after a decline](#decisions-after-a-decline) | The action or reason the person endorses |
| [F · Financial constraints](#financial-constraints) | Which funding assumptions, currency or exclusions need review |
| [S · Monitoring](#monitoring) | One preference about how or when the person wants updates |
| [V · Transfer checks](#transfer-checks) | Whether a frozen prediction agrees with an independent choice |

## How a route is built

Four factual screens establish the goal, planned withdrawals, household reserve and investment preferences before C1. **Right always means yes. Left always means no.** In the C, B, F and S tables, the numbered statements appear one at a time. Yes records the endorsed statement and ends the scenario. No advances to the next statement when one exists. Declining the last statement leaves the answer open unless the row gives an explicit opposite. Passing leaves the scenario open and moves on. A, L and V use the financial swipe rules below.

| Stage | Rule used by the app |
| --- | --- |
| 1 · Practice | C1 correct → common sequence. C1 incorrect or passed → explanation and C2. C2 incorrect or passed → factual review with tolerance undetermined. |
| 2 · Common sequence | Even assignment: A01 → L01 → B01 → A02 → L03 → A03 → B02 → A04 → L02 → A05 → A06 → L04 → A07 → A08.<br>Odd assignment: A08 → L03 → B02 → A07 → L01 → A06 → B01 → A05 → L04 → A04 → A03 → L02 → A02 → A01. |
| 3 · Risk probes | Before the interview, reserve two IDs from A09–A20. Among remaining unseen IDs, use at most two with thresholds strictly inside the current interval if it crosses a band boundary or has an open edge. Choose the threshold closest to the interval midpoint, or to the median candidate threshold if the upper bound is infinite. |
| 4 · Loss probes | If exactly one of the two core pairs shows the specified switch, ask one additional pair, selected by starting capital and assignment. The L table gives the exact rule. |
| 5 · Explanations and constraints | After the common sequence and probes, visit eligible B03–B10, then F01–F08, in ascending ID order. Multiple triggers can apply. A reason endorsed in B03 can activate a later card. |
| 6 · Close | Ask the first eligible S card in ID order. With the pilot off, go directly to profile review. The optional pilot presents four independent choices before revealing the report. |

**A branch to trace.** B01 asks whether to reduce exposure after a 15% fall. Yes makes B03 eligible after the common cards and probes. Endorsing an upcoming expense in B03 makes F01 eligible even if the intake said no withdrawal. Declining that reason and endorsing discomfort makes B04 eligible instead. Passing B03 confirms neither reason. Other independently eligible cards can still appear.

## Comprehension

| ID | Situation shown | Statement | Interpretation and next step |
| --- | --- | --- | --- |
| C1 | In one year, your balance will be either CHF 9,000 or CHF 12,000. Both are equally likely. | CHF 9,000 is the lowest balance I could end up with. | Right is correct. Left or pass → C2. |
| C2 | Try another example. The two possible balances are CHF 9,500 and CHF 11,000. Both are equally likely. | CHF 11,000 is the lowest balance I could end up with. | Left is correct. Right or pass → factual review. |

## Risk and return

All A, L and V scenarios use a one-year horizon. The financial tables show the exact CHF balances and probabilities used to populate the on-screen sentence. Each client sees one of two statements. Consecutive assignment numbers reverse the endorsed outcome for each item.

| Statement shown | Right | Left | Pass / can’t choose |
| --- | --- | --- | --- |
| I would take the guaranteed balance. | Certain outcome | Uncertain outcome | Show the indifference statement. |
| I would take the uncertain investment. | Uncertain outcome | Certain outcome | Show the indifference statement. |
| Both outcomes work equally well for me. | Record indifference. | Show the comprehension statement. | Leave open. |
| I would need more explanation to compare these outcomes. | Record difficulty understanding. | Leave open. | Leave open. |

For each A scenario answered during profiling, a certain choice imposes φ ≥ threshold and an uncertain choice imposes φ ≤ threshold. Indifference contributes a provisional ±10% interval around the threshold. A skipped or misunderstood comparison contributes no bound. The app intersects the bounds and reports all compatible pilot bands (cut points 2, 5 and 10). It leaves tolerance undetermined after fewer than two understood choices or conflicting bounds. Reserved A scenarios have zero scoring weight.

| ID | When shown | Starting CHF | Guaranteed CHF | Uncertain CHF (50% each) | φ threshold |
| --- | --- | --- | --- | --- | --- |
| A01 | Common | 10,000 | 10,750 | 9,800 / 11,800 | 1 |
| A02 | Common | 10,000 | 10,350 | 9,300 / 12,300 | 4 |
| A03 | Common | 10,000 | 9,394 | 8,925 / 12,675 | 7.999 |
| A04 | Common | 10,000 | 10,200 | 9,800 / 11,800 | 12 |
| A05 | Common | 5,000 | 5,288 | 4,650 / 6,150 | 1.991 |
| A06 | Common | 5,000 | 4,900 | 4,400 / 6,400 | 5 |
| A07 | Common | 5,000 | 5,150 | 4,900 / 5,900 | 10 |
| A08 | Common | 5,000 | 5,048 | 4,931 / 5,869 | 16.003 |
| A09 | Adaptive probe or reserved | 10,000 | 10,775 | 9,800 / 11,800 | 0.5 |
| A10 | Adaptive probe or reserved | 10,000 | 10,725 | 9,800 / 11,800 | 1.5 |
| A11 | Adaptive probe or reserved | 10,000 | 10,675 | 9,800 / 11,800 | 2.5 |
| A12 | Adaptive probe or reserved | 10,000 | 10,650 | 9,800 / 11,800 | 3 |
| A13 | Adaptive probe or reserved | 10,000 | 10,575 | 9,800 / 11,800 | 4.5 |
| A14 | Adaptive probe or reserved | 10,000 | 10,500 | 9,800 / 11,800 | 6 |
| A15 | Adaptive probe or reserved | 10,000 | 10,450 | 9,800 / 11,800 | 7 |
| A16 | Adaptive probe or reserved | 10,000 | 10,350 | 9,800 / 11,800 | 9 |
| A17 | Adaptive probe or reserved | 10,000 | 10,250 | 9,800 / 11,800 | 11 |
| A18 | Adaptive probe or reserved | 10,000 | 10,100 | 9,800 / 11,800 | 14 |
| A19 | Adaptive probe or reserved | 10,000 | 10,139 | 9,918 / 11,682 | 16.994 |
| A20 | Adaptive probe or reserved | 10,000 | 10,238 | 10,050 / 11,550 | 19.982 |

## Loss comparisons

Within each pair, the first card allows an uncertain outcome at or above the stake. The second introduces a possible loss. Choosing the uncertain outcome first and the guarantee second counts as one switch. Two such switches make B09 eligible. The report adds an observation only after the person also endorses B09’s first statement. These choices carry no φ score.

Conditional pair selection uses the intake’s lower starting-capital value. A missing value uses the lowest bracket. The implementation compares the nominal number directly with 7,500 and 15,000. For non-CHF goals, this can select a different bracket than a CHF conversion would.

| ID | Pair | When shown | Starting CHF | Guaranteed CHF | Uncertain CHF (50% each) |
| --- | --- | --- | --- | --- | --- |
| L01 | 1 | Common | 10,000 | 10,600 | 10,000 / 11,600 |
| L02 | 1 | Common | 10,000 | 10,200 | 9,600 / 11,200 |
| L03 | 2 | Common | 5,000 | 5,425 | 5,000 / 6,000 |
| L04 | 2 | Common | 5,000 | 5,175 | 4,750 / 5,750 |
| L05 | 3 | If one core switch and 7,500–<15,000, even assignment | 10,000 | 11,100 | 10,000 / 12,800 |
| L06 | 3 | If one core switch and 7,500–<15,000, even assignment | 10,000 | 10,400 | 9,300 / 12,100 |
| L07 | 4 | If one core switch and below 7,500, even assignment | 5,000 | 5,350 | 5,000 / 5,800 |
| L08 | 4 | If one core switch and below 7,500, even assignment | 5,000 | 5,150 | 4,800 / 5,600 |
| L09 | 5 | If one core switch and at least 15,000 | 20,000 | 21,600 | 20,000 / 24,000 |
| L10 | 5 | If one core switch and at least 15,000 | 20,000 | 20,600 | 19,000 / 23,000 |
| L11 | 6 | If one core switch and 7,500–<15,000, odd assignment | 10,000 | 10,500 | 10,000 / 11,200 |
| L12 | 6 | If one core switch and 7,500–<15,000, odd assignment | 10,000 | 10,200 | 9,700 / 10,900 |
| L13 | 7 | If one core switch and below 7,500, odd assignment | 5,000 | 5,560 | 5,000 / 6,400 |
| L14 | 7 | If one core switch and below 7,500, odd assignment | 5,000 | 5,210 | 4,650 / 6,050 |

## Decisions after a decline

These responses guide follow-ups and interpretation. Only B09 can confirm the repeated loss observation.

| ID | Trigger | Situation shown | Swipe statements in order | What it records or triggers |
| --- | --- | --- | --- | --- |
| B01 | Common | You invested CHF 10,000 for eight years. A year later it is worth CHF 8,500. Your income is steady. | 1. I would reduce how much I have at risk now.<br>2. I would keep my investments as they are.<br>3. I would want to understand the fall before deciding. | Initial action. Reduce → B03. Keep → B07. Understand the fall → B05 and eligibility for S03. |
| B02 | Common | Your investment fell 8% this month. You have an expense due in two years. | 1. My first priority would be checking how much I can withdraw on time.<br>2. I would first look into why the investment fell.<br>3. I would first reconsider how much fluctuation I can live with. | First concern. Cash at deadline → B08. Cause of decline → B06. Tolerance for fluctuation plus B01 reduce → B10. |
| B03 | B01 endorsed reducing exposure | You said you would reduce your exposure after a decline. | 1. The main reason is that I have an expense coming up.<br>2. The main reason is that the loss makes me uncomfortable.<br>3. The main reason is that I think the investment itself has changed. | Reason for reducing. Expense → F01. Discomfort → B04. Changed investment → record the explanation. |
| B04 | B03 endorsed discomfort | Your goal and time horizon stay the same. This time the investment falls 5%. | I would still reduce how much I have at risk. | Tests whether the decision persists at a smaller loss. Left explicitly records no. |
| B05 | B01 requested an explanation | Investments similar to yours have fallen too. | 1. I want to know what caused my own loss before taking action.<br>2. I want to check how much I can withdraw when I need it.<br>3. I have enough information to decide now. | What the client wants to know when comparable investments also fell. |
| B06 | B02 prioritized the cause of the fall | The broader market is flat, but your investment is down. | 1. I would first check whether too much of my money is in a few holdings.<br>2. I would first check whether the investment strategy has changed.<br>3. I would first check my cash needs. | First issue to examine when the holding diverges from the market. |
| B07 | B01 endorsed holding | Your investment has been falling for two years. Your goal is unchanged. | 1. I would review how much money I have at risk.<br>2. I would revisit the date of my goal.<br>3. I would leave the plan as it is for now. | What sustained losses would prompt the person to reconsider. |
| B08 | B02 prioritized available cash | Imagine a separate cash reserve already covers your upcoming expense. | With the expense covered, I would keep my current allocation. | Checks whether the allocation would be retained if the expense were covered. Left explicitly records no. |
| B09 | At least two qualifying L-pair switches | Think back to the scenarios where you could finish below your starting amount. | 1. The possibility of ending with less than I put in changed my choice.<br>2. It would matter to me only if I had to withdraw soon. | First statement endorsed → confirmed observation and eligibility for S02. Endorsing the second records a withdrawal condition only. |
| B10 | B01 endorsed reducing exposure and B02 prioritized tolerable fluctuation | Think about the different decisions you made after a decline. | 1. The withdrawal date explains the difference for me.<br>2. The size of the fall explains the difference for me.<br>3. I found the situation unclear. | Possible explanation for differing choices. |

## Financial constraints

These cards clarify the mandate. The factual screens supply the actual amounts used in funding calculations.

| ID | Trigger | Situation shown | Swipe statements in order | What it records or triggers |
| --- | --- | --- | --- | --- |
| F01 | Withdrawal positive or unknown, or B03 endorsed an upcoming expense | Think of the money you are investing today. Count only what you need from it at your first withdrawal. | 1. I need less than a quarter of my starting investment available then.<br>2. I need between a quarter and half of my starting investment available then.<br>3. I need more than half of my starting investment available then. | Cross-checks the stated share against the funded withdrawal reserve when the amounts permit it. |
| F02 | Positive planned withdrawal | Imagine your balance is lower than planned when a withdrawal is due. | 1. I could postpone the withdrawal.<br>2. I could withdraw a smaller amount.<br>3. Both the date and the amount are fixed for me. | Which part of the withdrawal can change. A swipe records a preference; changing the budget requires editing the intake. |
| F03 | Household expenses not marked as covered elsewhere | Imagine your income drops for six months. | 1. A separate cash reserve would cover my essential expenses.<br>2. I would need some of this investment, but could leave most of it invested.<br>3. I would need most of this investment for essential expenses. | Reliance on invested funds can flag a missing household reserve. |
| F04 | Variable income reported | Think about your planned monthly contribution. | I could pause contributions without taking money out of this investment. | Tests reliance on future contributions. Left explicitly records no. If earmarked savings are positive, no or pass flags them for review. |
| F05 | Employer exposure reported | Imagine your employer runs into financial trouble. | 1. Both my income and my investments could fall at the same time.<br>2. My income is the part I would expect to fall.<br>3. My investments are the part I would expect to fall. | What the person believes could fall together. The intake flag also prompts an employer-exposure review. |
| F06 | Any ethical exclusion or preference entered | A fund does not disclose whether it invests in an activity you flagged. | 1. I would need proof that the activity is excluded before accepting this fund.<br>2. I could accept the fund and treat this exclusion as a preference. | Requiring verification flags holdings coverage and makes S05 eligible. A mandatory exclusion entered in intake remains binding. |
| F07 | Intake spending currency differs from CHF, including undecided | Think about the currency you will actually spend. | **Known currency:** I expect to pay this expense in {code}.<br>**Otherwise:**<br>1. I expect to pay this expense in Swiss francs.<br>2. I expect to pay this expense in euros.<br>3. I expect to pay this expense in US dollars. | With a known code, right confirms it. Left or pass leaves it open for review. Without a code, use the currency statements in order. |
| F08 | Target entered and at least one applies: desired return missing, required rate unavailable, or required rate above the desired rate. | Imagine the current plan is unlikely to reach your target. | 1. I would first reconsider my deadline.<br>2. I would first reconsider how much I contribute.<br>3. I would first reconsider my target amount. | Which input the client would revisit. Edits to amounts and dates are made in intake. |

## Monitoring

Read in priority order. The first matching row is the single closing scenario. The first endorsed statement sets the monitoring preference. Passing it ends the route without a stated preference.

| ID | Trigger | Situation shown | Swipe statements in order | What it records or triggers |
| --- | --- | --- | --- | --- |
| S01 | Positive withdrawal | At your next review… | 1. Show me how much I could withdraw on the planned date first.<br>2. Show me the gap to my target first. | Withdrawal review display. |
| S02 | B09 first statement endorsed | If my balance falls below what I put in… | 1. I want an alert when my losses reach a threshold I set.<br>2. I would prefer a reminder at my next review. | Loss notification preference. |
| S03 | B01 requested an explanation | After a decline… | 1. First, show me what the decline means for my goal.<br>2. First, show me which holdings lost value.<br>3. First, show me how the wider market performed. | Preferred explanation after a decline. |
| S04 | Variable income | When deciding when to review my plan… | 1. A change in my contributions should trigger a review.<br>2. A new expense should trigger a review.<br>3. I would prefer to request a review myself. | Trigger for a plan review. |
| S05 | Mandatory exclusion or F06 requires verification | Think about the activities you want excluded. | 1. I want to revisit my exclusions when a fund changes its holdings.<br>2. I want to check exclusions at my regular review. | When to revisit exclusions. |
| S06 | Default | Think about how often you want to revisit your profile. | 1. A yearly check-in would suit me best.<br>2. I would prefer a check-in every three months.<br>3. I would prefer to check in when my circumstances change. | Preferred review frequency. |

## Transfer checks

The research pilot is optional. After the closing card, the app freezes predictions, then shows the two reserved A scenarios and two V scenarios in that order. Even assignments receive V01 and V03. Odd assignments receive V02 and V04. V uses the same statements and gestures as A. The model predicts the certain or uncertain choice only when the whole estimated φ interval falls strictly on its corresponding side of the threshold. A boundary touch or overlap leaves the prediction open.

| ID | Assignment | Starting CHF | Guaranteed CHF | Uncertain balances and probabilities | What it tests |
| --- | --- | --- | --- | --- | --- |
| V01 | Even | 10,000 | 10,200 | 9,000 (25%) / 11,000 (75%) | Transfer to unequal odds; excluded from scoring. |
| V02 | Odd | 10,000 | 10,400 | 9,500 (75%) / 14,500 (25%) | Transfer to unequal odds; excluded from scoring. |
| V03 | Even | 5,000 | 5,100 | 4,600 (60%) / 6,500 (40%) | Transfer to unequal odds; excluded from scoring. |
| V04 | Odd | 10,000 | 10,400 | 8,000 (25%) / 12,000 (75%) | Transfer to unequal odds; excluded from scoring. |

## Questions for the team review

| Where to look | Decision to discuss |
| --- | --- |
| A01–A20 | Is “I would take…” clear enough that a left swipe means preferring the other investment? Can a person who likes neither find “I can’t choose”? |
| L01–L14 and B09 | Within a pair both the guaranteed amount and the uncertain balances move. Is the report clear that it describes a repeated choice in these scenarios, without assigning a loss-aversion coefficient? |
| B, F and S sequences | The first yes ends the scenario. Could two reasons both fit? Review B03 and S06 for cases where wording order might determine the recorded answer. |
| S01–S06 | A planned withdrawal always takes priority. Should someone who also requests loss alerts get a second monitoring card? |

Sources for this edition: [profile bank](bank.json), [transfer items](transfer_validation.json), [displayed statements](../riskmatch/swipe.py), [routing and scoring](../riskmatch/profile.py) and [session flow](../riskmatch/profile_session.py).
