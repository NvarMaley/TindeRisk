# Step 0 handoff

## Course, scope and team

The team's dated account of the professor's reply on November 17 confirms the topic, the continued applicability of the 2024 brief, the two StockTwits sources and discretion over backtest dates and depth. The Moodle sample is available locally. The larger raw-message sample was offered separately. Permission given for the class project has the scope of that conversation. The archive describes an earlier product design. [Professor feedback in the previous project record](https://github.com/NvarMaley/TindeRisk/blob/c41fd972784a861662d1cd609df013f6d431d0ea/docs/05_DECISIONS.md#professor-feedback--2026-11-17)

**Current MVP.** One goal per client, adaptive swipe profile, spendable reserve, comparison of admissible portfolios after modeled costs in the goal currency, user selection, closing-price monitoring and a confirmed rebalance. Compare simple allocations first. Additional strategies enter the catalogue through the research protocol. HMM regimes and FOMC text signals are extensions. Human calibration is deferred. [Project definition](README.md) · [Research decisions](RESEARCH.md)

**Working sequence.** Setup → dated data inventory and cleaning → estimates and course replications → signals and constrained allocations → net backtests → client comparison and monitoring → pitch rehearsal and release audit. When the presentation date is known, schedule the rehearsal and independent reproduction before it. The existing checklist names Raf for instructor liaison and Raf/Vlad on data tasks. Proposed workstreams for the group to allocate are data, quantitative estimation, portfolio construction and backtests, app and client experience, and integration and pitch. One person can hold multiple workstreams. Record each person's actual assignment when confirmed.

**Repository access, November 21.** GitHub returned four accounts with access, including the owner, and two pending invitations. Reconcile the two invitees against the five-person roster before sending duplicates. The default branch requires a pull request with one approving review, including for administrators. The setup branch passed its public tests. A teammate can review the change here. [Setup pull request](https://github.com/NvarMaley/TindeRisk/pull/62)

## Shared environment and course replay

From the repository root, create a fresh Python 3.12 environment. On Windows, activate it with `.venv\Scripts\activate`. The six class reproductions read the three supplied data files in `data/Data for laboratories-20261119/`. CI uses public tests and checks out the source on GitHub runners. The local course replay writes its figures and numerical checks to `results/course_labs/`.

```sh
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip check
python -m pytest -q
python -m research.course_labs
```

A clean Python 3.12.6 environment reproduced the course exercises. All 18 local tests passed with the app running and the browser suite enabled. The original lab notebooks are preserved for comparison. The independent project implementation covers the exercises below. The course calculations use the supplied inputs, conventions and numerical targets. [Lab replay](research/course_labs.py) · [Dependencies](requirements.txt)

| Lab | Verification and differences to account for |
| --- | --- |
| LN1 · Markowitz | Risky frontier, minimum variance, 20% target, tangent weights and capital market line. The analytic target return is 7.8659%, against approximately 7.8657% in the handout. The gamma values differ slightly with numerical optimization. |
| LN2 · Beta | Plotted the returns and wealth paths, applied the exercise's UVXY correction on March 8, 2012, and fitted each ticker against SPY on matched dates. AAPL beta 1.03235635 and the equal-weight beta 0.64995114 match the course. The anomaly correction applies to this teaching sample. |
| LN3 · Stability | Reproduced equal-weight return 7.7943% and volatility 22.6312%. The course annualizes the mean daily log return by compounding and builds covariance from marginal volatilities and pairwise correlations. Checked unconstrained and long-only composition maps and 500 seeded simulations of 101 frontier portfolios. The analytic 15% target gives gamma 0.50269 against the exercise solver's 0.50702. |
| LN4 · Black–Litterman | Implied risk aversion 1.62874226. The teaching solver reproduces tracking error 1.32125% at τ = 0.05 and τ ≈ 0.09613 at 2%. Tightening the solver changes the first tracking error to 1.53226%. Retain solver and tolerances with allocation results. |
| LN5 · Risk budgeting | Equal-weight volatility 19.86674%. The positive log-constrained solution has four relative contributions of 25% after normalization. |
| LN7 · Sentiment | Recomputed the SPY market model on each ticker's preceding year and matched all 37,950 supplied non-missing residuals within 5 × 10⁻¹⁶. Reproduced 454 good, 294 neutral and 383 bad events, the 14-observation polarity signal and the one-session long and short portfolios. The classroom replay uses the supplied missing-return convention and excludes trading costs. Its P&L is exploratory. |

## Study registration and dates

The [study register](experiments.csv) starts one design record per H01–H07 and one dated benchmark record. Owner roles identify workstreams. Before an independent comparison, append a versioned row per trial with its named owner, data vintage, dated specification, fixed margin, dates, allowed variations and eventual result. Economically useful gains remain open where the team has not chosen a threshold. Keep the historical explorations labelled when making that choice.

The [benchmark configuration](config.yaml) records the universe, execution convention, currencies, fees, estimation window, seeds and dates. For the three ETF references, 2005 onward supplies warm-up, 2010–2015 is development and January 2016–October 2026 is retrospective validation. The prospective window is December 2026–November 2027. Its first signal belongs after the final November 2026 close and before the December execution. An unlogged order can be reconstructed for illustration only.

For H01–H04 and H07 ETF adaptations, use the benchmark development and retrospective windows as candidate windows and intersect them with the study’s available history. A prospective comparison can use only decisions archived after its own specification is frozen. An unready model misses that origin. For the classroom H06 replication, use 2010–2015 for development and January 2016–March 2020 for separate historical replay, subject to actual ticker coverage. The final study-specific splits still depend on the Step 1 inventory of jointly available outcomes and point-in-time predictors. StockTwits ends in March 2020. A subsequent ETF return supplies no missing company sentiment. H05 needs verified accounting availability and delisting coverage. Previously examined 2005–2025 macro relationships remain exploratory. Record a separate split for each study and purge overlapping outcomes before any final estimates. [Time-split protocol](RESEARCH.md#etf-benchmark-schedule)

## Publication rights

| Material | Verified evidence and remaining decision |
| --- | --- |
| Team-authored code and synthetic data | The repository contains a synthetic demonstration and original implementation. The team still needs to select its code license. A repository license should state which project-authored files it covers. |
| Yahoo ETF history | Keep provider quotes and price histories out of the public bundle. Obtain a display agreement or a source permitting redistribution for a hosted price view. [Yahoo Finance data providers](https://help.yahoo.com/kb/SLN2310.html) |
| FRED and ALFRED | Check each series owner, permitted use, copyright notice and required attribution before dashboard display or model training. Public availability alone does not determine reuse rights. [FRED service terms](https://fred.stlouisfed.org/legal/terms/) |
| WRDS, CRSP, Compustat and historical classifications | Academic access is subject to the institution's subscriptions and vendor agreement. Verify permission for the specific proposed output, recipients and use. Raw data remain in the local research directory. [WRDS download policy](https://wrds-www.wharton.upenn.edu/pages/about/data-download-and-analysis-policy/) · [WRDS AI policy](https://wrds-www.wharton.upenn.edu/pages/about/ai-policy-on-chatgpt-and-other-generative-ai-tools/) |
| Moodle, course materials, StockTwits, figures and larger message archive | The instructor's approval is recorded above. Ownership of underlying market data and third-party text needs a separate check for redistribution. The source notebooks, supplied data, exercise charts and local market outputs stay outside the public setup branch. |
| Libraries and models | Direct dependencies are installed from pinned upstream packages. Streamlit, CVXPY, OSQP, Clarabel and PyArrow declare Apache licenses, pandas and scikit-learn declare BSD licenses. Keep upstream notices when redistributing a package. No external model weights are included in the setup. Record the exact license of any future pretrained model before distributing it. |

## Completion criterion

Mark a technical item complete when the implementation and corresponding test pass, the inputs and command reproduce the stated output, the notebook or project documentation records the result and limitations, and the change has been reviewed. Use a second member's approval for merges to main. Keep external decisions, unverified results and partial items open with the remaining action identified.
