# Step 3.0a · Client profile dimensions

The fixed questionnaire captures five dimensions. Each answer has a
primary purpose so a single response does not raise both risk tolerance
and financial capacity.

| Dimension | What it captures | Inputs for the fixed questionnaire | How it informs the result |
| --- | --- | --- | --- |
| Financial capacity | The client's ability to absorb a financial loss and keep enough cash available | Investment horizon, upcoming withdrawals outside the emergency reserve, financial buffer and the loss that would compromise the plan | Sets a ceiling on the continuous risk estimate |
| Risk tolerance | The client's willingness to accept investment fluctuations and losses | Response to a temporary decline and trade-offs between stability and growth | Determines the risk level the client is willing to take, subject to the capacity ceiling |
| Knowledge and experience | Familiarity with investments and ability to understand the proposed trade-offs | Products held, investing experience and understanding of diversification and loss | Guides explanations and flags unfamiliar features for clarification |
| Investment objectives | What the investment is meant to accomplish | Primary purpose such as preserving capital, generating income or growing capital | Gives context for the comparison and surfaces a mismatch between the goal and the permitted risk level |
| Investment constraints | Explicit limits on what a portfolio can hold or do | Asset or sector exclusions, restrictions on borrowing and other supported allocation limits | Filters eligible portfolios and defines constraints for a later re-optimization |

A loss that would prevent someone from meeting a commitment belongs to
capacity. Discomfort with a temporary loss belongs to tolerance. Record
the horizon and withdrawal needs once under capacity, even when they
also help explain an objective. Knowledge informs explanations and
cannot increase the risk level by itself. A growth objective also
cannot lift the ceiling.

Apply `min(tolerance_volatility, capacity_volatility)` before assigning
the risk category. Then retain the client's constraints when checking
which portfolios can actually be offered. The category has a reference
volatility for comparison, while the capacity ceiling remains a limit
on the portfolio presented to the client. A reference above that ceiling
or an infeasible allocation calls for an explanation and a feasible
configuration before offering a portfolio.

For example, a client may want long-term growth and be comfortable with
large fluctuations, yet need part of the money in two years. If the
tolerance estimate is 10% and the illustrative capacity ceiling is 8%,
the effective level is 8%, in **Balanced**. Limited investing experience
calls for a clearer explanation of the trade-offs. An explicit
no-borrowing constraint still applies when comparing portfolios.

These definitions guide the fixed questions in 3.0b. The scoring and
ceiling rules in 3.0c and the data contract in 3.0d follow separately.
