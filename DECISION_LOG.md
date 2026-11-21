# RiskMatch decision log

## 2026-11-21 — English as the project language

The project owner chose English for project files and folder names. This includes client-facing questions, documentation, research terminology, Python identifiers and messages, notebook cells and generated output. Imported course materials and datasets keep their original contents and filenames.

| Change | Current location |
|---|---|
| Client profile specification and research protocol | [Client profile](CLIENT_PROFILE.md) and [research](RESEARCH.md) |
| English card bank and separate transfer items | [60 cards](questions/bank.json) and [4 transfer items](questions/transfer_validation.json) |
| Data audit and pinned pilot dependencies | [Audit module](data_audit.py) and [requirements](requirements-pilot.txt) |
| Course groupings | `Theory/CFA/`, `Theory/Course_Notes/`, `Theory/Methodology/` and `Theory/Quant_Project/` |
| Local research data and input checksums | `data/additional_data/` and [pilot checksums](data/pilot_checksums.json) |
| In-progress profile, mandate and CHF demonstration | [Profile](riskmatch/profile.py), [mandate](riskmatch/mandate.py) and [catalogue generator](riskmatch/catalogue.py) |

The English questionnaire uses schema version `1.0-pilot-en` and the separate transfer set uses `pilot-1-en`. Field names and labels changed together with their readers. Card IDs, canonical answer order, stakes, outcomes, probabilities and financial thresholds were preserved. The input manifest records the two new questionnaire hashes. Market and course inputs retained their previous content.

**Verification.** Compared the original and English implementations on 1,000 seeded response paths covering all 60 cards. The paths, numerical φ bounds, held-out predictions and allocation choices matched. Verified hashes for 1,110 local course and data files across the directory renames, excluding operating-system metadata. The notebook reproduces the input audit and contains an executable check of the English bank at Step 3.1d.

**Team repository.** The reworked project replaces the previous tree on the default branch. The public source includes the synthetic demo, the English cards and the code for rebuilding the historical walkthrough from authorized local inputs.

**Handoff.** Development of the first product phase paused for this migration. The client specification and card bank are available for review. Human comprehension, timing, category calibration and the one-week retest remain open. Test the English wording in the pilot.

## 2026-11-21 — Phase 1 client profile web app

Delivered a local Streamlit web application for browser-based intake, adaptive choices and client review. The stage ends with a reviewable profile export. No market data connection is required. The profile collects amounts or ranges, records unknowns, distinguishes required and desired return, and separates tolerance from reserves and binding constraints.

**Decisions.** The funding calculation uses conservative endpoints and separates household reserves, withdrawal savings and growth contributions. The aversion cut points and the indifference width are provisional. Corrections recalculate the relevant route and invalidate confirmation. Pilot predictions are frozen before feedback. Post-feedback revisions are ineligible for the independent check. An unfinished pilot export contains progress rather than forecasts. The app stores the active interview in browser-session scope on the local server. Persistence across sessions requires downloading a profile file.

**Verification.** Unit tests cover all 60 cards across 1,000 simulated routes, retry and early exit, scoring, financial ranges, a home purchase with an immediate funding shortfall, mandatory exclusions, immutable validation predictions, retest accounting and replay after corrections. Browser tests cover touchscreen swiping, keyboard-only answers, an undetermined profile, local download and restore. The notebook replays the CHF 50,000 example and the conservative funding calculation. Participant calibration, completion times and one-week stability still require observations. Portfolio matching remains the next product phase.

## 2026-11-21 — Single-statement swipe questionnaire

After the factual intake, every scenario and validation item presents one statement. Right means yes, left means no. A declined explanation can trigger another statement. Unconfirmed reasons stay open. A financial card discloses the stake, horizon, guaranteed balance, possible balances and probabilities before asking for one preference. The pilot alternates which outcome the statement endorses. A separate clarification can record indifference or difficulty understanding a trade-off.

Swipes log direction, statement number and time. Drafts replay to the same follow-up. Existing option-based exports retain their original answer events. Analyze each presentation format separately in the pilot and measure both completed scenarios and gestures.

## 2026-11-21 — Internal review of the swipe bank

The team deferred participant testing and will use the current questionnaire for development. The [review tables](questions/CARD_REVIEW.md) reproduce all 60 profile scenarios, four transfer checks, statement order and branch conditions for a wording and routing review.


## 2026-11-21 — Step 0 audit and setup

Reviewed 0.1–0.16 against files, local runs and GitHub. Recovered the November 17 instructor feedback from the previous prototype and applied the reworked adaptive MVP scope. Created the shared environment, benchmark configuration and H01–H07 experiment register. The independent course replay uses local teaching data. The ETF prospective calendar is specific to the benchmarks. Research margins and final windows still need dated study-level decisions.

One approving review is now required on main, including administrator changes. The setup work is on a separate pull request. The local app and executed research notebook remain in the working copy. The human questionnaire pilot stays deferred. [Setup evidence and open items](SETUP.md) · [GitHub change](https://github.com/NvarMaley/TindeRisk/pull/62)

The owner confirmed the existing GitHub repository and team invitations. Item 0.3 is complete.

## 2026-11-21 — Portfolio method names

The checklist and notebook use the quantitative methods as task names. The README distinguishes macro analysis across portfolios from the optional H03 allocation experiment. Catalogue admission remains a research decision.

## 2026-11-21 — Project-wide scope review

Reviewed technical Steps 0–10 against the three product phases. The historical ETF panel and three-asset benchmarks retain their experiment-specific definitions. Candidate universes and feasible risk budgets are study-specific. Revised mandatory catalogue, backtest and UI assumptions, corrected the Expected Shortfall label, and added pitch and release coverage to the notebook. The data collection audit remains in progress.

## Checklist evidence review

The earlier naming pass left scope assumptions in the task descriptions. The subsequent scope pass corrected the asset universe and allocation rules. This review also corrected the unsupported grading legend, the profile correction wording, conditional regime selection and two open LN7 tasks whose results already existed in the course replay. The pending human pilot and independent portfolio validation remain open.

## README verification against the product decisions

Clarified the three phases, current delivery status, provisional duration, client confirmation, and use of the aversion interval across the constrained net frontier. Historical experiments keep their original scope.
