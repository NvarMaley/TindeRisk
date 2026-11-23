# Implementation checklist

Use each subsection in order. Capture commands, dataset versions, denominators, units, timestamps, parameters and observed discrepancies under the matching notebook ID. A passing synthetic identity checks the implementation on that case only. Record the remaining bias, likely direction and sensitivity range when possible. Data acquisition and out-of-sample market validation remain open until the listed evidence exists.

The local [QARM project brief](Theory/Quant_Project/Project_Brief/QARM_2_Slides___Projects.pdf), slides 3–4, asks for a course-based quantitative strategy, a portfolio web app, GitHub code and a 15-minute client pitch. Its strategy examples illustrate possible approaches. The written research record also serves the team's own reporting goal. Verify any later instructor clarification separately.

Work down the numbered tasks. Each box describes an action, method and observable acceptance check. Leave it open until the matching notebook chapter names the input version, command, result and limitation. Record a change in scope in the journal. An item may be deferred or rejected with a reason. The local import status and remaining data gates are recorded in the [data inventory](data/README_data.md).

[Methodology audit](METHODOLOGY_AUDIT.md) records the course crosswalk, priority findings and conditional extensions. For each bias check record the exposed population, expected direction (or unknown), control result, sensitivity of the client decision and unresolved limitation. An unchecked task may have a documented design and still lack empirical evidence.

The selected quantitative extension pairs classical and robust frontiers, a local dual check and reverse withdrawal stress. The historical comparisons are complete. Section 7.2 records the decision to withhold prospective admission.

### Correction de périmètre du 23 novembre 2026

- [x] Étendre le portefeuille investissable aux 13 ETF du panel et garder le cas à trois comme référence. Vérifier les prévisions, les huit dates, le choc conjoint, les 462 simulations d'exécution, les scénarios client, les exclusions et le suivi. Le notebook contient le comparatif recalculé. [Résultats et limites](research/universe/README.md)

### Course acceptance evidence (brief slides 3–4)

| Course criterion | Tasks | Reproducible demonstration to prepare |
|---|---|---|
| Client need, strategy and use of course tools | 2.1.2, 6.1.1–6.2.2 | Change the withdrawal in the same mandate, recalculate the reserve, compare the constrained frontier with a simple benchmark and explain sensitivity to covariance and fees. |
| Interactive, complete and technically reliable web app | 8.1.2, 9.1.1–9.1.2 | Open the deployed Streamlit URL in a fresh browser, change a constraint and verify the displayed numbers against the notebook. Record the code URL and release version. |
| Clear presentation and response to client questions | 9.1.3 | Time a 15-minute rehearsal; have a reviewer ask about risk, costs or an infeasible goal and trace the answer to an observed result. |

The earlier team's dated handoff reports that the instructor confirmed the topic and the 2024 brief. The [dated feedback](https://github.com/NvarMaley/TindeRisk/blob/c41fd972784a861662d1cd609df013f6d431d0ea/docs/05_DECISIONS.md#professor-feedback--2026-11-17) and slide-to-deliverable mapping are recorded in notebook 1.1.1. Research extensions remain open workstreams. A written report serves the team's own documentation needs.

## 1. Project controls and research design

### 1.1 Establish the course and team baseline

**Evidence to retain:** requirement mapping and environment manifest. **Course reading:** [Advanced Data Analytics Lecture3 Explique](Theory/Course_Notes/Advanced_Data_Analytics_Lecture3_Explique.md) · [Guide Ultime Chapitre 29](Theory/Methodology/Chapter_Guides_00-34/Guide_Ultime_Chapitre_29.md).

- [ ] **1.1.1** Read the applicable QARM brief and instructor clarification. Record versions, the course optimization requirement, web app, GitHub and pitch deliverables. Cross-reference each requirement to a task and have a teammate check the mapping.
  - **Procedure.** Read the Project Brief slides and any dated instructor clarification. Make a requirement → slide/page → task → acceptance evidence matrix.
  - **Verification and failure handling.** Have a second reader distinguish compulsory deliverables from example client mandates. Leave any disputed interpretation open.
  - **Bias and control.** Scope anchoring. Trace each supposed course requirement to a page or clarification; mark team preferences separately when unsupported.
- [x] **1.1.2** Scope decision recorded. Formal responsibility assignments and reviewer scheduling were waived by the project owner on 22 November 2026.

- [x] **1.1.3** Connected the local workspace to GitHub, pinned the baseline interpreter, recorded the licensing position and reproduced the synthetic notebook checks from a fresh checkout. See notebook 1.1.3 and the Course examples workflow. Third-party redistribution rights remain an open release item in 9.1.2.

The primary brief mapping is documented in notebook 1.1.1. Independent reading confirmation is pending.

### 1.2 Register what would change a decision

Completed 22 November 2026. Notebook 1.2 records the prospective precision simulation, coverage checks and numerical reproductions, including the LN3 discrepancy.

**Evidence to retain:** dated study register and reproduction log. **Course reading:** [Guide Ultime Chapitre 01](Theory/Methodology/Chapter_Guides_00-34/Guide_Ultime_Chapitre_01.md) · [literature](Theory/Course_Notes/literature.md).

- [x] **1.2.1** Create one study record per H01–H07 with paper/lab, target, horizon, universe, benchmark, variants, primary loss, useful-gain threshold and rejection rule. Distinguish exact replication from adaptation.
  - **Procedure.** Register estimand, unit of observation, population, H0/H1, timing, gross and net economic effect, benchmark and multiplicity family before fitting. Specify a withdrawal or rejection rule.
  - **Verification and failure handling.** Archive a signed/versioned protocol. A changed primary outcome opens an exploratory variant with a new ID.
  - **Bias and control.** Underpowered discovery. Before the trial simulate null and minimum useful effect with the proposed dependence, sample size and model-selection pipeline. Record false positives, power and interval width. Downgrade a trial with inadequate precision to exploratory.
- [x] **1.2.2** Freeze development, inner validation and untouched evaluation dates after coverage audit. Mark inspected periods retrospective. Record amendments and variant counts before inspecting new outcomes.
  - **ETF calendar.** Notebook 1.2.2 freezes the CHF frontier calendar. The [study register and calendars](research/study_protocol.md) cover H01–H07.
  - **Procedure.** Build a date ledger of warm-up, training, inner validation and last untouched block for each target horizon. Mark any published or previously inspected test dates.
  - **Verification and failure handling.** Require maximum training-label end before the next evaluation decision. Where prospective outcomes do not exist, mark prospective evaluation pending.
  - **Bias and control.** Repeated access to a holdout. Record who viewed each period, when and why; a model revised after seeing it requires a new evaluation period.
- [x] **1.2.3** Reproduce analytical course examples for mean–variance, risk-free asset, shrinkage, Black–Litterman, risk budgets and event studies. Record expected/actual values, tolerances and discrepancies.
  - **Procedure.** Run LN1 Markowitz, LN2 beta, LN3 stability, LN4 views, LN5 risk budgets and LN7 events against lab fixtures. For LN6 construct the two-identical-assets example.
  - **Verification and failure handling.** Archive constraints, units, expected and reproduced values, tolerance and explanations. Matching a lab validates the calculation for its fixture only.
  - **Bias and control.** Shared implementation errors. Reconcile with an independently derived analytical solution on a fixture outside the source lab.

## 2. Profile the client

### 2.1 Build the factual intake

Implemented and tested 22 November 2026. Notebook 2.1 records the four-screen walkthrough and financial checks. The theoretical payment clarification in 2.3.2 completes the revised interpretation criterion.

**Evidence to retain:** mandate and dated cash ladder. **Course reading:** [Portfolio-Management-explications copie](Theory/CFA/Portfolio-Management-explications%20copie.md) · [Guide Ultime Chapitre 34](Theory/Methodology/Chapter_Guides_00-34/Guide_Ultime_Chapitre_34.md).

- [x] **2.1.1** Design four screens for goal/currency/horizon, capital and contributions, withdrawals and reserves, then desired return and preferences. Accept ranges and unknowns. Test missing, zero, negative and contradictory values by field.
  - **Procedure.** Use an intake schema with value/range, unit, currency, timing and explicit unknown. Encode ethics as hard exclude versus preference. Use hypothetical payment examples to check how the interpretation affects the reserve.
  - **Verification and failure handling.** Retain original answers and corrections. Check that zero, missing and “prefer not to answer” produce distinct states.
  - **Bias and control.** Anchoring and missing-not-at-random amounts. Record range, unknown and refusal separately; check whether the funding outcome changes at plausible endpoints.
- [x] **2.1.2** Calculate protected and investable capital using dated withdrawals and confirmed external funding. Reconcile cash sources and uses. Test a fully funded expense, immediate withdrawal and reserve exceeding capital.
  - **Procedure.** Construct a dated cash ladder. Reserve the maximum cumulative uncovered outflow plus the separate safety buffer, accounting for earmarked resources only once.
  - **Verification and failure handling.** Reconcile assets to reserve plus investable capital or an explicit shortfall. Vary the endpoints of ranges to expose mandates that switch eligibility.
  - **Bias and control.** Optimistic funding. Stress delayed contributions and simultaneous household cash needs. Report the earliest shortfall date and amount across feasible joint scenarios.
  - **Funding invariant.** Compute the dated cash ladder from liabilities, settlement, safety buffer and confirmed funding. Keep the tolerance band out of that calculation. Change only tolerance and compare the entire ladder; any difference requires correcting the dependency and recomputing affected proposals. Move the withdrawal earlier with tolerance fixed and rerun liquidity even when the amount stays constant.
- [x] **2.1.3** Solve the goal-funding return from dated cash flows with an explicit timing convention. Show it beside the desired return. Test a known zero-return case and an underspecified or infeasible mandate.
  - **Procedure.** For dated deposits Cᵢ solve target = initial(1+r)^T + Σ Cᵢ(1+r)^(T−tᵢ) using scipy.optimize.brentq on a bracket with opposite signs. Document timing and annual basis.
  - **Verification and failure handling.** Plug the solution back into terminal wealth. Check boundary/non-unique cases for mixed-sign flows. Report unresolved when a justified bracket or unique solution is unavailable.
  - **Bias and control.** Nominal/real mismatch. State whether the target is in today's or future currency and convert consistently under disclosed inflation assumptions. Report sensitivity of required return.

### 2.2 Build the adaptive swipe interview

The [versioned bank](questions/profile_v1.json), [engine](src/riskmatch/interview.py) and notebook 2.2 record the executable checks. The [behavioral rationale](questions/QUESTIONNAIRE_DESIGN.md#how-to-interpret-hypothetical-answers-in-the-report) documents the wording review under the revised theoretical scope.

**Evidence to retain:** versioned card specification and route traces. **Course reading:** [W13 Behavioral Finance Guide FR](Theory/Course_Notes/W13_Behavioral_Finance_Guide_FR.md) · [Guide Ultime Chapitre 14](Theory/Methodology/Chapter_Guides_00-34/Guide_Ultime_Chapitre_14.md) · [Guide Ultime Chapitre 18](Theory/Methodology/Chapter_Guides_00-34/Guide_Ultime_Chapitre_18.md).

- [x] **2.2.1** Draft 60 scenario IDs including 15 common items. For every card record construct, wording, amounts, probabilities, interpretation, trigger and pass behavior. Review the English wording for leading statements and numeracy burden.
  - **Procedure.** Use questions/QUESTIONNAIRE_DESIGN.md. Freeze a blueprint of 1 comprehension, 1 declared tolerance, 5 trade-offs, 4 matched loss scenarios, 2 decline reactions, 1 flexibility and 1 monitoring card. Record exact amounts, polarity, competing interpretation and authorized score effect.
  - **Verification and failure handling.** Check the yes/no/pass mapping against the displayed statement and exercise mirrored choices in simulation. Revise ambiguous mappings before route simulation. Balance affirmative endorsement of risky and certain options.
  - **Bias and control.** Acquiescence and frame confounding. Counterbalance which option a yes endorses and compare equivalent response encodings in software. For loss pairs record changes in mean, variance, probabilities and reference point; isolate only what the design identifies.
- [x] **2.2.2** Implement one statement per gesture, right=yes and left=no, with pass, keyboard equivalent and an explanation after failed practice. Test on touch and desktop, including short drags and repeated events.
  - **Procedure.** Persist card version, wording, display side, step, answer and correction in an event history. Replay mobile, mouse and keyboard paths against the same canonical choice.
  - **Verification and failure handling.** One gesture yields at most one response. A pass adds no directional evidence. Verify identical scores after replay and after correcting a gesture.
  - **Bias and control.** Interface measurement error. Replay passes and corrections through the supported input methods and check their recorded meanings. Never infer confidence from gesture speed alone.
- [x] **2.2.3** Map each risk choice to a threshold by equating the one-year mean–variance utilities of the alternatives. Validate the implied threshold analytically. Intersect consistent bounds and return unresolved status on contradiction or insufficient evidence.
  - **Procedure.** Compute μ=Σpᵢrᵢ and v=Σpᵢ(rᵢ−μ)² on decimal returns at a common horizon. For sure return c solve φ*=2(μ−c)/v. Test v=0, dominance, negative thresholds and ties before using an item.
  - **Verification and failure handling.** For initial 1,000 and outcomes 900/1,200 equally likely versus sure 1,020, expect φ*=2.6667. Keep lo=max(lower bounds), hi=min(upper bounds). Flag lo>hi.
  - **Bias and control.** Functional-form and stake bias. A one-year mean–variance threshold is conditional on the hypothetical stake and comprehension. Test whether rankings change with a different stake or a matched utility model; avoid transporting a band with unstable rankings to client wealth.
- [x] **2.2.4** Implement core routing, threshold probes inside uncertain intervals, paired loss comparisons and conditional follow-ups. Test a planned sale motivated by an upcoming expense versus discomfort after a decline. Check termination and replay after correcting an answer.
  - **Procedure.** Trace the common path then choose a probe with a threshold inside the unresolved interval. After a decline explore liquidity, discomfort and market belief separately. Cap risk probes at two under the initial design.
  - **Verification and failure handling.** Run routes covering a passed practice, no eligible probe, all eligible triggers and an early stop. Compare event log to expected sequence and final branch reason.
  - **Bias and control.** Adaptive exposure bias. Freeze routing rules and log eligible probes including those skipped. Describe simulated reachability only. Deterministic routing cannot establish the behavioral effect of receiving a probe.
- [x] **2.2.5** Show tolerance range, capacity, reserve, conflicts, exclusions and monitoring preference. Keep behavioral observations descriptive. Check that a demographic label or stated return target alone cannot raise the risk limit.
  - **Procedure.** Generate four report sections from distinct fields: model-compatible tolerance, funding capacity, confirmed behavior and strength of evidence. Present desired and required return separately.
  - **Verification and failure handling.** Change age or self-description with all financial facts and choices fixed. Inspect any changed allocation eligibility and remove unjustified dependence.
  - **Bias and control.** Circular validation. Behavioral or demographic annotations can explain a conflict; never train a tolerance label on its own score or count the same response twice.
  - **Client review.** Label the one-year tolerance range as a theoretical model output. Offer correction of misunderstood choices or funding facts. When the range is unresolved, show compatible alternatives and explain the missing evidence. Preserve confirmed liquidity constraints throughout.

- [x] **2.2.6** Propagate approximate amounts through capacity calculations. Check whether a single uncertain trade-off changes the band or options by omitting it in turn. Test near-indifference, an accidental swipe, conflicting choices and an unanswered probe. Clarify within the route limit when consequential, otherwise retain the range. Verify the interface distinguishes reported ranges, model-compatible bounds and statistically calibrated confidence intervals.
  - **Procedure.** Omit each trade-off once and recompute the interval and feasible options. Distinguish sensitivity to a single card from participant-sampling variability. Test CHF 10–15k uncertain withdrawal on CHF 50k capital.
  - **Verification and failure handling.** Expect CHF 35–40k investable absent other claims. Record whether clarification changes an action. Keep uncertain classification visible if it does.
  - **Bias and control.** Unstable classifications. Report the union of feasible bands from leave-one-answer-out sensitivity and the actual actions that differ. Label this as sensitivity, separate from a sampling interval.

### 2.3 Justify the questions and test the routes

The [simulation](research/questionnaire_validation/SIMULATION.md) reached 60/60 cards in 480 synthetic interviews. The [question-by-question rationale](questions/QUESTIONNAIRE_DESIGN.md#how-to-interpret-hypothetical-answers-in-the-report) covers the seven core families and their clarifications.

**Evidence to retain:** synthetic route table and theoretical interpretation of the card families. **Course reading:** [Guide Ultime Chapitre 17](Theory/Methodology/Chapter_Guides_00-34/Guide_Ultime_Chapitre_17.md) · [Guide Ultime Chapitre 18](Theory/Methodology/Chapter_Guides_00-34/Guide_Ultime_Chapitre_18.md).

- [x] **2.3.1** First simulate complete, uncertain, contradictory and aborted routes with fixed seeds. Verify scoring independence from display side, held-out answers and future answers.
  - **Procedure.** Generate seeded coherent, inconsistent, indifferent and pass-heavy participants. Vary presentation order and gesture polarity. Count coverage of every intended branch.
  - **Verification and failure handling.** Separate structural reachability from human prevalence. Fail if held-out choices update the score or a repeat event updates it twice.
  - **Bias and control.** Simulator confirmation bias. Generate stress routes outside the scoring model: habitual yes, random responses, stake-dependent choices and genuine indifference. Report unresolved rate under each.
- [x] **2.3.2** Justify each question family using an actual card, a possible response, a competing explanation and its permitted effect on the profile. Ground design decisions in published research where applicable.
  - **Verification.** Notebook 2.3.2 replays a sale driven by liquidity, discomfort or market expectations. All three preserve the same numerical tolerance evidence. The matched loss pairs invite clarification and a pass adds no directional bound.
  - [x] Document all 60 cards, answer polarity, scoring bounds, conditional follow-ups and worked client possibilities in the [card-by-card guide](questions/GUIDE_DES_CARTES.md). Notebook 2.3.2 checks the inventory and the illustrative rankings.
  - **Scope.** The course deliverable uses fictional responses and deterministic checks. Frequency of behaviors, time taken and prediction of real decisions are unmeasured.

## 3. Collect and prepare point-in-time data

### 3.1 Establish a source catalogue

Completed 22 November 2026. The [source register and study decisions](research/source_catalogue/README.md) link 115 study inputs, comparators and requirements to 843 raw snapshots. The offline fixture checks six manual rows and rejects an unfunded withdrawal. Source-specific research and execution limits remain visible in the register.

**Evidence to retain:** series catalogue and immutable raw manifest. **Course reading:** [Guide Ultime Chapitre 08](Theory/Methodology/Chapter_Guides_00-34/Guide_Ultime_Chapitre_08.md) · [W6 Financial Statements Analysis](Theory/Course_Notes/W6_Financial_Statements_Analysis.md).

#### Acquisition and reconciliation sheet for 3.1.1–3.2.5

Use the [local import inventory](data/README_data.md) to separate available files from outstanding study requirements. Record vintage, access, rights and decision-date coverage for each branch. The public-data fixture can exercise the pipeline before vendor access is available.

| Study / source to investigate | Grain and requested fields | Preparation and admission control |
|---|---|---|
| H01/H02/H07 and benchmarks · authorized total-return provider or fund issuer | Instrument/session: stable ID, venue, close, currency, distributions, split factor, adjusted or total-return level, inception and termination. For bonds distinguish fund returns from yield changes. | Resolve venue sessions, base currency and distribution convention. Preserve dead securities when studying a historical opportunity set. Reconcile a known distribution and split against the issuer. |
| H03/H04 · FRED, ALFRED and original statistical releases | Series/vintage/observation: curve (e.g. T10Y2Y), credit spread (BAA10Y), VIXCLS, CPIAUCSL, UNRATE, INDPRO; rate level versus change, seasonal adjustment, release date and vintage bounds. | Retain initial releases and revisions separately. Derive year-on-year inflation only after enough released history. If release time is ambiguous lag conservatively; run vintage versus latest-revised sensitivity and label the latter retrospective. |
| Cash and spending currency · central bank or FRED | DTB3 is a US discount-basis bill quote; DEXSZUS quotes CHF per USD. Select a defensible CHF cash benchmark separately. Record quote convention, tenor, maturity date, fixing and calendar. | For a bill of face 1, discount quote d in decimals and D days, price=1−dD/360 and holding return=1/price−1. State interpolation/roll assumption or label annual-rate/day-count conversion as a proxy. Never use a US cash rate as CHF cash by default. |
| H05 · WRDS CRSP, Compustat and historical CCM | Security-month PERMNO/PERMCO, returns, delisting, price, shares, venue/share code; GVKEY, fiscal end, filing availability, book equity inputs, revenue, COGS, total assets; link dates/types and point-in-time industry. | Define exchange breakpoints, share classes, market cap units, accounting lag/restatements and delist conventions per dataset release. Keep firm-months together. Verify link uniqueness and report attrition across filters. |
| H05 · academic factor library | Market excess, SMB, HML, profitability, investment, momentum and cash as needed, monthly region/currency and units. H04 valuation data require dated numerator and denominator. | Align factors and forward return months explicitly. Convert percentage files to decimals once. Store model (CAPM/FF3/FF5 + momentum), input vintage and common sample. |
| H06 · authorized course StockTwits archive | Message or aggregate grain, timestamp/zone, asset identifier, polarity, count, event definition; market returns and dated company/sector links. | Drop duplicate IDs with an audit trail. Retain neutral and no-message days separately. Estimate pre-event market model, log coverage, avoid labels determined after trade time. |
| H03 exploratory materials and policy | Gold, oil or copper spot/total-return distinction, real yields and broad dollar; optional FOMC text with release timestamp/version. | Spot series can be predictors. A tradable commodity sleeve needs an investable returns series and documented roll/carry; separate explanation, forecast and execution. |
| H07 / monitoring · transaction inputs | Instrument/date: bid/ask or spread proxy, commissions, FX fee, settlement, liquidity flags, closing calendar and quote age. | If a spread is modeled, label scenarios and estimate break-even. Keep annual fund charges already embedded in fund returns from being charged twice. |
| Questionnaire · synthetic fixtures | Generated route, card version, choice, branch, pass, correction and holdout. | Keep held-out answers outside scoring. Interpret counts under the specified generator only. |


- [x] **3.1.1** For each study separate tradable holdings, predictors, cash and benchmarks. Record provider, identifier, currency, frequency, units, adjustments, earliest reliable date, revision policy, access and display rights. Check equity, bond, cash, FX and optional commodity coverage against the mandate.
  - **Procedure.** Write series_catalogue with study_id, provider/table/field, instrument_id, geography, frequency, currency, adjustment, units, start/end, vintage, entitlement and role. Set a tradable comparator and cash series per currency.
  - **Verification and failure handling.** Report required versus actually retrieved fields for each H01–H07. Mark missing prerequisites and the affected conclusion.
  - **Bias and control.** Convenience universe. Record ex-ante eligibility and why each candidate asset/region is missing. Test conclusions on a broader or narrower dated set before generalizing.
- [x] **3.1.2** Inventory authorized price/FX series, FRED/ALFRED macro vintages, WRDS security/accounting links, course StockTwits events and prospective spread/fee inputs. Hash raw snapshots and record retrieval times. Verify hashes and row counts on reload.
  - **Procedure.** Prepare raw manifests with query parameters, source version, retrieval timestamp, hash, rows, date range and missing codes. Partition raw snapshots by provider and vintage. Use the acquisition table below.
  - **Verification and failure handling.** On reload verify hash and range. Quarantine changed snapshots and explain revisions. Never log credentials or assume an academic license permits display.
  - **Bias and control.** Backfill and revision. Record database entry time where available and quantify results with histories before entry removed. Keep original raw and revised extracts.
- [x] **3.1.3** Build fictional shareable fixtures alongside restricted local data. Document the rebuild commands and missing sources. Verify a clean public clone never needs restricted data for its smoke test.
  - **Procedure.** Build a deterministic fixture including a split, delisting, macro revision, missing close, currency conversion and withdrawal. Store expected values independently of the pipeline.
  - **Verification and failure handling.** Run without network or private inputs. Compare recomputed tables to manual expected rows. Label synthetic outputs in every notebook figure.
  - **Bias and control.** Toy-data optimism. Include at least one deliberately failing fixture. Mark statistics on synthetic paths as software checks only.

- [x] **3.1.4** Inspect the supplied local data pack and reconcile the benchmark return panel. Evidence: [import report](data/README_data.md) and [read-only verification script](research/verify_import.py). This scoped check covers receipt, selected hashes, coverage and return identities. Source rights, research replication and point-in-time suitability remain in the individual open tasks.
  - **Bias and control.** An imported table can reproduce an earlier error. Raw-to-prepared ETF returns were independently reconciled; the provenance, publication timing and construction of the WRDS panel require separate tests.

### 3.2 Clean without leaking tomorrow's information

Completed 22 November 2026. The [cleaning record](research/cleaning/README.md), [versioned panels](data/prepared_v1/) and notebook 3.2 preserve timing, exceptions, study-by-study coverage and blocked uses. The release supports historical research under its stated conventions. No verified accounting-based H05 ranking or actual trade fills are available.

**Evidence to retain:** prepared panel, join attrition and exceptions. **Course reading:** [Guide Ultime Chapitre 01](Theory/Methodology/Chapter_Guides_00-34/Guide_Ultime_Chapitre_01.md) · [guide tris portefeuille asset growth](Theory/Course_Notes/guide_tris_portefeuille_asset_growth.md).

- [x] **3.2.1** Normalize calendars, time zones, quote direction and identifiers. Enforce one dated key per record. Audit stale and missing prices, duplicates, suspicious jumps and exclusions by asset and year. Reconcile flagged outliers to source events.
  - **Procedure.** Use venue-specific session calendars. Key prices by instrument, session and vendor vintage. Report NaN counts, duplicate keys, stale runs and median/MAD extreme-return flags by asset-year.
  - **Verification and failure handling.** Inspect flags against corporate actions and sources. Keep raw and corrected values with reason codes. Do not drop a crash or forward-fill a tradable quote by default.
  - **Bias and control.** Non-synchronous closes. Compare common-close cutoffs and one-session lead/lag sensitivity across venues. Stale or filled prices can depress variance and apparent correlation; report the changes.
- [x] **3.2.2** Separate observation, publication, availability and execution. Use backward as-of joins and effective-dated company links. Inject a later revision and after-close release and verify earlier signals stay identical.
  - **Procedure.** Retain observation_date, published_at, available_at, decision_at and execution_at. Join using pandas.merge_asof backward or DuckDB ASOF JOIN on available_at. Resolve same-timestamp ordering from market convention.
  - **Verification and failure handling.** Inject a later revision and an after-close release. Assert earlier features and weights remain identical. Without intraday release timing, delay to a documented later eligible decision.
  - **Bias and control.** Same-day look-ahead. Align timestamps in UTC with source zone and DST preserved; a same-date join needs positive evidence the release preceded the decision.
  - **Restated and backfilled market histories.** Rebuild decision-date features from as-received snapshots or documented vendor vintages. Include a future split or a corrected close in a mutation test: an old absolute-price filter or trade size must not change. For retrospective adjusted prices verify the return convention separately from executable historical prices. Restrict claims when only the latest history exists.
- [x] **3.2.3** Reconcile splits, dividends, delisting returns, security entry/exit and cash-rate conventions. Check one corporate action by hand, verify client-currency returns multiplicatively and count attrition before/after joins.
  - **Procedure.** Record price type and cash distributions. For legacy separate CRSP return/delisting fields combine (1+RET)(1+DLRET)−1 when both apply. Verify provider version before combining. Translate via (1+r_local)(1+r_FX)−1.
  - **Verification and failure handling.** Audit one split, distribution, delisting, reversed FX quote and holiday by hand. Investigate unexplained gross/total divergence. Keep cash approximation error separate from trading alpha.
  - **Bias and control.** Unrecorded delisting returns and fund fees. Quantify missing terminal returns and run documented adverse-exit scenarios. Reconcile gross versus net index/fund conventions.
- [x] **3.2.4** Verify publication timing of fundamentals, macro revisions and sector classifications. Quantify unmatched and ambiguous firm-days. Restrict a signal to descriptive analysis if availability cannot be established.
  - **Procedure.** Join PERMNO–GVKEY via dated CCM validity and documented link priorities. Match filings by release availability, including restatement vintage, and sector by both effective and known dates.
  - **Verification and failure handling.** Count unmatched, ambiguous and unknown-publication rows per year/sector. Restrict conclusions to dated coverage and rerun without ambiguous matches. Current sector labels cannot backfill history.
  - **Bias and control.** Selective linkage. Compare covered and excluded firm sizes, sectors and returns by calendar year. If coverage is selective, report the estimand for the linked sample only.
- [x] **3.2.5** Freeze common trading dates, warm-up, eligible assets and missing-data rules per comparison. Write versioned Parquet tables, coverage and exception reports. Test that a missing execution quote triggers the specified fallback.
  - **Procedure.** Export vintage-keyed prices, returns, factors, macro releases, features, eligible universe and cost panels. Keep dynamic membership, each model warm-up and paired evaluation dates in sample_manifest.
  - **Verification and failure handling.** Compare pre/post-filter counts and results on full eligible versus paired samples. A common sample formed from survivors at the final date fails review.
  - **Bias and control.** Complete-case bias. Report each method's eligible dates, paired dates, failure dates and investable fallback path. Gains on the intersection alone are insufficient for adoption.

## 4. Describe historical returns and macro exposures

### 4.1 Produce descriptive evidence

**Completed evidence:** [measurement protocol, results and reproduction](research/descriptive/README.md) · [tables and figures](research/descriptive/results/). **Course reading:** [EMiF Class2 Version Ultra Pedagogique fixed](Theory/Course_Notes/EMiF_Class2_Version_Ultra_Pedagogique_fixed.md) · [Guide Ultime Chapitre 05](Theory/Methodology/Chapter_Guides_00-34/Guide_Ultime_Chapitre_05.md).

- [x] **4.1.1** Calculate simple, log, excess and compounded returns with explicit calendar and currency. Compare manual one-period and multi-period examples to code. Plot wealth and asset coverage together.
  - **Procedure.** Use r=P_TR,t/P_TR,t−1−1, log1p(r), cumulative wealth Π(1+r), excess r−r_f. Document return currency, timestamps and cash convention. Compute annual growth from actual elapsed years.
  - **Verification and failure handling.** Hand-check a two-period +10%, −10% path ends at 0.99 of initial capital. Report calendar gaps, missing and total-loss observations separately.
  - **Bias and control.** Arithmetic/geometric confusion. Show arithmetic mean and realized CAGR with units, fees and exact sample dates; use compounded cash flows for wealth.
- [x] **4.1.2** Compute annualized volatility, drawdown depth/duration, rolling correlations, historical VaR and Expected Shortfall. Record tail counts, ties and interval uncertainty. Test a flat path and a known loss path.
  - **Procedure.** Using positive losses, estimate VaR as the chosen empirical quantile and ES as the average worst tail mass with fractional boundary weight. Plot running drawdown W/max(W)−1 and recovery duration. For annual volatility disclose serial-dependence assumptions.
  - **Verification and failure handling.** Backtest time-ordered VaR exceptions, exact binomial counts under independence and clustering diagnostics. Report uncertainty with blocks, insufficient tail size and ongoing unrecovered drawdowns.
  - **Bias and control.** Sparse and dependent tails. Report quantile convention, number of independent episodes, breach clustering and interval uncertainty. For joint VaR/ES comparisons preregister a consistent joint score with matching return/loss sign and domain.
  - **Tail calibration and annualization.** At frozen one-step VaR origins report predicted versus actual breach counts. Use Kupiec unconditional coverage and Christoffersen independence/conditional coverage when exception and transition counts support inference. Otherwise show counts, sparse transitions and dependence-aware uncertainty. For covariance-stationary additive returns use Var(sum of h returns)=hγ₀+2Σ(h−k)γₖ for k=1…h−1. Compare the IID square-root-of-time shortcut with autocovariance sensitivity; compounded simple returns require pathwise compounding.
- [x] **4.1.3** Attribute portfolio variance and marginal risk to holdings. Check covariance symmetry, eigenvalues and conditioning. Verify contributions sum to total risk and examine sensitivity to the estimation window.
  - **Procedure.** Compute σp=√(w′Σw), RCᵢ=wᵢ(Σw)ᵢ/σp and effective holdings 1/Σwᵢ² for fully invested long-only positions. Inspect correlation heatmaps, eigenvalues and condition number.
  - **Verification and failure handling.** Check ΣRCᵢ=σp; identical assets give diversification ratio one. Diagnose singularity before solving. Preserve negative hedging contributions.
  - **Bias and control.** Noise in diversification estimates. Cross-check risk contributions across windows and joint resamples. When volatility is near zero or covariance indefinite, flag attribution as undefined or unreliable.

### 4.2 Explain reactions to shocks

**Completed evidence:** [dated exposures, common shocks and historical episodes](research/shocks/README.md). **Course reading:** [W3 Economic Analysis Guide FR](Theory/Course_Notes/W3_Economic_Analysis_Guide_FR.md) · [Guide Ultime Chapitre 12](Theory/Methodology/Chapter_Guides_00-34/Guide_Ultime_Chapitre_12.md).

- [x] **4.2.1** Specify common rate, equity, inflation and FX shocks. Estimate sensitivities using dated exposures with assumptions stated. Apply identical shocks across allocations and reconcile holding contributions to the portfolio effect.
  - **Procedure.** For fixed income use −modified duration × Δyield plus ½ convexity × Δyield² when inputs exist. For other assets estimate dated factor exposures and apply an explicit vector of market, FX or inflation shocks.
  - **Verification and failure handling.** Sum holding-level P&L to portfolio P&L. Test bp-to-decimal conversion and cash sensitivity. Distinguish residual risk from explained shock loss.
  - **Bias and control.** Double-counted macro channels. Separate direct FX repricing from local-asset exposures. Validate combined scenario versus a joint revaluation, and report interaction residuals.
- [x] **4.2.2** Compare calm and stressed samples, historical episodes and hypothetical scenarios. Report observation counts, exposure instability and confounding. Label any association requiring separate predictive or causal evidence.
  - **Procedure.** Define crisis windows and identification assumptions before comparing outcomes. Estimate rolling exposures with uncertainty. For regime models use filtered probabilities available at t.
  - **Verification and failure handling.** Compare common dates and counts. Run leave-one-crisis-out sensitivity. A shock association alone cannot support a causal or predictive claim.
  - **Bias and control.** Ex-post regime selection. Predefine episodes and run leave-one-episode-out comparisons. For a regime strategy archive filtered probabilities and compare with an unconditional policy.

## 5. Replicate research and validate forecasts

### 5.1 Run each registered experiment

- [x] Extend all seven studies using course methods and external sources. Record a research use, active reference and decision gate for each signal. Recheck publication timing, trading costs and sensitivity to individual instruments. [Seven-study report](research/robustness/README.md) · [Signal register](research/robustness/results/signal_register.csv).

**Historical evidence:** [seven-study replay and admission decisions](research/experiments/README.md) · [forecasts, holdings and diagnostics](research/experiments/results/). H05 remains open for verified filing dates. H02 follows the registered GARCH eligibility and deferral rules. **Course reading:** [Guide Ultime Chapitre 01](Theory/Methodology/Chapter_Guides_00-34/Guide_Ultime_Chapitre_01.md) · [literature](Theory/Course_Notes/literature.md).

- [x] **5.1.1 · H01** Compare sample and Ledoit–Wolf covariance at identical weights using NumPy/scikit-learn. Score future integrated variance (QLIKE), check conditioning, then rerun optimization and measure weight stability and net utility.
  - **Procedure.** Fit sample covariance and sklearn LedoitWolf to the same trailing past returns. At frozen weights aggregate predicted daily variance to next month's integrated variance. Realized proxy Σdaily(w′r_d)² with a declared centering convention. Compare QLIKE(v,y)=log(v)+y/v.
  - **Verification and failure handling.** Require positive v and identical units/dates. Report paired loss difference, matrix conditioning, weight dispersion and net utility after re-optimization. Attribute forecast and allocation effects separately.
  - **Study sources.** [QARM2 LN3 Cours Explique copie 2](Theory/Quant_Project/QARM2_LN3_Cours_Explique%20copie%202.md) · [EMiF Class11 Version Ultra Pedagogique fixed](Theory/Course_Notes/EMiF_Class11_Version_Ultra_Pedagogique_fixed.md).
  - **Bias and control.** Target mismatch. Summed daily conditional variance measures integrated variance, while variance of a cumulative return may include autocovariances. Freeze the target and weights for the entire measurement. Check the sklearn shrinkage target against the replicated paper specification.
  - **Dynamic dependence as a conditional challenger.** Use DCC-GARCH only after checking the individual variance fits, standardized residuals, convergence and positive-definite H_t=D_t R_t D_t. Compare rolling, shrinkage and dynamic covariance at the same information cutoff, fixed weights and evaluation dates. Record fallback performance and whether the extra model changes after-cost allocations.
- [x] **5.1.2 · H02** Compare rolling variance, EWMA and GARCH-t with GJR sensitivity using arch. Check convergence, persistence, Ljung–Box and ARCH-LM on standardized residuals. Match forecast and realized variance horizons. Test dynamic exposure separately after costs.
  - **Procedure.** Fit rolling baseline, EWMA and arch GARCH(1,1)-t: h_t=ω+αε²_(t−1)+βh_(t−1). Add GJR asymmetry as a registered variant. Refit only at admissible origins. Sum daily conditional variance forecasts over common horizon.
  - **Verification and failure handling.** Check positivity, fit convergence, finite innovation variance and persistence. Inspect standardized residuals and their squares via Ljung–Box, then ARCH-LM. Compare QLIKE and block intervals. Fall back to EWMA when fit fails; report failure frequency.
  - **Study sources.** [EMiF Classe9 ARCH GARCH fixed](Theory/Course_Notes/EMiF_Classe9_ARCH_GARCH_fixed.md) · [EMiF Classe10 GARCH fixed](Theory/Course_Notes/EMiF_Classe10_GARCH_fixed.md).
  - **Bias and control.** Failed-fit selection. Keep every forecast origin, optimizer warning and benchmark fallback. Score both paired successful fits and the full deployed rule. For Student-t check degrees of freedom >2 before variance interpretations.
- [x] **5.1.3 · H03** Compare a yield-curve bond forecast with lagged macro factors learned by PCA inside training. For VAR or local projections justify lags, stability, shock identification and interval construction. Treat gold/rates and resources/sectors as exploratory until separately confirmed.
  - **Procedure.** Forecast next-month excess bond return using released curve slope as baseline. Within training scale and fit macro PCA, then augment baseline. For VAR use information criteria inside training, check roots, residual autocorrelation and ordering sensitivity. For local projections define shock, controls and horizon-specific HAC.
  - **Verification and failure handling.** Compare paired squared errors and out-of-sample R² on vintage-consistent dates. For impulse responses report identification assumptions and bootstrap bands. Treat exploratory real-rate/gold and resource/sector tests as separate hypotheses.
  - **Study sources.** [EMIF Class5-6 Version Ultra Pedagogique fixed](Theory/Course_Notes/EMIF_Class5-6_Version_Ultra_Pedagogique_fixed.md) · [W3 FED Cours Complet](Theory/Course_Notes/W3_FED_Cours_Complet.md).
  - **Bias and control.** Generated factors and identification. Refit scaling, PCA, lag selection and regression within every resampled training block. Apply alternative VAR orderings or external identification; mark responses sensitive to ordering as scenario evidence.
- [x] **5.1.4 · H04** Compare expanding historical mean, OLS and ridge for forward equity excess return. Tune on internal chronological folds. Report out-of-sample R² and paired losses. Apply Clark–West only for suitable nested squared-error forecasts.
  - **Procedure.** Refit expanding mean, lagged OLS and inner-tuned ridge at each origin. Compute R²_OS=1−Σe_model²/Σe_mean². For persistent predictors simulate the null with dependence retained; evaluate whether apparent fit is common under no predictability.
  - **Verification and failure handling.** Use Clark–West only for appropriate nested squared-error forecasts, paired dependence-aware tests for eligible alternatives. Report negative R², sensitivity to start date and after-cost effect.
  - **Study sources.** [guide predictibilite agregee marche](Theory/Course_Notes/guide_predictibilite_agregee_marche.md) · [Advanced Data Analytics Lecture4 Regression Explique](Theory/Course_Notes/Advanced_Data_Analytics_Lecture4_Regression_Explique.md).
  - **Bias and control.** Persistent predictors and small-sample optimism. Simulate joint predictor/return innovations under no predictability, preserving persistence and innovation correlation. Rerun the selection pipeline and compare observed forecast gain with its null distribution.
- [ ] **5.1.5 · H05** Use DuckDB/WRDS to construct lagged value, profitability, asset growth and 12–1 momentum. Compare dated sorts, elastic net and boosting on whole-month blocks. Test Spearman rank correlation, factor alpha, microcap sensitivity and the net investable long-only sleeve.
  - **Historical status.** The price-only 12–1 component is measured on 84 months. Four published portfolio sorts and one dated Apple filing now supply external diagnostics. No cross-sectional month yet meets the individual-stock gate. Learned stock ranks, net sleeve and alpha remain unscored. [Diagnostic](research/experiments/results/price_only_component.csv) · [Excluded origins](research/experiments/results/stock_eligibility.parquet).
  - **Procedure.** Within month form dated book-to-market, gross profitability, asset growth and 12–1 momentum. Declare accounting definitions, NYSE breakpoints, share-class and microcap rules. Compare simple sort, elastic net and boosting with whole months held together.
  - **Verification and failure handling.** Report Spearman rank IC per month, equal/value-weighted quantile spreads, long-only return and factor alpha with HAC. Rerun ex-microcaps, with estimated spread costs and dated industry controls. A diagnostic short leg needs separate borrow assumptions to be investable.
  - **Study sources.** [guide tris portefeuille asset growth](Theory/Course_Notes/guide_tris_portefeuille_asset_growth.md) · [guide modeles factoriels capm fama french](Theory/Course_Notes/guide_modeles_factoriels_capm_fama_french.md).
  - **Bias and control.** Errors in estimated betas and false factor discovery. If two-pass premia use estimated exposures, bootstrap both passes by month or justify a Shanken correction under its assumptions. For joint alpha testing check GRS sample size, nonsingularity and assumptions; otherwise use dependence-aware joint inference.
- [x] **5.1.6 · H06** Replicate the LN7 pre-event market model, volume peaks, cumulative abnormal returns and polarity. Control for overlapping events and available timestamps. Compare Black–Litterman with and without a view at matched tracking error, including no-signal dates.
  - **Follow-up evidence.** A continuous relative-polarity view improved historical utility by 0.000140 against the anchor at 10 bp. Validation was negative. The separate activity-based risk forecast also missed its admission threshold. [Decision and paired comparisons](research/sentiment_followup/README.md).
  - **Procedure.** Estimate pre-event market model outside the event window; AR_it=r_it−(α_i+β_i r_mt), CAR=sum AR. Align message polarity, volume peaks and first executable price; distinguish no messages from neutral polarity. Replicate LN7 rank comparison then account for coincident dates.
  - **Verification and failure handling.** Freeze P (view exposures), Q (expected excess view return), Ω (uncertainty) and prior before execution. With Ω large recover the no-view solution. Compare net utility under the same risk budget including no-signal months. Unknown publication dates block the predictive branch.
  - **Study sources.** [QARM2 LN4 Cours Explique copie 2](Theory/Quant_Project/QARM2_LN4_Cours_Explique%20copie%202.md) · [QARM2 LN7 Cours Explique copie 2](Theory/Quant_Project/QARM2_LN7_Cours_Explique%20copie%202.md).
  - **Bias and control.** Event-conditioned hindsight. Build placebo events matched on calendar, liquidity and prior message volume, preserving clusters. Compare event-window results with pre-event diagnostics; exclude labels assigned after decision time from the signal.
- [x] **5.1.7 · H07** Run identical signals through monthly, quarterly and no-trade-band policies on drifted holdings. Compare net wealth, turnover, risk drift, withdrawal coverage and break-even unit costs.
  - **Procedure.** Apply monthly, quarterly and band rules to the same signals and cash flows with drifted weights. Use currency amounts traded for costing. Find unit-cost break-even by re-running the funded ledger over a cost grid.
  - **Verification and failure handling.** Report paired net difference, risk-limit breaches, overdue withdrawals and hold dates. If no sign change occurs disclose no crossing in the tested grid.
  - **Study sources.** [guide couts transaction trading](Theory/Course_Notes/guide_couts_transaction_trading.md) · [Guide Ultime Chapitre 06](Theory/Methodology/Chapter_Guides_00-34/Guide_Ultime_Chapitre_06.md).
  - **Bias and control.** Policy tuning bias. Select a band on inner validation only. Compare on common post-selection dates and report near-optimal bands, turnover and funding outcomes when the chosen threshold shifts.

### 5.2 Apply econometric and forecast controls

**Historical evidence:** [dated forecasts](research/experiments/results/forecasts.parquet) · [calibration](research/experiments/results/interval_calibration.csv) · [paired comparisons](research/experiments/results/paired_comparisons.csv). Independent evaluation is pending under the registered calendar. **Course reading:** [EMiF Classe7 Version Ultra Pedagogique fixed](Theory/Course_Notes/EMiF_Classe7_Version_Ultra_Pedagogique_fixed.md) · [EMIF Class5-6 Version Ultra Pedagogique fixed](Theory/Course_Notes/EMIF_Class5-6_Version_Ultra_Pedagogique_fixed.md) · [Advanced Data Analytics Lecture11 DimReduction Explique](Theory/Course_Notes/Advanced_Data_Analytics_Lecture11_DimReduction_Explique.md) · [Guide Ultime Chapitre 17](Theory/Methodology/Chapter_Guides_00-34/Guide_Ultime_Chapitre_17.md).

- [x] **5.2.1** Inspect ACF/PACF, trends, outliers, dependence and breaks. Select applicable ADF/KPSS specifications, HAC or clustered inference. For integrated systems test cointegration before VECM. For panels justify fixed effects or Fama–MacBeth and corresponding inference.
  - **Procedure.** Follow guide 01 from population and variable to specification, estimation and residuals. ADF null is unit root; KPSS null is stationarity. Specify constant/trend and lag choices. For panels consider firm/month effects and dependence along both dimensions. For factor premia run monthly cross-sections then time-series inference on premia.
  - **Verification and failure handling.** Conflicting stationarity results trigger break and transformation sensitivity. For integrated systems test Johansen rank with deterministic terms before VECM. Document sample loss, residual plots, serial dependence and heteroskedasticity before interpreting coefficients.
  - **Bias and control.** Misspecification and endogeneity. Review residual plots, influence by date/firm and plausible omitted channels. Test alternate trend/lag choices on development; use predictive language in the absence of identified exogenous variation.
- [x] **5.2.2** Fit scaling, imputation, PCA, feature selection and tuning inside each training window. Purge overlapping labels where required, retain all firms from one month in the same fold, and perturb future observations to detect leakage.
  - **Procedure.** Create rolling origins and nested inner splits. Fit sklearn Pipeline imputation, StandardScaler, PCA and hyperparameter search using inner training only. Exclude training labels whose end overlaps validation/test. Use filtered regimes only.
  - **Verification and failure handling.** Check train/validation/test timestamp inequalities and rerun after changing held-out values. Hyperparameters, past transforms and decisions must be unaffected by later data.
  - **Bias and control.** Cross-fold contamination. Archive feature fit dates and each training label's availability, including publication gaps. Test prediction at the latest origin while its outcome is still unknown.
- [x] **5.2.3** Archive dated point/range forecasts by asset, horizon, currency and version. Score means by squared error, variance by QLIKE, quantiles by pinball loss. Report interval width, coverage, clustered exceedances and counts by regime.
  - **Procedure.** Log forecast origin, target end, model version, point forecast, lower/upper quantiles and realization. Pinball loss=(q−1[y<f])(y−f); for a central band report mean width and fraction inside. Use PIT/CRPS only for complete predictive distributions.
  - **Verification and failure handling.** Report sample counts, misses by side, consecutive misses and calibration by regime. Compare widths at similar coverage. Low coverage triggers recalibration on development or a broader fallback, never tuning on final test outcomes.
  - **Bias and control.** Calibration hidden by pooling. Evaluate interval coverage, width and separate upper/lower misses within prespecified subperiods using dependence-aware intervals. Keep thin groups unresolved.
  - **Horizon and fallback.** Record elicitation horizon, forecast horizon, decision date and cash-flow dates separately. Monthly signals support near-term review. Evaluate long-term funding with explicit paths, reinvestment, inflation, FX and withdrawals. Block direct repetition of a one-month premium over the goal horizon. When an overlay expires, fails timing checks or fails out-of-sample admission, use the frozen baseline or no-view mix, mark the reason and preserve the failed origin. A stale valuation feed suspends a trade proposal.
- [x] **5.2.4** Compare paired losses on identical dates with suitable long-run variance or block bootstrap. Record all variants and multiplicity. Retain simple fallback forecasts where gains are weak, unstable or too small after costs.
  - **Procedure.** Choose primary paired difference and economic threshold in advance. Use HAC or moving-block bootstrap of dated loss differentials, with horizon, block choice and sensitivity recorded. For multiple confirmatory variants declare family and e.g. Holm adjustment; record all attempts.
  - **Verification and failure handling.** Report effect, interval, sample size, rejected/retained hypotheses and net utility. Inconclusive results or a failed timing check keep the reference strategy in place.
  - **Bias and control.** Winner's curse. When selecting the best among many trading rules, use a joint block-resampled max-statistic or suitable SPA/Reality Check against the common benchmark. Center under the null and resample identical dates jointly across alternatives. Retain the multiplicity register and independent confirmation.
  - **Overlapping forecast losses.** For suitable non-nested forecasts, use Diebold–Mariano on paired d_t=L_candidate−L_reference with HAC long-run variance. Document target horizon, overlap, lag bandwidth, refitting scheme and small-sample sensitivity. If the differential has zero long-run variance, too few independent origins, or nesting invalidates the reference distribution, report the paired effect and its limitations; use the registered nested-model procedure when justified.
  - **Forecast selection and combination.** For forecasts of the same target, currency and horizon at the same decision time, preregister a baseline, standalone candidates and an equal-weight forecast combination. If justified, compare nonnegative weights summing to one learned only from past out-of-fold forecasts and already available outcomes. Freeze the missing-component rule, compare paired forward losses and coverage on common origins, then evaluate the deployed rule across all origins. Check error dependence and incremental value against the baseline and individual forecasts. Retain the baseline, one model or a combination according to the frozen decision rule. Use explanatory-only signals for stress attribution. Require a separate after-cost benefit before changing allocation.

## 6. Build feasible portfolios and match a mandate

### 6.1 Estimate the constrained net frontier

**Completed evidence:** [funded frontier, historical comparison and sensitivity](research/frontier/README.md) · [dated grid](research/frontier/results/frontiers.csv) · [mandate exceptions](research/frontier/results/mandate_cases.csv). **Course reading:** [QARM2 LN1 Cours Explique copie 2](Theory/Quant_Project/QARM2_LN1_Cours_Explique%20copie%202.md) · [QARM2 LN5 Cours Explique copie 2](Theory/Quant_Project/QARM2_LN5_Cours_Explique%20copie%202.md) · [QARM2 LN6 Cours Explique copie 2](Theory/Quant_Project/QARM2_LN6_Cours_Explique%20copie%202.md).

- [x] **6.1.1** Apply liquidity, reserves, ethical exclusions, concentration and currency restrictions before optimization. Define feasible cash and risky sleeves. Test empty eligible universe, all-cash and infeasible-risk cases.
  - **Procedure.** Create dated eligibility matrix by mandate and instrument (liquidity, exclusions, currency, limits, withdrawal funding). Run a feasibility problem before maximizing return.
  - **Verification and failure handling.** Report binding constraints and uncovered amounts. An empty sleeve or impossible target yields an explicit status; never relax a hard exclusion silently.
  - **Bias and control.** Dated eligibility and infeasible reserves. Verify exclusions and look-through exposures as of each decision. Unknown holdings or unsettled proceeds may invalidate an option; show an unresolved constraint explicitly.
- [x] **6.1.2** Compare equal weight, fixed mix, constrained minimum variance, risk parity and conditional strategies on identical inputs. Check equal risk contributions in a known diagonal case and recovery of the Black–Litterman prior with negligible view confidence.
  - **Procedure.** Use equal weight and fixed mix controls, GMV and ERC (RCᵢ/σp=bᵢ); conditional BL prior π=δΣw_market in excess-return units. For LN2 compute beta=cov(p,m)/var(m), tracking error=sd(r_p−r_b).
  - **Verification and failure handling.** Analytically verify inverse-vol ERC under diagonal Σ, zero tracking error versus self, no-view BL and diversification ratio. Report benchmarks that lack a defensible prior.
  - **Bias and control.** Benchmark shopping. Freeze admissible controls before optimization. For an expanded universe test incremental opportunity by constrained out-of-sample spanning or matched-frontier comparison at common risk budgets after costs.
  - **Fair comparator.** Before looking at returns define an implementable fixed mix and a rule for ineligible holdings or a binding risk cap. Freeze the mandate including reserve, currency, exclusions, fees, execution, cash flows and start holdings across arms. If a fixed mix violates a hard cap, apply its prespecified risk reduction or flag it infeasible. Rerun mismatched comparisons before interpreting gains.
- [x] **6.1.3** Sweep risk budgets with CVXPY or SciPy. Estimate net expected return under explicit trade, spread and FX conventions. Save solver status, residuals, binding constraints and dominated candidates. Validate on a hand-computable two-asset case.
  - **Procedure.** For each cap s solve max μ′w−cost(Δw) subject to w′Σw≤s², budget and mandate constraints. Define financing of first trade and horizon of recurring costs. Use CVXPY and record primal residuals, feasibility and solver tolerances.
  - **Verification and failure handling.** Compare with analytic two-asset GMV and direct grid enumeration. Reject materially infeasible weights and dominated points on common net/currency assumptions. Label solver failures separately from economically infeasible caps.
  - **Bias and control.** Hidden financing in proportional fees. Express trades and budget in common pre-trade wealth units; positions plus reserve/cash plus one-time costs must equal wealth. Validate the initial purchase and the drifted rebalance independently.
  - **Dual verification (guide 00, §0D.3.4).** For a convex feasible instance record the cap convention (volatility or variance), units, primal residual, dual multiplier and solver status. At a smooth active cap perturb the same right-hand side in both directions and compare the objective slope with the reported multiplier. Repeat with a smaller step and an inactive cap. At a kink use one-sided slopes. This is local sensitivity to a constraint, not a forecast.
- [x] **6.1.4** Perturb means, covariances, fees and constraints and resample blocks. Report weight and frontier dispersion. Flag rankings that flip under plausible inputs.
  - **Procedure.** Use moving blocks of return vectors shared across all assets, then re-estimate means/covariance and reoptimize. Compare sampling sensitivity with deterministic fee and cap scenarios.
  - **Verification and failure handling.** Report weight intervals, turnover, rank changes and constraint breaches including failed draws. An unstable frontier is shown as uncertain.
  - **Bias and control.** Conditional-on-success frontiers. Publish number of infeasible/failed draws at each risk cap and denominator of reported percentiles. Compare changing weights and changing feasible set separately.
  - **Classical versus robust frontier (guide 04, §4.5.9).** At common risk budgets compare fixed mix, classical max net mean and robust max net mean minus ρ√(w′Vμw). Use Σ for risk and Vμ for uncertainty of the estimated horizon mean. Estimate Vμ from mean vectors obtained by jointly resampling blocks of training dates; record block length, horizon conversion, number of draws and PSD diagnostics. Freeze the radius or its inner-fold selection rule before evaluation. Equal holdings, execution timing, funded costs and hard constraints apply to both optimization arms. Recover the nominal objective at ρ=0; compare weights only for a unique optimum.

### 6.2 Present defensible client options

**Completed evidence:** [client options, risk preferences and dated shortfalls](research/options/README.md) · [eight eligible options at both risk limits](research/options/results/options.csv) · [funding scenarios](research/options/results/goal_scenarios.csv). **Course reading:** [Guide Ultime Chapitre 16](Theory/Methodology/Chapter_Guides_00-34/Guide_Ultime_Chapitre_16.md) · [Guide Ultime Chapitre 34](Theory/Methodology/Chapter_Guides_00-34/Guide_Ultime_Chapitre_34.md).

- [x] **6.2.1** Evaluate net mean–variance utility over the plausible phi interval with consistent horizon and decimal units. Compare Sharpe against matching currency cash. Test an unresolved interval, tied alternatives and sensitivity to capacity.
  - **Procedure.** Evaluate Uφ=μnet−φσ²/2 at both endpoints per pair of portfolios; differences are affine in φ. Compute internal crossover 2Δμ/Δvariance when defined. Match annual units and currency to the elicitation.
  - **Verification and failure handling.** Report robust winner, crossover, ties or unresolved. For zero excess-return volatility mark Sharpe undefined. An unbounded/unreliable φ interval cannot justify a precise personal ranking.
  - **Bias and control.** Sleeve/household utility mismatch. Define the wealth base for returns, risk and elicited φ. With deterministic reserve and risky fraction a, total excess mean scales by a and variance by a². Recompute rankings at both bases and test transfer of elicited preferences before personalized ranking.
- [x] **6.2.2** Display historical outcome, forecast range, shock loss, liquidity, fees and goal shortfall for each eligible option. Explain whether a longer horizon, more savings or a revised target closes a gap. Verify a desired return cannot override a hard constraint.
  - **Procedure.** Translate each admissible allocation into investable capital, dated loss scenario, modeled fee, funding path and return range. Separate observed history, future scenario and realized prospective outcomes.
  - **Verification and failure handling.** Recalculate an example independently in spending currency. Report any goal gap and compare adjustments to contributions, horizon or target at the same capacity.
  - **Bias and control.** False precision in long-horizon goals. Simulate dated cash flows with resampled joint returns and FX, protect required withdrawals at their due dates, and vary inflation and sequence of returns. Report both frequency and size of funding shortfalls with assumptions.
  - **Unmodeled joint tail losses.** Start with empirical joint stress and block-resampled asset/FX paths at the withdrawal date. If the decision is sensitive to losses beyond the sample, register peaks-over-threshold/GPD as a sensitivity, check threshold and shape stability, exceedance clustering and uncertainty. A t-copula extension requires dated marginal fits, residual dependence diagnostics and comparison with empirical joint losses. With sparse extremes present scenario losses and sampling limits. Never convert a hypothetical stress into a probability without calibration.
  - **Reverse withdrawal stress (guide 05, §5.13.3).** At the due date compute available cash plus saleable positions after FX, settlement and modeled fees. Start with the unacceptable event (available resources below amount due) and find the boundary along a specified shock path. Report exact coverage at equality, a pre-existing shortfall, or no reachable shortfall separately. Compare CHF 15,000 fully reserved against a larger or earlier payment. For joint shocks disclose how distance and feasibility are defined. The boundary carries no probability by itself.
  - **Client display.** Separate dated historical results, conditional monthly ranges and multi-year funding scenarios. Compare only feasible alternatives. When utility rankings flip across plausible tolerance or model inputs, present the trade-off and allow the client to choose. Use a practical-equivalence label only if the prespecified margin and uncertainty support it; a wide interval leads to an inconclusive label.

## 7. Backtest and decide catalogue admission

### 7.1 Replay realistic transactions

**Implementation and evidence.** [Funded execution replay](research/execution/README.md).

**Evidence to retain:** order, fill, cash and cost ledgers. **Course reading:** [guide couts transaction trading](Theory/Course_Notes/guide_couts_transaction_trading.md) · [Guide Ultime Chapitre 06](Theory/Methodology/Chapter_Guides_00-34/Guide_Ultime_Chapitre_06.md).

- [x] **7.1.1** At every origin save eligible data, forecast, signal and intended order before the execution timestamp. Execute at the first eligible quote under the registered rule. Verify a next-close order earns no return before its fill.
  - **Procedure.** Create decision and fill tables with origin, data cutoff, intended weights, quote, executable timestamp, fill status and first holding interval. Store orders before outcome evaluation.
  - **Verification and failure handling.** Move every post-decision observation and verify past orders are invariant. Check a next-close buy manually and a skipped fill with unchanged units.
  - **Bias and control.** Unfillable signals. Simulate a missed or partial fill and an unavailable quote. Report attempted versus filled orders and delay. No profit accrues on unfilled units.
- [x] **7.1.2** Maintain shares, cash, FX, reserves, external flows and costs. Charge on amounts traded from drifted weights. Reconcile gross and net wealth against hand examples for initial purchase, no trade, sale and withdrawal.
  - **Procedure.** Ledger identities: wealth=cash+Σunits×price×FX; cash_after=cash_before+external_flow−Σsigned_trade_value−fees. Estimate half-spread on gross traded notional; report one-way turnover convention separately. Use bid/ask fills or spread model once.
  - **Verification and failure handling.** Reconcile each fill to currency rounding tolerance, cash availability and fees. Compare zero-cost, positive-cost, no-trade and restricted-liquidity withdrawal paths.
  - **Bias and control.** Double counting spread, management fees or FX. Compare mid-plus-explicit-cost and bid/ask fill ledgers on a known trade. Record embedded versus additional charges per instrument.
  - **Liquidity and implementation bias.** Compare planned trade notional with observable lagged volume, timestamped spread and settlement. When available, report decision-to-fill implementation shortfall and opportunity cost on unfilled amounts. If only closing prices exist, stress participation limits, slippage and partial fills and label costs modeled. Archive the wealth/withdrawal sensitivity, including unfilled orders.
- [x] **7.1.3** Compare buy-and-hold and simple rebalancing over the same dates. Stress costs, calendars, crises, estimation windows and missed trades. Report net wealth, drawdown, turnover, risk breaches and withdrawal shortfalls.
  - **Procedure.** Run a walk-forward panel of strategies, comparisons and cost levels on matching dates. Stress warm-up, FX, execution lag, spread widening and missed trades with prespecified variants.
  - **Verification and failure handling.** Report paired terminal wealth, annualized return, max drawdown, ES, turnover, cash shortfall and breach duration. A result that reverses under plausible cost or date choices is flagged.
  - **Bias and control.** Path dependence. Keep the same return paths and cash flows across strategies and include an adverse ordering before withdrawal. Report the difference between terminal wealth and cash available on the exact due date.

### 7.2 Decide what may reach the application

**Implementation and evidence.** [Signed demonstration catalogue](research/catalogue/README.md).

**Evidence to retain:** study disposition and signed catalogue version. **Course reading:** [Guide Ultime Chapitre 22](Theory/Methodology/Chapter_Guides_00-34/Guide_Ultime_Chapitre_22.md) · [Guide Ultime Chapitre 30](Theory/Methodology/Chapter_Guides_00-34/Guide_Ultime_Chapitre_30.md).

- [x] **7.2.1** Review frozen out-of-sample results against the registered economic threshold and paired uncertainty. Label retrospective results. Record retain, reject or descriptive-only for every study with a reason.
  - **Procedure.** Compare paired net outcome and its block interval with the predeclared minimum useful gain and admissibility constraints. Distinguish development, retrospective and genuinely prospective evidence.
  - **Verification and failure handling.** Produce one retain/reject/inconclusive record per variant including failures and reasons. Do not reuse the final period after changing a rule.
  - **Bias and control.** Absence-of-evidence error. Compare the interval with the material-gain threshold. Claim practical equivalence only with prespecified equivalence margins and suitable interval/test; wide uncertainty remains inconclusive.
  - **Paired client-value test (guides 01 V18 and 04 §4.15.5).** Register one primary horizon, φ range, economic gain threshold and fallback before outcomes. Archive both frontiers and weights at each common origin. Compare net mean–variance scores on realized returns with the same household wealth base and horizon as φ. Recompute mean and variance per strategy inside each paired date-block draw. Report Δscore and intervals, turnover, costs, risk breaches and uncovered cash at due dates. Label this as mean–variance utility; an exact certainty equivalent requires a specified utility and inversion. Display dated estimated frontiers on common axes and realized comparisons in a separate table. Show sensitivity across prespecified windows, covariance estimators and fee levels. Record inconclusive results and keep the simpler benchmark when evidence is insufficient.
  - **Allocation experiment.** Keep the mandate and permitted information fixed; compare fixed mix, classical and robust frontiers over the same origins. Evaluate paired net utility, shortfall at withdrawal, breaches and turnover. With fictional mandates label results as conditional on those mandates. Retain the admissible baseline if the improvement is too small or inconclusive. Record questionnaire validation separately.
- [x] **7.2.2** Independently reproduce admitted catalogue entries, costs and mandate screens. Attach as-of date, uncertainty, fallback and data permissions. Check that a failed study cannot silently enter a recommendation.
  - **Procedure.** Freeze catalogue rows with study version, eligible mandate class, currency, date, benchmark, fee assumptions, forecast expiry, permissions and fallback. Rebuild from immutable source IDs.
  - **Verification and failure handling.** Have a reviewer rerun a selected row and a rejected row. Only approved, unexpired records pass the app eligibility query.
  - **Bias and control.** Selective promotion. Include rejected and expired entries with reason codes. Verify that changing the candidate cannot inherit a prior candidate's holdout status.

## 8. Monitor and review in the web app

### 8.1 Value the selected allocation

**Implementation and evidence.** [Local fictional portfolio monitor](research/monitor/README.md).

**Evidence to retain:** holdings snapshot and valuation reconciliation. **Course reading:** [Guide Ultime Chapitre 07](Theory/Methodology/Chapter_Guides_00-34/Guide_Ultime_Chapitre_07.md) · [Guide Ultime Chapitre 26](Theory/Methodology/Chapter_Guides_00-34/Guide_Ultime_Chapitre_26.md).

- [x] **8.1.1** Persist confirmed mandate, allocation, units, cash, model version and selection date. Connect an authorized close/FX feed with timestamps, refresh policy and stale-data handling. Test missing, delayed and corrected quotes.
  - **Procedure.** Use versioned holdings and append-only close/FX observations, provider timestamp, retrieval time, calendar and correction lineage. Store model and consent versions at selection.
  - **Verification and failure handling.** Test missing market day versus holiday, stale FX with fresh asset prices and vendor correction. Display last reliable valuation and withhold actionable proposals on stale inputs.
  - **Bias and control.** Feed survivorship and revision. Preserve as-received and subsequently corrected valuations. Report unavailable valuation days and elapsed quote age.
- [x] **8.1.2** Chart total value, flows, net time-weighted performance, drawdown, drift and goal progress. Show last refresh and distinguish projections. Test that a withdrawal reduces value without creating a fictitious investment loss.
  - **Procedure.** For end-period cash flow F compute subperiod return (V_end−F)/V_start−1, chain subperiods for TWR. Split at actual flows when timestamps allow. Document timing assumptions where unavailable.
  - **Verification and failure handling.** Use a zero-market-return withdrawal and a deposit during a price move. Reconcile chart change into market P&L, FX, fees and external flows.
  - **Bias and control.** Cash-flow timing bias. Reconcile a same-day deposit before versus after a price change; disclose when only end-of-day flows permit an approximation.

### 8.2 Decide whether to rebalance

**Implementation and evidence.** [Confirmed reviews and shadow holdings](research/monitor/README.md).

**Evidence to retain:** hold/trade comparison and confirmation events. **Course reading:** [Guide Ultime Chapitre 21](Theory/Methodology/Chapter_Guides_00-34/Guide_Ultime_Chapitre_21.md) · [guide couts transaction trading](Theory/Course_Notes/guide_couts_transaction_trading.md).

- [x] **8.2.1** Trigger review after material drift, changed risk, a due expense or a revised mandate. Compare hold versus trade on identical assumptions. Show turnover, costs, liquidity and expected effect on the goal.
  - **Procedure.** Run hold and proposed trade from identical current holdings, timestamps, cash forecasts and costs. Estimate post-trade risk drift and net change in withdrawal coverage.
  - **Verification and failure handling.** Compare accepted, declined and hold outcomes without attributing selection effects to the intervention. Allow hold when benefit is within estimation or cost uncertainty.
  - **Bias and control.** Self-selection into trades. Compute a dated shadow hold path for every eligible proposal with identical flows and executable prices. Describe acceptance-conditioned outcomes separately; attribution to the intervention needs a credible comparison design.
  - **Hold or trade.** Freeze the materiality margin, costs and uncertainty rule before testing. For a discretionary rebalance, keep the current eligible allocation if the paired net benefit is inconclusive. A new hard constraint or withdrawal triggers a funding review even if expected return barely changes; show the least disruptive feasible correction, or the uncovered amount if none exists. Request confirmation.
- [x] **8.2.2** Require explicit client confirmation and log declines, holds and accepted changes. Suspend proposals on stale inputs. Test double confirmation, inability to sell, settlement delay and insufficient liquidity.
  - **Procedure.** Persist review ID, mandate version and decision before applying one simulated trade. Treat repeated confirmations idempotently and revalue if the quote or mandate changes.
  - **Verification and failure handling.** Test duplicate confirmation, expired proposal, delayed settlement and insufficient available cash. Reconcile the final units to a single confirmed execution.
  - **Bias and control.** Repeated-action bias. Report unique proposals, stale expiries, declines and duplicate confirmations. Trace one decision to one execution or a documented no-trade outcome.

## 9. Verify, present and release

### 9.1 Demonstrate the complete workflow

**Implementation and evidence.** [Course release and client pitch](research/release/README.md).

**Evidence to retain:** release evidence and client pitch trace. **Course reading:** [Guide Ultime Chapitre 07](Theory/Methodology/Chapter_Guides_00-34/Guide_Ultime_Chapitre_07.md) · [Guide Ultime Chapitre 30](Theory/Methodology/Chapter_Guides_00-34/Guide_Ultime_Chapitre_30.md).

- [x] **9.1.1** Run unit, integration and mobile/desktop browser checks. Exercise uncertain profile, infeasible goal, missing private files, stale feeds and the full confirmed journey. Store commands, outcomes and known limitations.
  - **Procedure.** Create end-to-end fixtures linking participant events, mandate, as-of market snapshot, order and dashboard. Run pytest plus mobile/desktop browser smoke tests with a documented seed.
  - **Verification and failure handling.** Save expected/actual amounts and screenshots of uncertain, infeasible and stale states. A skipped integration test stays explicitly unverified.
  - **Bias and control.** Happy-path testing. Include failed imports, timeouts and incomplete profiles in test denominators. Allocate independent fixtures to developer tests and acceptance tests.
  - **Counterfactual acceptance.** Replay one confirmed mandate twice: change only tolerance, then only withdrawal date. Fail release if tolerance moves reserves or a due-date change skips liquidity review. Also simulate a failed signal, a stale valuation and near-tied options; verify the fallback, suspension and unresolved-choice displays respectively.
- [ ] **9.1.2** Reproduce public examples in a fresh clone. Review source/display rights, consent, sensitive profile storage, deletion and secrets. Verify only intended demo inputs are distributed.
  - **Procedure.** Create a redistributable input manifest, environment lock, run command and permissions table covering data, course texts and participant records. Test synthetic route in a network-free checkout.
  - **Verification and failure handling.** Compare expected hashes/metrics. Check exports for private fields and verify deletion on a synthetic participant.
  - **Bias and control.** Irreproducible provenance. Compare a fresh-clone input/version manifest to the approved one. Record private components the public reviewer cannot reproduce.
  - [x] The synthetic-only package was reproduced from a fresh remote checkout. Distribution rights for archives already tracked in the public research repository remain open.
- [ ] **9.1.3** Prepare the 15-minute client pitch around one mandate, two feasible alternatives or a documented shortfall, and a dated review. Cross-check figures against the notebook, course requirements against 1.1.1 and release decisions against the journal.
  - **Procedure.** Trace each reported number to study ID, sample dates, fee convention and notebook output. Use a client scenario to demonstrate uncertainty and a dated review decision.
  - **Verification and failure handling.** Rehearse to the course time limit. Have a second reader reproduce one slide number and identify where the scenario could fail.
  - **Bias and control.** Presentation cherry-picking. Choose the demo scenario before inspecting its performance and show a failure or infeasible case alongside it. Trace every headline result to its full denominator.

  - [x] The seven-slide pitch, timed script and independent numerical checks are complete. A second human reader and live questions remain unverified.

## Quantitative tool selection before the course presentation

| Decision | First comparison | Conditional extension and evidence needed |
|---|---|---|
| Elicit a preference · 2.2–2.3 | Common anchors, threshold intervals, hypothetical responses and simulated routes | Describe competing explanations and check the permitted change to the profile. |
| Estimate a risk budget · H01/H02 | Historical covariance, shrinkage, EWMA and common-weight realized variance | GARCH-t/GJR and DCC need calibrated forecasts and an improvement after costs. [Guide 04, §4.4.7](Theory/Methodology/Chapter_Guides_00-34/Guide_Ultime_Chapitre_04.md) |
| Explain and forecast macro effects · H03/H04 | Dated stress, historical mean, lagged regression and training-only PCA | VAR/VECM, local projections and ridge require suitable time-series properties and independent forecast origins. Compare paired losses under the appropriate hypothesis. [Guide 01, V4](Theory/Methodology/Chapter_Guides_00-34/Guide_Ultime_Chapitre_01.md) |
| Estimate investable signals · H05/H06 | Dated sorts and factor controls; market-model event study and no-view BL | Elastic net, boosting or a BL view must improve an investable sleeve after costs and survive timing, coverage and multiplicity checks. |
| Protect a dated withdrawal · 4.1/6.2 | Historical drawdowns, ES, joint stress and dated cash shortfalls | VaR coverage tests, EVT and copulas need enough independent observations and calibrated dependence. [Guide 05, §§5.5.12 and 5.5.15](Theory/Methodology/Chapter_Guides_00-34/Guide_Ultime_Chapitre_05.md) |
| Choose and review an allocation · 6–8 | Constrained net frontier, simple benchmarks, risk contributions, funded ledger and hold comparison | Evaluate spanning, stability and execution shortfall only under matched constraints, costs and observed liquidity. |

Record each method as planned, run, infeasible or deferred with reason, input vintage, comparator and effect on the client decision. The course demonstration prioritizes an interactive constrained frontier and sensitivity to a client constraint. Additional methods depend on the registered question and evidence.

## Reading index for the local theory corpus

The 104 Markdown sources below are indexed by decision. The two QARM sets are retained under their supplied paths. Research extensions need a registered decision, suitable dated data and a simple comparator before adoption.

| Source | Relevant use in this project |
|---|---|
| [Portfolio-Management-explications copie.md](Theory/CFA/Portfolio-Management-explications%20copie.md) | Investor mandate and behavioral interpretation · 2 |
| [Advanced_Data_Analytics_Cours_Explique.md](Theory/Course_Notes/Advanced_Data_Analytics_Cours_Explique.md) | Research design and course synthesis · 1.2 |
| [Advanced_Data_Analytics_Lecture10_GPR_Explique.md](Theory/Course_Notes/Advanced_Data_Analytics_Lecture10_GPR_Explique.md) | Conditional nonlinear forecast benchmark · 5.2 |
| [Advanced_Data_Analytics_Lecture11_DimReduction_Explique.md](Theory/Course_Notes/Advanced_Data_Analytics_Lecture11_DimReduction_Explique.md) | Train-only PCA · H03 |
| [Advanced_Data_Analytics_Lecture12_Clustering_Explique.md](Theory/Course_Notes/Advanced_Data_Analytics_Lecture12_Clustering_Explique.md) | Exploratory regimes fitted on training data · 4.2 |
| [Advanced_Data_Analytics_Lecture13_RL_Explique.md](Theory/Course_Notes/Advanced_Data_Analytics_Lecture13_RL_Explique.md) | Deferred sequential policy extension requiring credible execution simulator · H07 |
| [Advanced_Data_Analytics_Lecture14_WrapUp_Explique.md](Theory/Course_Notes/Advanced_Data_Analytics_Lecture14_WrapUp_Explique.md) | Research design and course synthesis · 1.2 |
| [Advanced_Data_Analytics_Lecture3_Explique.md](Theory/Course_Notes/Advanced_Data_Analytics_Lecture3_Explique.md) | Git and reproducible Python · 1.1 |
| [Advanced_Data_Analytics_Lecture4_Regression_Explique.md](Theory/Course_Notes/Advanced_Data_Analytics_Lecture4_Regression_Explique.md) | Train-only model fitting and tuning · H04/H05 |
| [Advanced_Data_Analytics_Lecture6_Classification_Explique.md](Theory/Course_Notes/Advanced_Data_Analytics_Lecture6_Classification_Explique.md) | Train-only model fitting and tuning · H04/H05 |
| [Advanced_Data_Analytics_Lecture7_DeepLearning_Explique.md](Theory/Course_Notes/Advanced_Data_Analytics_Lecture7_DeepLearning_Explique.md) | Conditional challenger requiring enough independent dates · 5.2 |
| [Advanced_Data_Analytics_Lecture8_Sequences_Explique.md](Theory/Course_Notes/Advanced_Data_Analytics_Lecture8_Sequences_Explique.md) | Conditional challenger requiring enough independent dates · 5.2 |
| [Advanced_Data_Analytics_Lecture9_PINNs_Explique.md](Theory/Course_Notes/Advanced_Data_Analytics_Lecture9_PINNs_Explique.md) | Conditional PDE pricing extension only with a derivative valuation target |
| [EMIF_Class4_Version_Ultra_Pedagogique_fixed.md](Theory/Course_Notes/EMIF_Class4_Version_Ultra_Pedagogique_fixed.md) | Stationarity, lags and systems · 5.2 |
| [EMIF_Class5-6_Version_Ultra_Pedagogique_fixed.md](Theory/Course_Notes/EMIF_Class5-6_Version_Ultra_Pedagogique_fixed.md) | Stationarity, lags and systems · 5.2 |
| [EMiF_Class11_Version_Ultra_Pedagogique_fixed.md](Theory/Course_Notes/EMiF_Class11_Version_Ultra_Pedagogique_fixed.md) | Conditional variance and dependence · H01/H02 |
| [EMiF_Class1_Version_Ultra_Pedagogique_fixed.md](Theory/Course_Notes/EMiF_Class1_Version_Ultra_Pedagogique_fixed.md) | Return units and empirical dependence · 4.1 |
| [EMiF_Class2_Version_Ultra_Pedagogique_fixed.md](Theory/Course_Notes/EMiF_Class2_Version_Ultra_Pedagogique_fixed.md) | Return units and empirical dependence · 4.1 |
| [EMiF_Class3_Notes_fixed.md](Theory/Course_Notes/EMiF_Class3_Notes_fixed.md) | Cross-sectional and factor inference · H05 |
| [EMiF_Classe10_GARCH_fixed.md](Theory/Course_Notes/EMiF_Classe10_GARCH_fixed.md) | Conditional variance and dependence · H01/H02 |
| [EMiF_Classe12_Version_Ultra_Pedagogique_fixed.md](Theory/Course_Notes/EMiF_Classe12_Version_Ultra_Pedagogique_fixed.md) | Conditional breaks and nonlinear regimes · 4.2/5.2 |
| [EMiF_Classe13_Version_Ultra_Pedagogique_fixed.md](Theory/Course_Notes/EMiF_Classe13_Version_Ultra_Pedagogique_fixed.md) | Conditional breaks and nonlinear regimes · 4.2/5.2 |
| [EMiF_Classe7_Version_Ultra_Pedagogique_fixed.md](Theory/Course_Notes/EMiF_Classe7_Version_Ultra_Pedagogique_fixed.md) | Stationarity, lags and systems · 5.2 |
| [EMiF_Classe9_ARCH_GARCH_fixed.md](Theory/Course_Notes/EMiF_Classe9_ARCH_GARCH_fixed.md) | Conditional variance and dependence · H01/H02 |
| [EMiF_Cours8_Version_Ultra_Pedagogique_fixed.md](Theory/Course_Notes/EMiF_Cours8_Version_Ultra_Pedagogique_fixed.md) | Valuation and return forecasting · H04 |
| [QARM2_LN1_Cours_Explique.md](Theory/Course_Notes/QARM2_LN1_Cours_Explique.md) | Frontier · 6.1 |
| [QARM2_LN2_Cours_Explique.md](Theory/Course_Notes/QARM2_LN2_Cours_Explique.md) | Market beta and relative risk · 6.1 |
| [QARM2_LN3_Cours_Explique.md](Theory/Course_Notes/QARM2_LN3_Cours_Explique.md) | Estimation instability · H01 |
| [QARM2_LN4_Cours_Explique.md](Theory/Course_Notes/QARM2_LN4_Cours_Explique.md) | Prior and subjective views · H06 |
| [QARM2_LN5_Cours_Explique.md](Theory/Course_Notes/QARM2_LN5_Cours_Explique.md) | Risk contributions · 6.1 |
| [QARM2_LN6_Cours_Explique.md](Theory/Course_Notes/QARM2_LN6_Cours_Explique.md) | Diversification measures · 6.1 |
| [QARM2_LN7_Cours_Explique.md](Theory/Course_Notes/QARM2_LN7_Cours_Explique.md) | Event studies and text signals · H06 |
| [SAAM_W11_Guide_Pedagogique.md](Theory/Course_Notes/SAAM_W11_Guide_Pedagogique.md) | Eligibility and ESG coverage · 6.1 |
| [W10_Banking_ExternalFactors_Guide.md](Theory/Course_Notes/W10_Banking_ExternalFactors_Guide.md) | Conditional bank-sector transmission in rate shocks · 4.2/H03 |
| [W10_Banks_Guide_Pedagogique.md](Theory/Course_Notes/W10_Banks_Guide_Pedagogique.md) | Conditional bank-sector transmission in rate shocks · 4.2/H03 |
| [W13_Behavioral_Finance_Guide_FR.md](Theory/Course_Notes/W13_Behavioral_Finance_Guide_FR.md) | Investor mandate and behavioral interpretation · 2 |
| [W13_Course_Conclusions_Guide.md](Theory/Course_Notes/W13_Course_Conclusions_Guide.md) | Research design and course synthesis · 1.2 |
| [W1_Regulation_Guide_Pedagogique.md](Theory/Course_Notes/W1_Regulation_Guide_Pedagogique.md) | Rights, eligibility and regulatory scope · 1.1/9.1 |
| [W1_Regulatory_Analysis_Guide.md](Theory/Course_Notes/W1_Regulatory_Analysis_Guide.md) | Source/display restrictions and regulatory assumptions · 3.1/9.1 |
| [W2_Industry_Analysis_Guide.md](Theory/Course_Notes/W2_Industry_Analysis_Guide.md) | Industry, financial inputs or institutional eligibility · 3.1/H05 |
| [W2_Industry_Analysis_Guide_FR.md](Theory/Course_Notes/W2_Industry_Analysis_Guide_FR.md) | Industry, financial inputs or institutional eligibility · 3.1/H05 |
| [W3_Economic_Analysis_Guide_FR.md](Theory/Course_Notes/W3_Economic_Analysis_Guide_FR.md) | Macro drivers and scenario interpretation · H03 |
| [W3_FED_Cours_Complet.md](Theory/Course_Notes/W3_FED_Cours_Complet.md) | Macro drivers and scenario interpretation · H03 |
| [W3_geopolitique_cours_complet.md](Theory/Course_Notes/W3_geopolitique_cours_complet.md) | Macro drivers and scenario interpretation · H03 |
| [W4_MarketAnalysis_Guide.md](Theory/Course_Notes/W4_MarketAnalysis_Guide.md) | Macro drivers and scenario interpretation · H03 |
| [W4_Market_Analysis_Guide.md](Theory/Course_Notes/W4_Market_Analysis_Guide.md) | Macro drivers and scenario interpretation · H03 |
| [W4_Market_Analysis_Guide_Complet.md](Theory/Course_Notes/W4_Market_Analysis_Guide_Complet.md) | Macro drivers and scenario interpretation · H03 |
| [W5_ESG_Guide_Pedagogique.md](Theory/Course_Notes/W5_ESG_Guide_Pedagogique.md) | Eligibility and ESG coverage · 6.1 |
| [W5_SAAM_Governance_ESG_Regulation.md](Theory/Course_Notes/W5_SAAM_Governance_ESG_Regulation.md) | Eligibility and ESG coverage · 6.1 |
| [W5_SAAM_Sustainable_Analysis_Guide.md](Theory/Course_Notes/W5_SAAM_Sustainable_Analysis_Guide.md) | Eligibility and ESG coverage · 6.1 |
| [W6_Financial_Statements_Analysis.md](Theory/Course_Notes/W6_Financial_Statements_Analysis.md) | Industry, financial inputs or institutional eligibility · 3.1/H05 |
| [W6_Quality_of_Earnings_Guide.md](Theory/Course_Notes/W6_Quality_of_Earnings_Guide.md) | Industry, financial inputs or institutional eligibility · 3.1/H05 |
| [W7_Guide_Pedagogique.md](Theory/Course_Notes/W7_Guide_Pedagogique.md) | Industry, financial inputs or institutional eligibility · 3.1/H05 |
| [W8_Investment_Approaches_Guide.md](Theory/Course_Notes/W8_Investment_Approaches_Guide.md) | Conditional comparison of investment signals · 5.2 |
| [W8_Technical_Analysis_Guide.md](Theory/Course_Notes/W8_Technical_Analysis_Guide.md) | Conditional comparison of investment signals · 5.2 |
| [W9_Assurances_Guide_Pedagogique.md](Theory/Course_Notes/W9_Assurances_Guide_Pedagogique.md) | Conditional liability scenarios and cash timing · 2.1/4.2 |
| [W9_Pension_Funds_Guide_Pedagogique.md](Theory/Course_Notes/W9_Pension_Funds_Guide_Pedagogique.md) | Asset–liability mismatch and withdrawal horizon · 2.1/6.2 |
| [guide_couts_transaction_trading.md](Theory/Course_Notes/guide_couts_transaction_trading.md) | Implementation shortfall · H07 |
| [guide_modeles_factoriels_capm_fama_french.md](Theory/Course_Notes/guide_modeles_factoriels_capm_fama_french.md) | Cross-sectional and factor inference · H05 |
| [guide_predictibilite_agregee_marche.md](Theory/Course_Notes/guide_predictibilite_agregee_marche.md) | Valuation and return forecasting · H04 |
| [guide_tris_portefeuille_asset_growth.md](Theory/Course_Notes/guide_tris_portefeuille_asset_growth.md) | Cross-sectional and factor inference · H05 |
| [literature.md](Theory/Course_Notes/literature.md) | Research design and course synthesis · 1.2 |
| [Guide_Ultime_Chapitre_00.md](Theory/Methodology/Chapter_Guides_00-34/Guide_Ultime_Chapitre_00.md) | Numerical tolerances and dimensions · 1.2.3 |
| [Guide_Ultime_Chapitre_01.md](Theory/Methodology/Chapter_Guides_00-34/Guide_Ultime_Chapitre_01.md) | Identification, inference and out-of-sample checks · 5.2 |
| [Guide_Ultime_Chapitre_02.md](Theory/Methodology/Chapter_Guides_00-34/Guide_Ultime_Chapitre_02.md) | Risk premia and factor attribution · H05 |
| [Guide_Ultime_Chapitre_03.md](Theory/Methodology/Chapter_Guides_00-34/Guide_Ultime_Chapitre_03.md) | Discounting and rate sensitivity · 4.2 |
| [Guide_Ultime_Chapitre_04.md](Theory/Methodology/Chapter_Guides_00-34/Guide_Ultime_Chapitre_04.md) | Constrained frontier · 6.1 |
| [Guide_Ultime_Chapitre_05.md](Theory/Methodology/Chapter_Guides_00-34/Guide_Ultime_Chapitre_05.md) | Tail loss and stress · 4.1 |
| [Guide_Ultime_Chapitre_06.md](Theory/Methodology/Chapter_Guides_00-34/Guide_Ultime_Chapitre_06.md) | Costs and execution · 7.1 |
| [Guide_Ultime_Chapitre_07.md](Theory/Methodology/Chapter_Guides_00-34/Guide_Ultime_Chapitre_07.md) | Versioning and stale feeds · 8.1 |
| [Guide_Ultime_Chapitre_08.md](Theory/Methodology/Chapter_Guides_00-34/Guide_Ultime_Chapitre_08.md) | Source reliability · 3.1 |
| [Guide_Ultime_Chapitre_09.md](Theory/Methodology/Chapter_Guides_00-34/Guide_Ultime_Chapitre_09.md) | Sector comparability · H05 |
| [Guide_Ultime_Chapitre_10.md](Theory/Methodology/Chapter_Guides_00-34/Guide_Ultime_Chapitre_10.md) | Accounting timing and definitions · H05 |
| [Guide_Ultime_Chapitre_11.md](Theory/Methodology/Chapter_Guides_00-34/Guide_Ultime_Chapitre_11.md) | Asset-specific exposures · 4.2 |
| [Guide_Ultime_Chapitre_12.md](Theory/Methodology/Chapter_Guides_00-34/Guide_Ultime_Chapitre_12.md) | Macro transmission · H03 |
| [Guide_Ultime_Chapitre_13.md](Theory/Methodology/Chapter_Guides_00-34/Guide_Ultime_Chapitre_13.md) | Investability and index selection · 3.1 |
| [Guide_Ultime_Chapitre_14.md](Theory/Methodology/Chapter_Guides_00-34/Guide_Ultime_Chapitre_14.md) | Framing and reference points · 2.2 |
| [Guide_Ultime_Chapitre_15.md](Theory/Methodology/Chapter_Guides_00-34/Guide_Ultime_Chapitre_15.md) | Sustainability constraints · 6.1 |
| [Guide_Ultime_Chapitre_16.md](Theory/Methodology/Chapter_Guides_00-34/Guide_Ultime_Chapitre_16.md) | Utility under uncertainty · 6.2 |
| [Guide_Ultime_Chapitre_17.md](Theory/Methodology/Chapter_Guides_00-34/Guide_Ultime_Chapitre_17.md) | Forecast scoring and calibration · 5.2 |
| [Guide_Ultime_Chapitre_18.md](Theory/Methodology/Chapter_Guides_00-34/Guide_Ultime_Chapitre_18.md) | Noise and classification sensitivity · 2.2 |
| [Guide_Ultime_Chapitre_19.md](Theory/Methodology/Chapter_Guides_00-34/Guide_Ultime_Chapitre_19.md) | Conditional combination of views · H06 |
| [Guide_Ultime_Chapitre_20.md](Theory/Methodology/Chapter_Guides_00-34/Guide_Ultime_Chapitre_20.md) | Position sizing and constraints · 6.1 |
| [Guide_Ultime_Chapitre_21.md](Theory/Methodology/Chapter_Guides_00-34/Guide_Ultime_Chapitre_21.md) | Mandate review and consent · 8.2 |
| [Guide_Ultime_Chapitre_22.md](Theory/Methodology/Chapter_Guides_00-34/Guide_Ultime_Chapitre_22.md) | Decision audit · 7.2 |
| [Guide_Ultime_Chapitre_24.md](Theory/Methodology/Chapter_Guides_00-34/Guide_Ultime_Chapitre_24.md) | Optional strategy attribution · 4.2 |
| [Guide_Ultime_Chapitre_25.md](Theory/Methodology/Chapter_Guides_00-34/Guide_Ultime_Chapitre_25.md) | Conditional leverage/short feasibility · 6.1 |
| [Guide_Ultime_Chapitre_26.md](Theory/Methodology/Chapter_Guides_00-34/Guide_Ultime_Chapitre_26.md) | Valuation and cash reconciliation · 8.1 |
| [Guide_Ultime_Chapitre_27.md](Theory/Methodology/Chapter_Guides_00-34/Guide_Ultime_Chapitre_27.md) | Rights and disclosure review · 9.1 |
| [Guide_Ultime_Chapitre_28.md](Theory/Methodology/Chapter_Guides_00-34/Guide_Ultime_Chapitre_28.md) | Client explanation · 6.2 |
| [Guide_Ultime_Chapitre_29.md](Theory/Methodology/Chapter_Guides_00-34/Guide_Ultime_Chapitre_29.md) | Independent review and ownership · 1.1 |
| [Guide_Ultime_Chapitre_30.md](Theory/Methodology/Chapter_Guides_00-34/Guide_Ultime_Chapitre_30.md) | End-to-end reproduction · 9.1 |
| [Guide_Ultime_Chapitre_31.md](Theory/Methodology/Chapter_Guides_00-34/Guide_Ultime_Chapitre_31.md) | Industry mechanisms · H05 |
| [Guide_Ultime_Chapitre_32.md](Theory/Methodology/Chapter_Guides_00-34/Guide_Ultime_Chapitre_32.md) | Conditional geography or mandate restrictions · 6.1 |
| [Guide_Ultime_Chapitre_33.md](Theory/Methodology/Chapter_Guides_00-34/Guide_Ultime_Chapitre_33.md) | Conditional liability stress · 4.2 |
| [Guide_Ultime_Chapitre_34.md](Theory/Methodology/Chapter_Guides_00-34/Guide_Ultime_Chapitre_34.md) | Household cash reserve and horizon · 2.1 |
| [Sommaire.md](Theory/Methodology/Chapter_Guides_00-34/Sommaire.md) | Chapter navigation and decision map · 1.2 |
| [QARM2_LN1_Cours_Explique copie 2.md](Theory/Quant_Project/QARM2_LN1_Cours_Explique%20copie%202.md) | Frontier · 6.1 |
| [QARM2_LN2_Cours_Explique2 copie.md](Theory/Quant_Project/QARM2_LN2_Cours_Explique2%20copie.md) | Market beta and relative risk · 6.1 |
| [QARM2_LN3_Cours_Explique copie 2.md](Theory/Quant_Project/QARM2_LN3_Cours_Explique%20copie%202.md) | Estimation instability · H01 |
| [QARM2_LN4_Cours_Explique copie 2.md](Theory/Quant_Project/QARM2_LN4_Cours_Explique%20copie%202.md) | Prior and subjective views · H06 |
| [QARM2_LN5_Cours_Explique copie 2.md](Theory/Quant_Project/QARM2_LN5_Cours_Explique%20copie%202.md) | Risk contributions · 6.1 |
| [QARM2_LN6_Cours_Explique copie 2.md](Theory/Quant_Project/QARM2_LN6_Cours_Explique%20copie%202.md) | Diversification measures · 6.1 |
| [QARM2_LN7_Cours_Explique copie 2.md](Theory/Quant_Project/QARM2_LN7_Cours_Explique%20copie%202.md) | Event studies and text signals · H06 |
