# Step 3.0e · Fixed questionnaire pilot

## Run two sessions

Recruit 5–10 volunteers for a small exploratory test. Use the English
questionnaire v0.1, fixed scorer v1.0 and the configured reference Sharpe
of 0.35 for both sessions. Record the versions. If the wording changes,
start a new comparison for that version.

1. Give each volunteer a random participant code to reuse at the second
   session. Explain that participation is optional and the activity is a
   test of the questionnaire. Participants can skip an item or stop.
   Collect the minimum needed and retain only aggregate results in the
   repository. Use the predefined choice IDs and avoid recording names,
   income amounts, account details or personal stories.
2. At the first session, have the participant answer the 14 questions
   independently. Record response time, skips and uncertainty choices.
   Ask the neutral probes below after they finish. Record whether their
   explanation matches the intended meaning, partly matches, or misses
   it before providing any clarification.
3. Repeat the fixed questionnaire after 7–14 days. Give the same
   instructions and keep the first answers and result out of view.
   Before showing a comparison, ask whether the participant's situation
   changed materially. Record only yes, no, or unsure. Explain the
   intended meanings and show a worked example after the retest.

Participants can use a consistent fictional situation instead of describing
their finances. Mark such responses as fictional and report them separately.
Use the fictional cases below for the structured edge-case walkthrough.

## Comprehension probes

| Question | Ask the participant | What a clear explanation reflects |
| --- | --- | --- |
| F01–F02 | What money and time periods did you have in mind for these two questions? | Most of the investment over its planned horizon and the share withdrawn within two years are distinct. |
| F04–F06 | How would you explain the difference between these two questions? | F04 concerns a planned payment. F06 concerns willingness to keep an allocation through a temporary loss. |
| F09 | What does holding many companies change in this example? | It spreads exposure to individual companies. An ETF can still fall with the market. |
| F12–F13 | What would your choices change about the portfolio? | Exclusions change eligible investments. Borrowing permission concerns investing more than the amount contributed. |

Also ask which wording was hardest to interpret and whether any response
option was missing. Count paraphrases as clear when they express the
intended meaning in the participant's own words.

## Worked cases

| Case | Expected output |
| --- | --- |
| High willingness, horizon of two to less than five years | 14% tolerance and 8% capacity, giving Balanced at 8%. |
| Upcoming withdrawals uncertain | Clarify F02 and hold the catalogue reference. |
| A loss under 5% compromises a planned payment | Capacity at 3%, below the catalogue range. |
| Selecting gold and “No exclusions from this list” together | Reject the contradictory choices and prompt the participant to select again. |

The independent notebook cell executes all four checks on synthetic inputs.

## Pilot worksheet and summary

Use a local worksheet with the participant code, session number, completion
time, choice IDs F01–F14, source of answers (personal or fictional), and
whether the situation changed. Record one separate comprehension rating per
probe. Exclude incomplete responses from paired score analyses and report
their count.

For matched respondents with no reported material change and unchanged
versions, report exact category agreement, including the below-catalogue
outcome as a distinct category. Use the number of matched eligible
respondents as the denominator. Also report median absolute change in
effective volatility in percentage points, per-item agreement and the
number of reference checks that changed status. Compare multiple-choice
items as sets. Report unmatched responses, material changes and unknown
status separately. For comprehension, report clear ratings out of all rated
participants per probe, along with skips or uncertain answers per item.
Summarize concrete wording changes and repeat affected items after revision.

This pilot provides descriptive feedback from a small group. Human results
and the retest remain pending. The checklist item stays open until both
sessions have been run and the aggregate findings are recorded.
