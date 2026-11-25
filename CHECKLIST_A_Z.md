# Checklist A–Z — RiskMatch V3

Each work package progresses from notebook to shared engine to Web App. Check items only after evidence.

**Execution order:** follow the [dependency roadmap](docs/ROADMAP.md) and [prerequisite registry](docs/TASK_DEPENDENCIES.csv). Chapter numbers are stable navigation references, not mandatory execution order. Generic chapter checkboxes are closure criteria rather than individual tickets. All 75 catalog IDs are preserved.

Consolidation evidence (2026-11-25): [method specifications](docs/METHOD_SPECIFICATIONS.md), [API routes](docs/API_ROUTES.md) and [remaining blockers and numerical evidence](docs/CONSOLIDATION.md). 222/1230 identified tickets now closed. The four currently ready formal tickets concern rights, historical Treasury eligibility, behavioral human pilot and future multi-user authorization.

Client experience consolidation (2026-11-25): [client flow and coverage](docs/CLIENT_FLOW.md). Separate client and research navigation, visible objective selection within mandate, loading/retry states, catalog warming, server-version-aware restart and actual local handler smoke tests. Formal model/data approval gates remain unchanged.

Academic review (2026-11-25): [chapter-by-chapter review](docs/PROFESSOR_REVIEW.md). All 27 chapters have executed portable fixtures and local historical evidence cells. The generated local review notebook has 83 executed code cells and includes 63 successful in-process API requests, all 11 objective cases and four complete asset-level archive integrity checks. Formal tickets retain their prerequisite and acceptance status.

To display the next executable tasks: `.venv/bin/python scripts/task_dependencies.py --ready`.

## Setup and Organization

- [x] Restore the initial scaffold and original documentation.
- [x] Create the shared prototype, Web App and single notebook.
- [x] Initialize Git and create the dedicated GitHub repository (public per D002).
- [x] Define solo development, CI and collaboration policy (D003: enforce PR review and main protection before adding collaborators).
- [ ] Lock dependencies and document licenses.

## Usage and Traceability

This document preserves the requirements of the [original conversation](https://chatgpt.com/share/6b0551c6-2d38-83eb-b203-a2c1b260d522), adapted to the Treasury-only decision of 24 November 2026: no corporate credit, MBS, agencies, municipals or mixed bond ETFs. FAC11 Credit is replaced by Treasury Curve; the other 74 identities are unchanged. All 27 chapters remain in **one** [RiskMatch V3 notebook](notebooks/RiskMatch_V3.ipynb). Unchecked tasks are planned work, not existing features.

| Original Requirement | Chapters and Expected Evidence |
|---|---|
| Mandate, goals, risk aversion, constraints | 01–02, 12: validated mandate + explainable profile |
| US market, securities/Treasuries/futures, history | 03–06, 21–22: snapshots, sources, ledger |
| Analytics, models, strategies, allocation and improvement | 07–20: complete catalogs, tests, comparison |
| Metrics, costs, backtests, scenarios | 11, 23–24: net OOS metrics and results |
| Portfolio swipes and personalized choice | 25: filter, cards, shortlist, comparison, manual/optimized allocation across Matches |
| Portfolio management over time | 26: dynamic policies and monitoring |
| Notebook → local Web App and collaborative GitHub | 27: shared engine, UI, tests, CI, review |

### Validation Gates and Dependency Order

Each ID is a possible issue. To check it off, attach notebook reference (chapter/cell), function, test, run_id, UI evidence where applicable and PR. Unvalidated models remain experimental. Chapter order is pedagogical; the dependency gates determine release order.

- [x] **G00** — Reproducible installation, dedicated GitHub repository (public per D002) and CI; identical dependency versions on two machines.
  Closed in solo mode (D003): owner-confirmed green CI on c05aaee, local installation and notebook smoke, versioned contracts, exclusions and experiment registry. Configure collaborator write access, PR review and main protection before the first collaborator joins.
- [x] **G01** — Minimal mandate, specification of all 11 objectives (OBJ01–OBJ11), versioned discovery and protocol.
- [ ] **G02** — Validated US ETF universe, cash, benchmarks, licenses and PIT/total-return pipeline.
- [ ] **G03** — Statistics, covariance and baselines; minimum variance, maximum utility, maximum Sharpe and frontier with analytical tests.
- [ ] **G04** — Reconciled baseline ETF backtest, ledger, costs, leakage-free walk-forward, initial metrics and simple stress/Monte Carlo.
- [ ] **G05** — End-to-end RiskMatch prototype with baselines only; filter before swipe, comparison, paper confirmation.
- [ ] **G06** — Other ETF-compatible optimizers and strategies tested against baseline engine; no instrument or factor without verified data.
- [ ] **G07** — Individual securities, PIT factors, fundamentals, Treasuries and futures with cash flow and margin tests.
- [ ] **G08** — Financial catalog excluding dynamic management, multi-asset OOS validation, independent improvement then final matching.
- [ ] **G09** — Dynamic management, monitoring, paper trading and independent financial/behavioral/security review.

### Detailed Setup

- [x] **INFRA.01** — Verify Python, virtual environment, dependencies and reproducible versions.

  Evidence (2026-11-24, D001 approved): Python 3.12.6, isolated `.venv`, fresh install from `requirements.lock`, no broken requirements; local Python and JavaScript tests passed. Previous environment preserved as `.venv-legacy`. CI now targets Python 3.12; actual remote CI is INFRA.06. Notebook — Shared Setup / INFRA.01.

- [x] **INFRA.02** — Run INSTALL.command, START.command and STOP.command; check both local ports and logs.
  Local installer and health checks executed; web `/api/health` returned success and Jupyter `/lab` returned HTTP 302 after local runtime/proxy fixes. After the owner ran STOP.command, both ports no longer responded.
- [x] **INFRA.03** — Open RiskMatch_V3.ipynb and verify contents, Python kernel and executable cells.
  Notebook structure and local Python 3.12 kernel execution verified; eight synthetic cells executed successfully.
- [x] **INFRA.04** — Create a separate GitHub repository, initialize Git and check status and exclusions before commit (public per D002).
  Local `main` and remote `origin/main` confirmed at `c05aaee`; data exclusions checked. Owner approved public visibility for now, with restricted data kept local.
- [x] **INFRA.05** — Configure remote and solo workflow; require collaborator permissions, protected main and reviews before collaborative development.
  D003 approved: owner works alone for now; no collaborator invitations or main protection required in solo mode. Public read access does not grant write access.
- [x] **INFRA.06** — Check push CI in solo mode (PR CI before collaboration), test fresh installation and run tests.
  Fresh local install and tests passed, redesigned CI includes notebook smoke and privacy path checks. Owner reported green GitHub Actions on commit `c05aaee`.
- [x] **INFRA.07** — Define ticket/branch/commit naming, owner, dependencies and validation evidence.
  Conventions documented in CONTRIBUTING.md; owner is sole developer until collaboration begins.
- [x] **INFRA.08** — Create experiment registry and data/version conventions; prohibit secrets and private data in Git.
  docs/EXPERIMENT_REGISTRY.md and exclusion checker implemented.

### Shared Contracts, Minimal Backtest and First RiskMatch

- [x] **SYS.01** — Define GoalSpec, ForecastBundle, RiskReport, StrategySpec, OptimizerSpec and PortfolioCandidate separately; specify inputs/outputs, units and versions.
  Evidence: src/riskmatch/contracts.py, schema 1.0.0, architecture and synthetic notebook contract demo; no financial models validated.
- [x] **SYS.02** — Define eligibility registry by method: instrument, required data, capacity, leverage, margin, frequency and unavailable diagnostics.
  Evidence: src/riskmatch/eligibility.py, tests/unit/test_contracts.py; 64 catalog methods default to unavailable until independently validated. Requirements are conservative planning rules, not final financial eligibility.
- [ ] **UNIV.01** — Apply Treasury-only rule before allocation: classify issuer and type, verify PIT ETF holdings, reject corporate debt, MBS, agencies, municipals, foreign sovereigns, mixed ETFs and missing metadata; test acceptance/rejection.
- [ ] **EXT.01** — Revalidate coverage, liquidity, license, vintage and availability of extended security master (securities, Treasuries, futures, fundamentals); document strategies blocked by missing data.
- [ ] **BT00.01** — Define minimal ETF/cash ledger: trades, positions, fees, dividends/total return without double counting, NAV and flows.
- [ ] **BT00.02** — Implement delayed execution, commissions/spread, positions and NAV for cash, 1/N and 60/40 only.
- [ ] **BT00.03** — Reconcile an analytical two-asset, two-period case without fees, then with fees and contributions.
- [ ] **BT00.04** — Freeze chronological splits, calendar and common benchmark; test invariance to future data.
- [ ] **BT00.05** — Calculate initial net metrics, compare with benchmarks and export OOS report.
- [ ] **BT00.06** — Simulate ETF stress and simple deterministic paths, calculate shortfall/success probability and validate baseline engine.
- [ ] **MVP.01** — Produce baseline candidates with GoalSpec, constraints, net results and provenance; exclude incompatibilities.
- [ ] **MVP.02** — Present portfolio cards with consistent metrics, independent exploratory score and filter explanations.
- [ ] **MVP.03** — Test like/dislike/skip/undo, shortlist, benchmark comparison and paper confirmation.
- [ ] **MVP.04** — Validate the local Discovery → mandate → candidates → Explore → paper choice journey; preserve no-match option.
- [ ] **IMP.01** — Publish an improvement report separate from matching: references, ablations, costs, uncertainty and rejection criteria.
- [ ] **IMP.02** — Freeze the registry of actually validated eligible candidates and evidence before final selection.
- [ ] **MATCH.01** — Revalidate the final journey for eligible goals; preferences never change hard risk budgets.


## 01. Client Mandate

Notebook: [chapter 01](notebooks/RiskMatch_V3.ipynb#chapitre-01) · Guide chapter 1.

- [x] Study and formalize: Define ClientProfile, hard constraints, preferences and feasibility.
- [x] Document assumptions, formulas, data and units.
- [x] Run the notebook on a fixture and analyze errors.
- [x] Test analytical equivalence, edge cases and robustness.
- [x] Extract code into the shared module.
- [x] Write automated tests and make them pass.
- [x] Add the API contract and relevant screen.
- [ ] Verify local rendering and update documentation.
- [ ] Create a PR, obtain review and merge.

### 01 — A. Detailed Tasks


- [x] **CH01.01** — Define currency and amount types (USD/CHF; nominal vs real).
- [x] **CH01.02** — Define capital, investable wealth, assets, debts, emergency reserve and net worth as separate fields.
- [x] **CH01.03** — Collect income, spending, recurring contributions, withdrawals and dated liabilities.
- [x] **CH01.04** — Distinguish investment horizon from time until next withdrawal.
- [x] **CH01.05** — Represent each goal as amount, currency, due date, priority and shortfall penalty.
- [x] **CH01.06** — Calculate funding gap and required annual return for a single cash flow; solve dated multi-flow case numerically.
- [x] **CH01.07** — Separate ability, willingness and required risk; never infer capacity from behavioral choices.
- [x] **CH01.08** — Evaluate knowledge and experience separately for equities, Treasuries, futures, leverage and short selling.
- [x] **CH01.09** — Define limits on losses, stress, volatility, liquidity, asset/issuer/sector weights, turnover and costs.
- [x] **CH01.10** — Define ESG exclusions, tax assumptions, FX hedge preference, leverage, gross/net and derivatives permissions.
- [x] **CH01.11** — Represent hard vs soft constraints explicitly; define units, bounds and missing-value policy.
- [x] **CH01.12** — Implement feasibility report and conflicting constraint examples; never silently relax constraints.
- [x] **CH01.13** — Version ClientProfile and ConstraintSet; save synthetic examples and avoid real client data in notebooks.
- [x] **CH01.14** — Review risk-budget and goal changes in a before/after UI; require explicit confirmation.
- [x] **CH01.15** — Test zero capital, negative capital, inconsistent horizon, withdrawals exceeding resources, unsupported currency and missing consent.

Evidence (2026-11-24): [mandate specification](docs/CLIENT_MANDATE.md), notebook chapter 01 cell `2ce6b6ef`, `src/riskmatch/profiling/mandate.py`, `configs/mandate-example.json`, unit and loopback HTTP tests, bilingual form and confirmation tests in `tests/web/mandate.test.cjs`. Deterministic structural validation only; owner visual confirmation and GitHub publication remain pending. Objective-specific financial models, full market feasibility and suitability are later tickets. Assumptions are provisional pending owner review.



## 02. Behavioral Discovery

Notebook: [chapter 02](notebooks/RiskMatch_V3.ipynb#chapitre-02) · Guide chapter 20.

- [x] Study and formalize: Version cards, responses, coverage, score and sensitivity.
- [x] Document assumptions, formulas, data and units.
- [x] Run the notebook on a fixture and analyze errors.
- [x] Test analytical equivalence, edge cases and robustness.
- [x] Extract code into the shared module.
- [x] Write automated tests and make them pass.
- [x] Add the API contract and relevant screen.
- [ ] Verify local rendering and update documentation.
- [ ] Create a PR, obtain review and merge.

### 02 — A. Detailed Tasks


- [x] **CH02.01** — Define risk tolerance, loss sensitivity, time preference, ambiguity, confidence and decision consistency as distinct constructs.
- [x] **CH02.02** — Map expected utility, prospect theory, framing, loss aversion, anchoring and recency hypotheses to observable choices; do not claim diagnoses.
- [x] **CH02.03** — Build the initial 60-card bank: 16 lottery, 12 gain/loss, 12 trajectory, 8 uncertainty/horizon, 8 style, 4 coherence items.
- [x] **CH02.04** — Sample the 30-card session with 8/6/6/4/4/2 block quotas and deterministic seed.
- [x] **CH02.05** — Specify card IDs, versions, localized descriptions, choices, reference points, payoff/probabilities, scoring direction and pair IDs.
- [x] **CH02.06** — Write certainty-equivalent lottery pairs with known expected values and a clearly described safe alternative.
- [x] **CH02.07** — Create symmetric gain/loss framing pairs with economically equivalent payoffs.
- [x] **CH02.08** — Show drawdown trajectories with equal horizon, uncertainty, costs and no guaranteed recovery.
- [x] **CH02.09** — Separate ambiguity and time-preference items from the unidimensional score.
- [x] **CH02.10** — Randomize order and left/right placement while preserving balanced design; record presentation order.
- [x] **CH02.11** — Support like/dislike, unsure, skip, undo, accessible keyboard and touch gestures.
- [x] **CH02.12** — Compute prudent fraction p and score = round(1+29p); threshold provisional coverage of 70%.
- [x] **CH02.13** — Calculate missing-response sensitivity range and flag paired inconsistencies; display no score when coverage is insufficient.
- [x] **CH02.14** — Build simulated all-prudent/all-risk/mixed/missing/inconsistent response fixtures.
- [x] **CH02.15** — Implement separate CRRA utility and prospect-theory likelihood exploration; keep score 1–30 independent of lambda and gamma.
- [ ] **CH02.16** — Pre-register pilot protocol, consent, data minimization, withdrawal and retention; pilot 30–50 volunteers exploratorily.
  Draft protocol and local fictional consent/withdrawal implemented; external preregistration, reviewed workflow and real volunteers pending.
- [ ] **CH02.17** — Run cognitive interviews, readability/accessibility tests and timing/fatigue analysis (timing optional and never a direct excitation measure).
  Keyboard, touch and bilingual UI implemented; actual human interviews and accessibility/fatigue study pending.
- [ ] **CH02.18** — Analyze item difficulty, discrimination, test-retest reliability, omega and factor dimensionality; report uncertainty.
  Synthetic analysis harness implemented; human evidence and defensible factor model pending.
- [ ] **CH02.19** — Fit IRT/logistic model with person-level train/validation/test splits; check differential item functioning by language/order.
  Synthetic logistic anchor-proxy, disjoint splits and language/order terms implemented; actual calibration and sparse-session linking pending.
- [ ] **CH02.20** — Compare predictive validity on independent simulated choices; document limitations and seek expert review.
  Synthetic independent-choice test and baseline implemented; prospective human evidence and expert review pending.
- [x] **CH02.21** — Add score report, coverage, separate dimensions, methodology, revision, and consent screens; avoid gamification that rewards taking risk.
  Discovery navigation opens even before mandate confirmation and guides the client to complete the mandate before starting the questionnaire.

Evidence (2026-11-24): [behavioral protocol](docs/RISKMATCH_BEHAVIORAL.md), [draft pilot](docs/BEHAVIORAL_PILOT.md), notebook chapter 02 cell `5705c45e`, `src/riskmatch/behavioral/discovery.py`, `utility.py`, `pilot_analysis.py`, unit/HTTP/JavaScript tests. The score and likelihoods are experimental; never change financial risk capacity. Human validation, owner visual confirmation and GitHub publication remain pending.



## 03. US Universe

Notebook: [chapter 03](notebooks/RiskMatch_V3.ipynb#chapitre-03) · Guide chapter 2.

- [x] Study and formalize: Build the ETF security master: ticker, currency, class and dates.
- [x] Document assumptions, formulas, data and units.
- [x] Run the notebook on a fixture and analyze errors.
- [x] Test analytical equivalence, edge cases and robustness.
- [x] Extract code into the shared module.
- [x] Write automated tests and make them pass.
- [x] Add the API contract and relevant screen.
- [x] Verify local rendering and update documentation.
- [x] Publish through the owner-approved solo workflow (D003). Chapter 3 covers the research catalog; G06 and CH04.09 remain prerequisites for using the extensions downstream.

### 03 — A. Detailed Tasks


- [x] **CH03.01** — Define the US investment universe and eligible asset classes; identify ETF launch dates, domicile, currency and benchmark.
  Public issuer metadata recorded with source URLs; inception distinct from unknown listing dates. No current metadata used as historical eligibility.
- [x] **CH03.02** — Select 15–30 liquid US equity ETFs (capitalization, sector, style, REIT), nominal Treasury/TIPS-only ETFs and cash.
  The frozen catalog contains 27 listed products, including GLD, USO, SLV, CPER and WEAT. Initial candidate selection: 17 equity/real-estate ETFs, 5 Treasury ETF candidates and USD cash. Dated liquidity screen defined; actual liquidity and market data remain unverified and no candidate is approved for allocation.
- [x] **CH03.03** — Design permanent security ID, ticker history, asset_class, sector, issuer, currency, valid_from/to and multiplier fields.
- [x] **CH03.04** — Store dated investability, listing/delisting, liquidity, expense ratio, AUM and restrictions.
  Local dated-record schema, validation and receipt reader implemented; no fabricated records. Current holdings snapshots available. Historical eligibility records remain incomplete.
- [x] **CH03.05** — Define 300–3000-stock second-stage universe with historical constituents, delistings and historical market cap.
  Independent reconstruction confirmed all 336,000 monthly ranks. Of the ranked records, 190 have a same-day delisting and one lacks positive volume; hold these out of new positions. The 1,297 following-month delistings are tracked separately. 2026 ticker-only observations do not establish a new cohort.
  Research panel preserves every ranked member for the next month, including 191 missing returns. The local 2026 exception register identifies missing dates for all 45 incomplete histories. Terminal proceeds remain open.
  Monthly reconstruction now ranks 1,000 dated candidates in each of 336 months (1998–2025). Apply ranks only after month end; validate historical availability and liquidity before use. Earlier single-date scan located 3,658 preliminary US common-stock PERMNO candidates at 2025-12-31; 1,000 ranked locally, all 1,000 with a daily return observation on that date. An independent full-market 2026 snapshot grid matches 992/1,000 candidate tickers, including 955 with complete sessions. Identifier, license/PIT/G06 checks remain open.
- [x] **CH03.06** — Add only T-Bills, Treasury Notes, Treasury Bonds and TIPS; verify issuer and historical ETF holdings.
  Monthly statements and hashed auction evidence agree on 88,136 positive issue/date observations, including 447 on 2026-10-31. Hold unmatched or conflicting rows. The 138 observed fund reports fail the direct-holdings rule; all other undocumented fund dates remain unverified.
  Issue-level valuation windows and contractual nominal schedules are now materialized. Bills have pre-maturity mark returns. 201,632 nominal accruals and 1,739 indexed payments on 106 TIPS were reconstructed. Realized cash and coupon-bearing total returns require further reconciliation.
  Public auction receipts yielded 3,468 historical Treasury CUSIPs and 444 non-matured candidates at 2026-11-24; five issuer snapshots obtained. All report money-market shares, blocked by the strict direct Treasury-only rule; actual historical holdings, outstanding status/prices and G06 prerequisites pending. FedInvest has 288,594 positive issue-day valuation observations across 694 dates, including all 218 reference month-ends and all 497 recent curve-calendar dates through November 20, 2026. The latest separately verified valuation is November 23. Files were hash-checked; two separate historical archives, 310 monthly debt statements and 322,922 daily ratios for 108 TIPS audited. The quarterly N-PORT position files contain 6,110 positions across 138 identified filings. All 138 report positive exposure to a non-Treasury short-term vehicle. Exclude these observations under the direct-holdings rule. Daily completeness, cash flows and execution-price validation remain open.
- [x] **CH03.07** — Determine which futures families qualify for the active universe.
  The active universe contains zero futures families. Retain the ten historical families for research only. None has verified per-expiry coverage through November 2026. Futures-based USD/CHF, equity and rates hedges are unavailable. Futures history is outside the closure criteria for Chapters 03 and 04.
  CFTC aggregates cover all ten roots. A separate research archive provides 1,470 distinct family/contract-month pairs through March 2024. Record predecessor identity, missing expiries, settlement, volume, open interest and dated margin before enabling futures.
- [x] **CH03.08** — Record availability of futures hedges for USD/CHF, equities and rates.
  All three maps are empty under the active scope. Options remain a separate extension.
- [x] **CH03.09** — Choose benchmark per strategy and cash/risk-free series; distinguish tradable benchmark and non-tradable proxy.
- [x] **CH03.10** — Produce coverage matrix by instrument, date, frequency, missingness, liquidity and source; avoid invented pre-launch data.
  New local source: adjusted daily prices for 12 ETFs through Nov 2026; CRSP monthly AND daily returns for all 22 through 2025, matched by unique PERMNO. No cross-vendor splice; 132,278 ETF security/date keys now matched to daily volume with identical reported returns. The separate public 2026 OHLCV feed has all 22 ETFs on all 225 expected sessions through November 23. The official CRSP refresh, liquidity tests and historical holdings validation remain open. Local extracts and audits under data/processed/universe/ only.
- [x] **CH03.11** — Expose universe filters, availability chart and exclusion reason in UI.

Evidence: [US Universe](docs/US_UNIVERSE.md), `configs/universe_catalog.json`, `security_master.py`, notebook cell `a8500da9`, synthetic fixture and unit/HTTP/JS tests. This is a candidate catalog and coverage interface, not a validated investable universe. UNIV.01, G02, G06, actual holdings and liquidity remain open. Chapter 3 membership checks are reproducible with scripts/verify_universe_membership.py. Chapter 4 source rights and return validation remain open.



The optional crypto research extension contains BTC/USD and ETH/USD spot observations. Mandate, liquidity and custody eligibility remain open.

## 04. Sources and Licenses

Notebook: [chapter 04](notebooks/RiskMatch_V3.ipynb#chapitre-04) · Guide chapter 3.

- [x] Study and formalize: Catalog providers, licenses and data availability dates.
- [x] Document assumptions, formulas, data and units.
- [x] Run the notebook on a fixture and analyze errors.
- [x] Test analytical equivalence, edge cases and robustness.
- [x] Extract code into the shared module.
- [x] Write automated tests and make them pass.
- [x] Add the API contract and relevant screen.
- [ ] Verify local rendering and update documentation.
- [ ] Create a PR, obtain review and merge.

### 04 — A. Detailed Tasks


- [x] **CH04.01** — Inventory prices, corporate actions, fundamentals, index membership, futures, Treasury prices and curves, macro, factor and FX datasets.
- [x] **CH04.02** — For each source record provider, field, frequency, earliest date, coverage, latency, timezone, revision policy and identifiers.
- [ ] **CH04.03** — Verify licensing for local storage, transformation and collaboration before obtaining data; record license and permitted use.
  External terms, local-only policy and WRDS entitlement checks documented; individual license/redistribution confirmation still required. Do not publish licensed source data.
- [x] **CH04.04** — Compare CRSP/WRDS and licensed alternatives; assess public SEC EDGAR, Treasury, FRED/ALFRED and factor datasets.
  Acquisition comparison completed in docs/DATA_ACQUISITION_PLAN.md.
- [x] **CH04.05** — Define provider adapters with explicit as_of and dataset version; mock unavailable provider access.
  ProviderRequest and explicit local/public adapters implemented; exact-version DuckDB lookup respects the first verification date in UTC.
- [x] **CH04.06** — Document API limits, retry/backoff, caching and missing-data behavior without committing credentials.
  Public downloader bounded, retries transient errors; source-specific limits and permissions documented. Optional authorized EODHD update adapter added; no token configured, no live price update claimed.
- [x] **CH04.07** — Design raw immutable storage, normalized Parquet and DuckDB catalog; record file hash, ingestion ID and access date.
  Immutable public receipt hashes, data_catalog_schema.sql, local extraction audits implemented. Actual normalized tables belong to CH05.
- [x] **CH04.08** — Separate proprietary data from synthetic test fixtures and Git-tracked configs.
  Separation verified by the Git exclusion check. Downloads and CRSP extracts kept under ignored data/; no WRDS observations or identifiers committed.
- [ ] **CH04.09** — Create a source quality report and a data dictionary; confirm required fields before approving each method.
  The local research-window receipt includes a two-source year-end price check for all 27 listed products and an event-status panel. Source revisions, permitted use and historical continuity remain relevant to approval.
  All 11 WRDS files scanned and daily volumes reconciled for 22 ETFs. Public 2026 market bars, issuer NAV, historical N-PORT positions and SEC filing chronology now have independent local audits. See the November follow-up table for dates and verified counts. Rights, identifier continuity and completeness checks remain open. No allocation approved.

Evidence: docs/DATA_ACQUISITION_PLAN.md, configs/source_catalog.json, scripts/audit_crsp_monthly.py, scripts/audit_crsp_daily.py, scripts/fetch_public_universe_data.py, configs/data_catalog_schema.sql. Public downloads: Treasury legacy/v2 auction records and 15 latest-vintage FRED series. Source files remain local. CH04.03 and CH04.09 remain open. See [Source review and dictionary](docs/SOURCE_REVIEW.md) for method decisions and the signed-use evidence still needed.



## 05. Point-in-Time Ingestion

Notebook: [chapter 05](notebooks/RiskMatch_V3.ipynb#chapitre-05) · Guide chapter 3.1.

- [x] Study and formalize: Normalize snapshots, corporate actions, calendars and leakage tests.
- [x] Document assumptions, formulas, data and units.
- [x] Run the notebook on a fixture and analyze errors.
- [x] Test analytical equivalence, edge cases and robustness.
- [x] Extract code into the shared module.
- [x] Write automated tests and make them pass.
- [x] Add the API contract and relevant screen.
- [x] Verify local rendering and update documentation.
- [x] Publish through the owner-approved solo workflow (D003).

### 05 — A. Detailed Tasks


- [x] **CH05.01** — Define canonical trading calendar, UTC timestamps and local exchange close.
  Explicit exchange schedule contract and observed session partition. Actual historical early-close timestamps remain unverified and null.
- [x] **CH05.02** — Implement unique instrument/date keys, types, corporate actions, contract expiration and series version checks.
  Typed keys, event-specific keys and source versions. Futures are archived; no active contract ingestion.
- [x] **CH05.03** — Ingest raw data without modification, then produce a deterministic cleaned layer.
  Content-addressed Parquet research partitions, input and output hashes, original raw files preserved.
  Supplemental normalization includes CRSP monthly ETFs, company accounts and CCM, Fama-French/Momentum, real-time macro vintages, FedInvest and TIPS, stock refresh references, fees, assets, liquidity and benchmark membership.
- [x] **CH05.04** — Store observation_date, availability_time, release/vintage and as_of; as-of join only availability_time <= decision time.
  Unknown availability never qualifies. Historical availability remains a source-approval condition.
- [x] **CH05.05** — Detect duplicates, gaps, outliers, stale quotes, invalid prices and missing FX; differentiate closed market from missing data.
  Explicit calendar, nulls and quality counts; candidate anomalies are flags, not automatic corrections.
- [x] **CH05.06** — Handle split factors, dividends, capital changes, mergers, delistings and ticker changes.
  Normalized WRDS distributions, delisting successor/proceeds fields and dated name history plus public split/dividend events. Cash settlement and return reconciliation continue in Chapter 6; ambiguous events remain unavailable.
- [x] **CH05.07** — Build historical membership and fundamental publication lag tests; never use today's constituents retrospectively.
  Dated membership and source filing chronology are distinct from observed outcomes; synthetic availability tests passed.
- [x] **CH05.08** — Align cross-market timestamps without leaking later closes; prohibit uncontrolled forward fill.
- [x] **CH05.09** — Create feature store with explicit lag, lookback, units and data hash.
- [x] **CH05.10** — Test corrected/revised data, missing assets, late arrivals and deliberately injected future data.
- [x] **CH05.11** — Record completeness, rejection reason, lineage, freshness and reproducible snapshot in MarketSnapshot.
- [x] **CH05.12** — Display data coverage and freshness in UI; block dependent runs on invalid snapshots.

Evidence: [Point-in-time preparation](docs/POINT_IN_TIME.md), local Parquet and metadata report, synthetic notebook and API/JS/Python tests. Chapter 5 technical work is separate from actual historical approval: CH04.03/09 and G02 remain open; all real-data partitions remain research-only.



## 06. Returns and FX

Notebook: [chapter 06](notebooks/RiskMatch_V3.ipynb#chapitre-06) · Guide chapter 3.1.

- [x] Study and formalize: Calculate simple/log/total returns, FX and reconcile adjusted prices.
- [x] Document assumptions, formulas, data and units.
- [x] Run the notebook on a fixture and analyze errors.
- [x] Test analytical equivalence, edge cases and robustness.
- [x] Extract code into the shared module.
- [x] Write automated tests and make them pass.
- [x] Add the API contract and relevant screen.
- [x] Verify local rendering and update documentation.
- [x] Publish through the owner-approved solo workflow (D003).

### 06 — A. Detailed Tasks


- [x] **CH06.01** — Calculate simple return P_t/P_(t-1)-1 and log return log(1+r) where valid.
- [x] **CH06.02** — Calculate total return with adjusted split/dividend handling without double counting.
- [x] **CH06.03** — Compare raw-close and total-return series on hand-calculated dividend/split fixtures.
- [x] **CH06.04** — Compound simple returns over horizons; verify product(1+r)-1 equals exp(sum(log(1+r)))-1 when valid.
- [x] **CH06.05** — Calculate arithmetic and geometric average; distinguish forecast mean from realized CAGR.
- [x] **CH06.06** — Compute daily/weekly/monthly aggregation with explicit trading dates and K=252/52/12 conventions.
  Crypto daily convention K=365; incomplete intervals remain null.
- [x] **CH06.07** — Compute base-currency return (1+r_local)(1+r_FX)-1; test reciprocal quotation.
- [x] **CH06.08** — Compute nominal to real return (1+r)/(1+inflation)-1; align inflation availability.
  USD latest-vintage CPI ex-post reference; historical release approval remains open.
- [x] **CH06.09** — Normalize cash accrual using appropriate day count; model excess return vs matching rf series.
- [x] **CH06.10** — Separate dirty bond price/coupons and futures cash P&L; skip log returns for nonpositive futures prices.
  Nominal conditional cash-flow scenarios and TIPS/futures synthetic cases. Actual clean/dirty and cash receipts remain unresolved; futures archived.
- [x] **CH06.11** — Reconcile NAV with dated contributions/retractions; calculate TWR and MWR/IRR.
  Synthetic NAV/flow tests; real ledger validation remains BT00 and chapter 23.
- [x] **CH06.12** — Report units, frequency, missingness, and base currency in output charts.

Evidence: [Return methodology](docs/RETURNS.md), 30 local content-addressed return tables, source-separated CRSP and SOFR reconciliations, single notebook and bilingual quality view. Technical implementation is complete; source approval and actual investment eligibility remain governed by G02.



## 07. Descriptive Statistics

Notebook: [chapter 07](notebooks/RiskMatch_V3.ipynb#chapitre-07) · Guide chapter 4.

- [x] Study and formalize: Means, volatility, covariance, correlation and charts.
- [x] Document assumptions, formulas, data and units.
- [x] Run the notebook on a fixture and analyze errors.
- [x] Test analytical equivalence, edge cases and robustness.
- [x] Extract code into the shared module.
- [x] Write automated tests and make them pass.
- [x] Add the API contract and relevant screen.
- [x] Verify local rendering and update documentation.
- [x] Publish through the owner-approved solo workflow (D003).

### 07 — A. Detailed Tasks


- [x] **CH07.01** — Compute count, missingness, min/max, quantiles and distribution diagnostics by asset.
- [x] **CH07.02** — Compute arithmetic/geometric means, median, variance, sample standard deviation, annualized volatility and downside deviation.
- [x] **CH07.03** — Compute skewness, kurtosis, histogram, empirical CDF and QQ plots; compare heavy tails with normal reference.
- [x] **CH07.04** — Compute auto-correlation, PACF, Ljung-Box and stationarity diagnostics; state assumptions and limitations.
  ADF(1) statistic without an unsupported conventional p-value; longest contiguous runs.
- [x] **CH07.05** — Compute covariance and Pearson/Spearman correlations; handle missing-data alignment and constant series explicitly.
- [x] **CH07.06** — Compute rolling means, volatility, beta and correlations with trailing windows; test no future data.
- [x] **CH07.07** — Compute cross-sectional ranks and standardized features with winsorization fit only on training periods.
- [x] **CH07.08** — Test analytical two-asset covariance and portfolio variance; verify symmetry, PSD, units and sample denominator.
- [x] **CH07.09** — Implement summaries and compare assets, frequency and selected dates in UI.
  Universe presents a searchable client catalogue with name, ticker, source and a direct link to a dedicated statistical profile. Profiles include explanatory graphs and same-frequency multi-source comparisons; acquisition audits and portfolio comparison remain separate.

Evidence: [Descriptive methodology](docs/DESCRIPTIVE_STATISTICS.md), 27,230 local statistical profiles, 2,093,782 rolling rows, 2,064,387 cross-sectional rows and four complete-case reference covariance matrices after corporate-action correction. The statistical research pipeline and comparison UI are implemented; G02 remains required for historical financial-model approval and G03.



## 08. Return Forecasting

Notebook: [chapter 08](notebooks/RiskMatch_V3.ipynb#chapitre-08) · Guide chapter 4.

- [ ] Study and formalize: Historical, EWMA, CAPM, Black-Litterman and uncertainty.
- [x] Document assumptions, formulas, data and units.
- [x] Run the notebook on a fixture and analyze errors.
- [x] Test analytical equivalence, edge cases and robustness of implemented models.
- [x] Extract code into the shared module.
- [x] Write automated tests and make them pass.
- [x] Add the API contract and relevant screen.
- [x] Verify local rendering and update documentation.
- [x] Publish experimental implementation through owner-approved solo workflow (D003).

### 08 — A. Detailed Tasks


- [x] **CH08.01** — Define forecast target (total/excess return), horizon and timestamped lagged features.
  One-period total/price return target implemented; excess target defined but requires matched RF for real assets.
- [x] **CH08.02** — Set naive historical-mean and cash/zero-alpha baselines; estimate rolling means and EWMA.
  Historical, rolling, EWMA and zero-return implemented; aligned cash/RF baseline pending.
- [ ] **CH08.03** — Estimate CAPM beta and expected excess return; compare Fama-French multifactor model and Black-Litterman references.
  Synthetic CAPM/multifactor/no-view BL references implemented; CH10.04/CH15.06 remain open.
- [x] **CH08.04** — Split chronological train/validation/test; purge overlapping labels and embargo where necessary.
  One-period labels are nonoverlapping; tests verify test-period isolation.
- [ ] **CH08.05** — Fit OLS with diagnostics; Ridge, Lasso and Elastic Net using train-only scaling and tuning.
  Train-only OLS and regularization implemented; full diagnostics and G07 remain open.
- [ ] **CH08.06** — Fit Random Forest, XGBoost and neural-network candidates; tune on validation only and record seeds/parameters.
  Technical implementation operational: pinned scikit-learn/XGBoost installed in the isolated environment, synthetic leakage tests and local real-history tests passed on four assets across equity, Treasury ETF and commodity ETF; ML enabled by default in the asset profile. Formal closure remains blocked by CH08.05/G07.
- [ ] **CH08.07** — Record predictions, forecast intervals, residual distributions and uncertainty; avoid claims of reliable return prediction.
  Implemented for the experimental models; formal closure depends on CH08.06.
- [ ] **CH08.08** — Evaluate MSE, MAE, rank IC, directional accuracy and calibration; compare net economic performance.
  Held-out MSE, MAE, temporal rank correlation, direction, coverage and illustrative net strategy implemented; cross-sectional IC/backtest pending.
- [ ] **CH08.09** — Run ablations on features, outlier policy, windows and model complexity; report instability.
  Lag-only, train-clipping and shorter rolling-window ablations implemented; broader sensitivity remains pending.
- [ ] **CH08.10** — Register ForecastBundle with expected return, distribution, horizon, confidence, data_version and model_version.
  Experimental bundle with provenance and empirical interval; confidence calibration and downstream acceptance pending.
- [ ] **CH08.11** — Show forecasts vs realized values, intervals and limitations in UI.
  Experimental bilingual screen implemented and browser-tested; formal closure depends on CH08.10.

Evidence: [Return forecasting](docs/RETURN_FORECASTING.md), corrected corporate-action returns, bounded unlevered forecasts, synthetic tests and local API/asset profile. All 1,474 items examined: 1,008 have all ten core forecasts, 464 have separate conditional estimates, two remain unavailable. No fit errors or forecasts below -100%. A separate 575-asset monthly USD total-return cohort at 2025-12-31 is historical research only; different horizons/targets are not merged. Prior chapter coverage audit found 1,473 assets with returns and descriptive profiles. G02/G07 and CH10/CH15 dependencies remain open.

Optional cross-chapter StockTwits research (CH08/10/15): [sentiment evidence](docs/SENTIMENT.md). Historical course archive safely read from Parquet; 753 matched catalogue assets, 61,141 asset-months, 562/575 common cohort. Seven pooled paired prediction experiments with three simple mean references, historical sentiment factor and scalar relative-view diagnostic; 26 held-out months and calendar-block uncertainty. No current signal after March 2020; no validated incremental gain or production forecast/view promotion. Asset sheets and Sources panel show historical data only.



## 09. Volatility and Covariance

Notebook: [chapter 09](notebooks/RiskMatch_V3.ipynb#chapitre-09) · Guide chapter 4.

- [x] Study and formalize: EWMA, GARCH, shrinkage, DCC; PSD and OOS comparison.
- [x] Document assumptions, formulas, data and units.
- [x] Run the notebook on a fixture and analyze errors.
- [x] Test analytical equivalence, edge cases and robustness of research estimators.
- [x] Extract code into the shared module.
- [x] Write automated tests and make them pass.
- [x] Add the API contract and relevant screen.
- [x] Verify local API/rendering tests and update documentation.
- [x] Publish research implementation via owner-approved solo workflow (D003).

### 09 — A. Detailed Tasks


- [x] **CH09.01** — Estimate sample covariance and annualize consistently with return mean.
- [x] **CH09.02** — Fit EWMA variance and covariance; test decay parameter and initialization.
- [ ] **CH09.03** — Fit GARCH(1,1), EGARCH and GJR-GARCH; check convergence, persistence, residual autocorrelation and asymmetry.
  Implemented and run on all regular candidates; nonconvergence, persistence and guards explicitly reported. G04 remains open.
- [ ] **CH09.04** — Compare historical volatility with conditional forecasts and simple rolling baselines.
  Implemented chronological validation/test comparison; formal closure depends on CH09.03.
- [ ] **CH09.05** — Fit Ledoit-Wolf and OAS shrinkage; compare out-of-sample realized risk and condition number.
  Implemented six exact-interval cohorts; formal closure depends on CH09.04.
- [ ] **CH09.06** — Implement factor covariance model B*Sigma_f*B' + Sigma_e; evaluate residual covariance choices.
  Train-only PCA factor reference and diagonal/full residual variants implemented; economic factor approval requires CH10.10.
- [ ] **CH09.07** — Fit DCC-GARCH conditional correlation where appropriate; test correlation/covariance PSD.
  Three small aligned cohorts fitted; formal closure depends on CH09.05.
- [x] **CH09.08** — Apply numerical regularization only with traceable diagnostics and explicit tolerances.
- [ ] **CH09.09** — Evaluate QLIKE, variance forecast errors, realized risk and portfolio stability in chronological validation.
  Implemented QLIKE/MSE and inverse-volatility stability diagnostic; full backtest remains pending.
- [ ] **CH09.10** — Build rolling volatility/correlation charts, covariance heatmap and confidence warnings.
  Experimental asset and comparison views implemented; formal closure depends on CH09.09.

Evidence: [Volatility and covariance](docs/VOLATILITY_COVARIANCE.md), 1,474 catalogue assets examined, 1,015 regular-model profiles, 457 descriptive-only and two unavailable; six covariance cohorts including exact 575-asset Chapter 8 vector, all sample/shrinkage/PCA matrices PSD, three DCC fits. G04 and CH10.10 prerequisites remain open.



## 10. Factors and Regressions

Notebook: [chapter 10](notebooks/RiskMatch_V3.ipynb#chapitre-10) · Guide chapter 8.

- [x] Study and formalize: 13 factors, exposures, scores, OLS, PCA and attribution.
- [x] Document assumptions, formulas, data and units.
- [x] Run the notebook on a fixture and analyze errors.
- [x] Test analytical equivalence, edge cases and robustness of research estimators.
- [x] Extract code into the shared module.
- [x] Write automated tests and make them pass.
- [x] Add the API contract and relevant screen.
- [x] Verify local API/rendering tests and update documentation.
- [x] Publish research implementation via owner-approved solo workflow (D003).

### 10 — A. Detailed Tasks


- [ ] **CH10.01** — Define factor taxonomy and map all 13 factors to input data and timestamps (catalog below).
  All 13 mapped; G07 approval and true carry/term/inflation-surprise inputs remain open.
- [ ] **CH10.02** — Construct lagged scores, cross-sectional winsorization/z-score, coverage report and neutralization choices.
  Eight observed scores on 336,000 dated membership rows; liquidity size-neutralized, original filings accepted before ranking.
- [ ] **CH10.03** — Build market, size, value, profitability, investment and momentum series using published factors or reproducible definitions.
  Published FF and momentum panels plus eight research portfolio series.
- [ ] **CH10.04** — Estimate CAPM, Fama-French 3/5-factor and multifactor exposures with OLS, rolling OLS and ridge.
  1,022 matched assets; FF3 is FF5 subset; price-only and retrospective targets explicit.
- [ ] **CH10.05** — Use heteroskedasticity/autocorrelation-robust standard errors where justified; test multicollinearity and residuals.
  HAC, VIF, condition numbers, Durbin–Watson; observation-lag HAC limitations disclosed.
- [ ] **CH10.06** — Run PCA on declared covariance/correlation basis; report explained variance, loading stability and sign conventions.
  Train-only published-factor correlation PCA, held-out absolute loading similarity.
- [ ] **CH10.07** — Construct factor portfolios long/short or long-only subject to investability and costs.
  Eight top/bottom quintile research portfolios and illustrative turnover costs; actual execution/borrow eligibility pending.
- [ ] **CH10.08** — Compare factor returns, rank IC, exposure drift and turnover over identical OOS windows.
  Common 36-date held-out window; 29 complete net-return periods; rolling exposure drift.
- [ ] **CH10.09** — Compute attribution from exposure × realized factor return and reconcile residual.
  5,725 specifications reconcile alpha + factors + residual within 1e-10.
- [ ] **CH10.10** — Compute factor risk via BΣ_fB' and residual risk; avoid double counting close factors.
  575-asset common factor covariance, 99 aligned intervals, diagonal/full residual PSD; conditioning/approval remains pending.
- [ ] **CH10.11** — Build factor exposures radar/bar charts and attribution table with coverage warnings.
  Bilingual asset exposure/rolling charts and attribution, Sources aggregate coverage.

Evidence: [Factors and regressions](docs/FACTORS_REGRESSIONS.md), 1,474 examined, 1,022 regression profiles, 445 analytical references, seven unavailable; G07/G02 and original dependency gates remain open.



## 11. Tail Risk

Notebook: [chapter 11](notebooks/RiskMatch_V3.ipynb#chapitre-11) · Guide chapter 10.

- [x] Study and formalize: VaR, ES, EVT, copulas, drawdown and validation.
- [x] Document assumptions, formulas, data and units.
- [x] Run the notebook on a fixture and analyze errors.
- [x] Test analytical equivalence, edge cases and robustness.
- [x] Extract code into the shared module.
- [x] Write automated tests and make them pass.
- [x] Add the API contract and relevant screen.
- [ ] Verify local rendering and update documentation.
- [ ] Create a PR, obtain review and merge.

Implementation evidence (2026-11-25): `tail_risk.py`, `tail_report.py`, `build_tail_universe.py`, `test_tail_risk.py`, bilingual asset sheet and aligned comparison. Local run: 1,474 catalogue items; 1,008 regular 95% profiles, 28 also support 99%, 302 support 95% POT; 463 descriptive only and 3 unavailable. Threshold sensitivity and conditional intervals are experimental; portfolio risk limits and independent acceptance remain open. Formal tickets below retain prerequisite gates.

### 11 — A. Detailed Tasks


- [x] **CH11.01** — Define loss L=-r and horizon/confidence conventions; document sign and positive currency loss.
- [x] **CH11.02** — Implement historical, Gaussian parametric and simulated VaR at 95%/99%.
- [x] **CH11.03** — Implement ES with correct upper-tail weighting for discrete observations and ties.
- [ ] **CH11.04** — Implement expected shortfall risk contributions and scenario-based marginal risk where differentiable.
- [x] **CH11.05** — Compute downside deviation, target shortfall, maximum drawdown, drawdown duration, recovery time and underwater chart.
- [ ] **CH11.06** — Fit EVT peaks-over-threshold with defensible threshold sensitivity; estimate tail uncertainty.
- [ ] **CH11.07** — Compare normal/Student-t and empirical/copula dependence models; evaluate tail dependence.
- [ ] **CH11.08** — Backtest VaR exception rates and independence; compare ES stress diagnostics with finite sample caveats.
- [x] **CH11.09** — Test zero risk, constant return, extreme loss, missing series, small sample and tail quantile ties.
- [x] **CH11.10** — Expose loss distribution, risk limits, confidence/horizon and warnings; never display VaR as guaranteed maximum.



## 12. Financial Objectives

**Open with chapter 01:** CH12.01–02, CH12.04 and CH12.07 plus OBJxx.01 specify objectives before construction. Evaluation on real data and simulation depend on the risk/backtest engine.

Notebook: [chapter 12](notebooks/RiskMatch_V3.ipynb#chapitre-12) · Guide chapter 5.

- [x] Study and formalize: Formalize the 11 objectives, units, constraints and loss function.
- [x] Document assumptions, formulas, data and units.
- [x] Run the notebook on a fixture and analyze errors.
- [x] Test analytical equivalence, edge cases and robustness.
- [x] Extract code into the shared module.
- [x] Write automated tests and make them pass.
- [x] Add the API contract and relevant screen.
- [ ] Verify local rendering and update documentation.
- [ ] Create a PR, obtain review and merge.

Implementation evidence (2026-11-25): `analytics/objectives.py`, `analytics/objectives_report.py`, `/api/objectives/evaluate`, `objectives.js`, `tests/unit/test_objectives.py`, `docs/FINANCIAL_OBJECTIVES.md`. Four fixed reference mixes, 2,000 common six-month block-bootstrap paths each, 223 aligned historical USD months (178 training / 45 holdout), 219 CHF months (175 / 44, two gaps; no block crosses a gap). Evaluate dated funding, priorities, capital floors, income proxies, risk, inflation shock and liability shortfall. Full net-income attribution, DV01 matching, contractual hedge cost/gap stress, point-in-time and independent review remain open rather than claiming certification. Detailed formal tickets retain prerequisite gates.

### 12 — A. Detailed Tasks


- [x] **CH12.01** — Define all 11 objectives as typed goals, not interchangeable portfolio names (catalog below).
- [x] **CH12.02** — Separate objective function, eligibility constraint, benchmark, risk measure and preference weight.
- [ ] **CH12.03** — Translate nominal and real capital goals into dated target amounts; compute shortfall distribution.
- [x] **CH12.04** — Calculate required return with dated contributions, withdrawals and liabilities; report infeasibility.
- [ ] **CH12.05** — Implement income schedule, liability matching, loss budget, inflation-adjusted and absolute-return objectives.
- [ ] **CH12.06** — Implement goal probability P(W_T>=G), expected deficit E[(G-W_T)+] and downside utility with comparable units.
- [x] **CH12.07** — Support multiple goals with priorities, nonnegative normalized weights and documented penalty scaling.
- [ ] **CH12.08** — Test incompatible goals, zero contributions, large liability, horizon mismatch and inflation shocks.
- [ ] **CH12.09** — Compare the same candidate against different goals without recasting the portfolio's underlying strategy.
- [ ] **CH12.10** — Show goal progress, funding gap, probability estimate and explicit risk/goal tradeoffs.



## 13. Baselines

Notebook: [chapter 13](notebooks/RiskMatch_V3.ipynb#chapitre-13) · Guide chapter 6.

- [x] Study and formalize: Cash, 1/N, 60/40 and market benchmark.
- [x] Document assumptions, formulas, data and units.
- [x] Run the notebook on a fixture and analyze errors.
- [x] Test analytical equivalence, edge cases and robustness.
- [x] Extract code into the shared module.
- [x] Write automated tests and make them pass.
- [x] Add the API contract and relevant screen.
- [ ] Verify local rendering and update documentation.
- [ ] Create a PR, obtain review and merge.

Implementation evidence (2026-11-25): `backtesting/baselines.py`, `baseline_report.py`, `/api/baselines`, `baselines.js`, `tests/unit/test_baselines.py`, `docs/BASELINES.md`. Eight fixed-reference variants on 223 matched USD ETF months from June 2007 to Dec 2025; 575-asset Chapter 8 retrospective equal-weight cohort on 100 matched months, compared to cash, 60/40 and SPY on the identical shorter window. CHF uses only continuous matched intervals and BIL as an unhedged cash proxy, not a risk-free rate. Ledger reconciles fees, flows and NAV. Executable fills, historical universe membership, CHF native RF and independent approval remain open; formal tasks retain prerequisite gates.

### 13 — A. Detailed Tasks


- [ ] **CH13.01** — Define cash benchmark, equal weight 1/N, 60/40 and market-cap benchmarks.
- [ ] **CH13.02** — Calculate weights and monthly/quarterly rebalancing with drift between rebalance dates.
- [ ] **CH13.03** — Implement initial trade costs, subsequent turnover and end-of-period valuation; use executable timestamps.
- [ ] **CH13.04** — Compare fixed weights and buy-and-hold separately; compare same dates, currency and rf.
- [ ] **CH13.05** — Use ETF benchmark or historically valid constituents for market-cap weighting.
- [ ] **CH13.06** — Define long-only and unlevered first baseline; enforce sum weights=1.
- [ ] **CH13.07** — Reconcile hand-calculated two-period NAV with weights, flows, fees and returns.
- [ ] **CH13.08** — Create baseline benchmark report with gross/net CAGR, vol, drawdown, Sharpe and stress.
- [ ] **CH13.09** — Expose baseline cards and benchmark comparison in the app before advanced models.



## 14. Mean-Variance

Notebook: [chapter 14](notebooks/RiskMatch_V3.ipynb#chapitre-14) · Guide chapter 6.

- [x] Study and formalize: Minimum variance, maximum Sharpe, maximum utility, frontier and constraints.
- [x] Document assumptions, formulas, data and units.
- [x] Run the notebook on a fixture and analyze errors.
- [x] Test analytical equivalence, edge cases and robustness.
- [x] Extract code into the shared module.
- [x] Write automated tests and make them pass.
- [x] Add the API contract and relevant screen.
- [ ] Verify local rendering and update documentation.
- [ ] Create a PR, obtain review and merge.

Implementation evidence (2026-11-25): `optimization/mean_variance.py`, `mean_variance_report.py`, `build_mean_variance.py`, `/api/mean-variance`, `mean-variance.js`, unit tests and `docs/MEAN_VARIANCE.md`. Four default reference configurations (575-asset cohort and five ETF core in USD/CHF) computed with all four model statuses optimal by LP gap/residual checks. Default shrinkage of extreme Chapter 8 forecasts is explicit, raw alternative available. Chronological training-only holdout, 9 frontier points, lambda sensitivity, linear exposure/turnover API, infeasible target checks, allocation and risk contribution diagnostics. Signed comparison only for core, gross-only; hard issuer/sector/liquidity/volatility/stress/actual turnover constraints without certified inputs remain unverified. No independent acceptance or PIT membership certification; formal tasks keep prerequisite gates.

### 14 — A. Detailed Tasks


- [x] **CH14.01** — Define w, μ, Σ, rf, lambda, funded vs derivative exposure and constraints units.
- [x] **CH14.02** — Implement minimum variance quadratic program and unconstrained analytic reference for invertible covariance.
- [x] **CH14.03** — Implement maximum utility μ'w-lambda*w'Σw/2 with explicit lambda calibration and sensitivity.
- [x] **CH14.04** — Compute efficient frontier by target return constrained quadratic programs; mark infeasible targets.
- [x] **CH14.05** — Implement max Sharpe search/reformulation; handle zero-risk and nonpositive excess-return cases.
- [x] **CH14.06** — Implement constraints on weights, groups, issuer, leverage, gross/net, turnover, risk factors, liquidity and target return.
- [x] **CH14.07** — Run pre-solve feasibility and capture solver status, tolerance, objective, residuals, warm starts and active constraints.
- [x] **CH14.08** — Validate analytic two-asset case, covariance singularity, negative expected excess return and infeasible mandate.
- [ ] **CH14.09** — Compare no-short vs permitted short, concentration caps and turnover penalty on uniform OOS windows.
- [x] **CH14.10** — Plot frontier, weights and marginal risk; export model configuration and solver diagnostics.



## 15. Black-Litterman

Notebook: [chapter 15](notebooks/RiskMatch_V3.ipynb#chapitre-15) · Guide chapter 6.

- [x] Study and formalize: Prior, views, confidence, posterior and allocation.
- [x] Document assumptions, formulas, data and units.
- [x] Run the notebook on a fixture and analyze errors.
- [x] Test analytical equivalence, edge cases and robustness.
- [x] Extract code into the shared module.
- [x] Write automated tests and make them pass.
- [x] Add the API contract and relevant screen.
- [ ] Verify local rendering and update documentation.
- [ ] Create a PR, obtain review and merge.

Implementation evidence (2026-11-25): `optimization/black_litterman.py`, `black_litterman_report.py`, `build_black_litterman.py`, `/api/black-litterman`, bilingual interactive views and allocation comparison, analytical and edge-case tests. Dated restricted CRSP cap anchor covers all 549 equity constituents of 575-asset cohort; ETFs remain in optimizer but not double-counted in anchor. Prior/posterior uncertainty, correlated/duplicate/conflicting views, delta/tau sensitivities, separate Chapter 14 optimizer and training-only holdout against historical, CAPM and EWMA. No global market or suitability certification, historical membership and actual client hard constraint validation remain open; detailed tickets retain prerequisite gates.

### 15 — A. Detailed Tasks


- [ ] **CH15.01** — Derive equilibrium prior π=δΣw_market with consistent total vs excess returns.
- [ ] **CH15.02** — Estimate delta from declared market/risk-free assumptions; record sensitivity and avoid implicit psychometric mapping.
- [ ] **CH15.03** — Build absolute/relative views P and q; define view horizon and uncertainty Ω.
- [ ] **CH15.04** — Validate dimensions, prior covariance PSD, tau, confidence and correlated views.
- [ ] **CH15.05** — Compute posterior via stable linear solves; handle singular matrices and conflicting views explicitly.
- [ ] **CH15.06** — Verify no-view prior, weak/strong confidence, opposing views and identical-view redundancy.
- [ ] **CH15.07** — Compare posterior means and covariance with historical, CAPM and EWMA on matched OOS dates.
- [ ] **CH15.08** — Feed posterior to a separately registered optimizer; compare against prior-only weights.
- [ ] **CH15.09** — Build interactive views/confidence panel, posterior chart and resulting allocation comparison.



## 16. Risk Parity and Hierarchical Methods

Notebook: [chapter 16](notebooks/RiskMatch_V3.ipynb#chapitre-16) · Guide chapter 6.

- [x] Study and formalize: RP, HRP, HERC, diversification and risk contributions.
- [x] Document assumptions, formulas, data and units.
- [x] Run the notebook on a fixture and analyze errors.
- [x] Test analytical equivalence, edge cases and robustness.
- [x] Extract code into the shared module.
- [x] Write automated tests and make them pass.
- [x] Add the API contract and relevant screen.
- [ ] Verify local rendering and update documentation.
- [ ] Create a PR, obtain review and merge.

Implementation evidence (2026-11-25): `optimization/hierarchical.py`, `hierarchical_report.py`, `build_hierarchical.py`, `/api/hierarchical`, bilingual risk budgets/dendrogram/holdout panel, [methodology](docs/HIERARCHICAL.md). Four configurations (575 cohort and five ETF, USD/CHF); Euler contribution checks, convex ERC and cap-active-set KKT, HRP heuristic, two-level HERC constrained cluster risk budgeting, maximum diversification ratio, linkage/cluster sensitivity, historical train-only holdout and pre-crisis tests with exact intervals. Equity/ETF caps can break exact equality of risk contributions; distinguish constrained optimum and heuristic. Actual historical eligibility/executions and unsupported mandate hard constraints remain unverified; formal dependency gates remain open.

### 16 — A. Detailed Tasks


- [ ] **CH16.01** — Calculate portfolio risk and marginal/total risk contributions; verify sum RC=σp.
- [ ] **CH16.02** — Specify target risk budgets and denominator conventions; distinguish negative contributions for short positions.
- [ ] **CH16.03** — Solve risk parity with long-only baseline and budget feasibility checks.
- [ ] **CH16.04** — Compute correlation distance sqrt((1-rho)/2); validate distance and PSD.
- [ ] **CH16.05** — Build hierarchical clustering/dendrogram with explicit linkage and leaf ordering.
- [ ] **CH16.06** — Implement HRP recursive bisection inverse-variance allocation and cluster weights.
- [ ] **CH16.07** — Implement HERC cluster risk budgets and allocation; compare linkage/cluster count sensitivity.
- [ ] **CH16.08** — Implement maximum diversification ratio w'σ/σp and handle zero volatility.
- [ ] **CH16.09** — Test equal variance/uncorrelated, perfectly correlated, duplicate assets and unstable clusters.
- [ ] **CH16.10** — Compare allocations, realized risk contribution, turnover and crisis robustness OOS.
- [ ] **CH16.11** — Show risk contributions, dendrogram, cluster weights and diversification diagnostics.



## 17. Downside Optimization

Notebook: [chapter 17](notebooks/RiskMatch_V3.ipynb#chapitre-17) · Guide chapter 6.

- [x] Study and formalize: CVaR, Sortino, Omega, drawdown, tracking error and IR.
- [x] Document assumptions, formulas, data and units.
- [x] Run the notebook on a fixture and analyze errors.
- [x] Test analytical equivalence, edge cases and robustness.
- [x] Extract code into the shared module.
- [x] Write automated tests and make them pass.
- [x] Add the API contract and relevant screen.
- [ ] Verify local rendering and update documentation.
- [ ] Create a PR, obtain review and merge.

Implementation evidence (2026-11-25): `optimization/downside.py`, `downside_report.py`, `build_downside.py`, `/api/downside`, bilingual frontier/active exposure/path diagnostics, [methodology](docs/DOWNSIDE.md). CVaR LP and additive CDaR LP with objective reconciliation, positive Sortino QP tangency, Omega homogeneous LP, exact signed small-universe vertex search, benchmark-relative TE/IR using exact benchmark identity and regularized active covariance. Same matched monthly USD/CHF cohort/core; train-only net holdout, tail scenario and alpha sensitivities, explicit zero-downside and infeasible states. Small tail samples, current static membership, actual fills and unsupported hard mandate constraints remain unverified; formal dependency gates remain open.

### 17 — A. Detailed Tasks


- [ ] **CH17.01** — Specify thresholds, loss signs, confidence level, scenario probabilities and path horizon.
- [ ] **CH17.02** — Implement CVaR via auxiliary z and nonnegative shortfall variables; validate tail loss case by hand.
- [ ] **CH17.03** — Implement Sortino using downside deviation relative to MAR; handle zero denominator without inventing infinity ranking.
- [ ] **CH17.04** — Implement Omega ratio at threshold; define handling when expected downside is zero.
- [ ] **CH17.05** — Implement min drawdown or CDaR with explicit path dependence and solver limitations.
- [ ] **CH17.06** — Implement tracking-error minimum against weights/returns from a valid benchmark.
- [ ] **CH17.07** — Implement max information ratio with active return and risk; validate benchmark identity/zero TE.
- [ ] **CH17.08** — Compare historical/scenario sample size and stress sensitivity; avoid overfitting the worst observed path.
- [ ] **CH17.09** — Add downside frontier, benchmark-active exposure, scenario and drawdown charts.
- [ ] **CH17.10** — Use identical constraints and net OOS backtest for each downside method.



## 18. Advanced Optimization

Notebook: [chapter 18](notebooks/RiskMatch_V3.ipynb#chapitre-18) · Guide chapter 6.

- [x] Study and formalize: Robust, resampled, DRO, Kelly, entropy and diagnostics.
- [x] Document assumptions, formulas, data and units.
- [x] Run the notebook on a fixture and analyze errors.
- [x] Test analytical equivalence, edge cases and robustness.
- [x] Extract code into the shared module.
- [x] Write automated tests and make them pass.
- [x] Add the API contract and relevant screen.
- [ ] Verify local rendering and update documentation.
- [ ] Create a PR, obtain review and merge.

Implementation evidence (2026-11-25): `optimization/advanced.py`, `advanced_report.py`, `build_advanced.py`, `/api/advanced`, bilingual advanced configurator, [methodology](docs/ADVANCED.md). Block-bootstrap box/spectral robust utility, all-draw feasible resampled utility and trade-off points, Euclidean W1 robust mean with nominal covariance, positive-wealth Kelly and capped fractional blend, exact entropy/L1 mirror-prox. Zero-radius analytical equivalence, edge-case tests and separate training-only net holdout; explicit hypothetical stress. Four default USD/CHF configurations. Ambiguity calibration, true cash fractional blend when caps preclude it, unsupported mandate hard constraints, actual execution and independent approval remain explicitly limited; detailed formal dependency gates remain open.

### 18 — A. Detailed Tasks


- [ ] **CH18.01** — Define mean/covariance uncertainty sets and robust utility objective; calibrate using training data.
- [ ] **CH18.02** — Implement robust optimization on bounded scenarios and document worst-case assumptions.
- [ ] **CH18.03** — Implement block bootstrap resampling, optimize each draw and aggregate feasible weights.
- [ ] **CH18.04** — Implement distributionally robust formulation with declared ambiguity radius; evaluate computational cost.
- [ ] **CH18.05** — Implement log-growth Kelly and fractional Kelly; ensure admissible positive terminal wealth in all modeled scenarios.
- [ ] **CH18.06** — Implement entropy objective (-sum w log w) for positive funded weights; compare equal-weight limiting case.
- [ ] **CH18.07** — Apply regularization and transaction cost/turnover penalties to comparable objectives.
- [ ] **CH18.08** — Record solver status, runtime, seed, convergence, residual and sensitivity for every method.
- [ ] **CH18.09** — Test uncertainty radius zero, correlated assets, return near -100%, zero weights and infeasible solutions.
- [ ] **CH18.10** — Compare robustness, concentration, OOS stress and net performance against simple baselines.
- [ ] **CH18.11** — Expose model parameters, uncertainty tradeoffs and warnings in app configurator.



## 19. Passive and Active Strategies

Notebook: [chapter 19](notebooks/RiskMatch_V3.ipynb#chapitre-19) · Guide chapter 7.

- [x] Study and formalize: Passive, long-only, smart beta, core-satellite and factors.
- [x] Document assumptions, formulas, data and units.
- [x] Run the notebook on a fixture and analyze errors.
- [x] Test analytical equivalence, edge cases and robustness.
- [x] Extract code into the shared module.
- [x] Write automated tests and make them pass.
- [x] Add the API contract and relevant screen.
- [ ] Verify local rendering and update documentation.
- [ ] Create a PR, obtain review and merge.

Implementation evidence (2026-11-25): `strategies/long_only.py`, `long_only_report.py`, `build_long_only.py`, `/api/long-only`, bilingual strategy/ledger panel, [methodology](docs/LONG_ONLY.md). Sixteen registry entries including eight factor sleeves; 15 admissible computed on the 575-asset USD/CHF cohorts (single SPY replication incompatible with default 5% cap, still external benchmark). Core ETF-only factor/fundamental sleeves explicitly unavailable. Dated stock top-1000 eligibility, verified factor score archive, positive accepted original book equity, rolling alpha, aggregate core/satellite budgets, drift and actual fee-adjusted turnover limits, chronological sequential holdout, risk-matched external reference and cost shock. Historical index constituent sampling, original market availability/execution, unsupported mandate hard limits and independent acceptance remain open; formal dependency gates remain open.

### 19 — A. Detailed Tasks


- [ ] **CH19.01** — Build a strategy registry separating signal, estimate, optimizer, execution policy and benchmark.
- [ ] **CH19.02** — Define passive ETF replication; use historical index membership for individual-stock sampling only after EXT.01, with tracking constraints.
- [ ] **CH19.03** — Build active long-only alpha/signal ranking with eligible universe and concentration controls.
- [ ] **CH19.04** — Implement smart beta alternative weight rules (equal, factor, fundamental) with turnover limits.
- [ ] **CH19.05** — Construct factor-investing sleeves; document factor score weighting and neutralization choices.
- [ ] **CH19.06** — Define core-satellite architecture: core benchmark, active sleeves, target budgets and aggregate constraints.
- [ ] **CH19.07** — Specify each strategy's input data, rebalance frequency, data publication delays, signal exit rules and transaction-cost assumptions.
- [ ] **CH19.08** — Compare each strategy to passive, 1/N and risk-matched alternatives on identical OOS dates.
- [ ] **CH19.09** — Test zero signal, missing fundamentals, stale index weights, universe changes and cost shocks.
- [ ] **CH19.10** — Expose signal rationale, allocation method, benchmark and realized active risk.



## 20. Alternative Strategies

Notebook: [chapter 20](notebooks/RiskMatch_V3.ipynb#chapitre-20) · Guide chapter 7.

- [x] Study and formalize: Long/short, neutral, macro, CTA, arbitrage, carry, momentum and others.
- [x] Document assumptions, formulas, data and units.
- [x] Run the notebook on a fixture and analyze errors.
- [x] Test analytical equivalence, edge cases and robustness.
- [x] Extract code into the shared module.
- [x] Write automated tests and make them pass.
- [x] Add the API contract and relevant screen.
- [ ] Verify local rendering and update documentation.
- [ ] Create a PR, obtain review and merge.

### 20 — A. Detailed Tasks

Experimental implementation: [model specifications and limitations](docs/ALTERNATIVE.md). Signed and defensive ETF strategies run on the chronological common monthly cohort. Dated futures and carry are explicitly unavailable; pair selection may reject all pairs. Exact borrow and release data, market-impact, mandate certification and independent review remain open. Detailed production acceptance tickets remain open.

- [ ] **CH20.01** — Implement long/short with borrow availability and costs, gross/net, position caps and collateral.
- [ ] **CH20.02** — Implement market-neutral beta and optional dollar-neutral constraints; measure realized beta.
- [ ] **CH20.03** — Implement macro signals using release/vintage data for growth, inflation and rates.
- [ ] **CH20.04** — Implement CTA time-series momentum and volatility scaling; separate real contract P&L from continuous signal series.
- [ ] **CH20.05** — Implement cointegration/spread statistical arbitrage with train-only pair selection and structural-break checks.
- [ ] **CH20.06** — Implement carry by asset class and funding convention; track roll, carry and crash exposure.
- [ ] **CH20.07** — Implement cross-sectional and time-series momentum with declared lag/lookback; test reversal and crowding.
- [ ] **CH20.08** — Implement mean-reversion z-score, entry/exit and loss limits; test nonstationarity.
- [ ] **CH20.09** — Implement tactical allocation as bounded deviation from strategic weights.
- [ ] **CH20.10** — Implement volatility targeting with capped exposure and liquidity/cost controls.
- [ ] **CH20.11** — Construct All Weather scenario/risk allocation and test inflation/rate regime shifts.
- [ ] **CH20.12** — Implement multi-strategy sleeve aggregation, correlations and risk budget; prevent duplicated exposure.
- [ ] **CH20.13** — Construct regime-switching signal using filtered not smoothed probabilities.
- [ ] **CH20.14** — Implement tail hedging simulation (conditional futures hedges; options only authorized extension); identify gap and cost limits.
- [ ] **CH20.15** — Compare all applicable strategies to relevant net benchmarks with documented delays and risk/cost decomposition.
- [ ] **CH20.16** — Reject any strategy incompatible with mandate and show reasons; no real orders.



## 21. US Treasuries

Notebook: [chapter 21](notebooks/RiskMatch_V3.ipynb#chapitre-21) · Guide chapter 4.

- [x] Study and formalize: T-Bills, Notes, Bonds, TIPS: cash flows, clean/dirty prices, duration, convexity, DV01 and curve risk.
- [x] Document assumptions, formulas, data and units.
- [x] Run the notebook on a fixture and analyze errors.
- [x] Test analytical equivalence, edge cases and robustness.
- [x] Extract code into the shared module.
- [x] Write automated tests and make them pass.
- [x] Add the API contract and relevant screen.
- [ ] Verify local rendering and update documentation.
- [ ] Create a PR, obtain review and merge.

### 21 — A. Detailed Tasks

Experimental implementation: [Treasury methods and limitations](docs/TREASURIES.md). 444 active identities as of 2026-11-25; 438 computed on 2026-11-23 valuation marks, 6 initial coupon periods not verified. Nominal/real par curves dated 2026-11-20, approximate spot/forward bootstrap, key-rate sensitivities, TIPS ratios and published cash payments, funded nominal cash-flow/LDI linear programs. Detailed formal acceptance remains open for exact settlement, executable liquidity, missing first-period dates, PIT publication and independent review.

- [ ] **CH21.01** — Build Treasury security master: CUSIP, issuer, type, coupon, calendar, settlement, day count, maturity and TIPS index ratio.
- [ ] **CH21.02** — Generate coupon, accrued interest and maturity redemption schedules; handle zero-coupon T-Bills and indexed TIPS principal/coupons.
- [ ] **CH21.03** — Calculate clean/dirty price, accrued interest, yield-to-maturity and total return including coupons.
- [ ] **CH21.04** — Construct Treasury nominal/real spot/forward curve; define discount factors/interpolation and bootstrap inputs.
- [ ] **CH21.05** — Compute Macaulay, modified, effective and key-rate duration; validate with price shocks.
- [ ] **CH21.06** — Calculate convexity, DV01 and key-rate DV01; document bumps and units.
- [ ] **CH21.07** — Model nominal/real rate shocks, slope, curvature, inflation breakeven, TIPS indexation and Treasury liquidity.
- [ ] **CH21.08** — Construct Treasury allocation with duration, DV01, maturity, liquidity and cash-flow constraints.
- [ ] **CH21.09** — Create cash-flow ladder and LDI duration/key-rate matching against dated liabilities.
- [ ] **CH21.10** — Model transaction costs and bid/ask; exclude stale/untradeable prices.
- [ ] **CH21.11** — Test zero coupon, par bond, payment date, maturity, day count, TIPS indexation and curve shocks.
- [ ] **CH21.12** — Display nominal/real curves, maturity ladder, coupons, rate sensitivity and breakeven.



## 22. Futures

Notebook: [chapter 22](notebooks/RiskMatch_V3.ipynb#chapitre-22) · Guide chapter 3.1.

- [x] Study and formalize: Expiries, multipliers, margin, collateral and roll.
- [x] Document assumptions, formulas, data and units.
- [x] Run the notebook on a fixture and analyze errors.
- [x] Test analytical equivalence, edge cases and robustness.
- [x] Extract code into the shared module.
- [x] Write automated tests and make them pass.
- [x] Add the API contract and relevant screen.
- [ ] Verify local rendering and update documentation.
- [ ] Create a PR, obtain review and merge.

### 22 — A. Detailed Tasks

Experimental implementation: [futures specification and gaps](docs/FUTURES.md). All ten archived families support conditional daily variation-margin/roll accounting on the default 2022–2024 archive window. Earlier unresolved rolls stop rather than fabricate fills. Zero active futures. Formal acceptance pending actual exchange settlements, per-expiry specifications/expiry/volume/open interest, clearing margins, executable roll and bid/ask, CTD/spot, PIT and independent review.

- [ ] **CH22.01** — Build contract specifications (ticker, expiry, multiplier, settlement, tick, margin, last trading date).
- [ ] **CH22.02** — Load historical per-expiry quotes, volume/open interest and margin schedules; preserve negative prices.
- [ ] **CH22.03** — Define contract rolls as executable closing/opening trades, with calendar and liquidity rules.
- [ ] **CH22.04** — Construct separate continuous back-adjusted series for signals only.
- [ ] **CH22.05** — Calculate P&L q*multiplier*(settle_t-settle_prev) by actual contract; reconcile daily variation margin.
- [ ] **CH22.06** — Calculate notional and gross/net exposure, beta and DV01 equivalents; do not count notional as funded asset weights.
- [ ] **CH22.07** — Implement integer contracts or rounding with post-round constraint validation.
- [ ] **CH22.08** — Maintain collateral, cash interest, initial/maintenance margins, stressed liquidity reserve and margin call simulations.
- [ ] **CH22.09** — Estimate roll cost, commissions, spread, slippage, carry and basis by contract.
- [ ] **CH22.10** — Test negative settlement, expired contract, roll day, margin increase, contract size change and missing quote.
- [ ] **CH22.11** — Show expiry ladder, roll schedule, margin/collateral, P&L attribution and notional separately.



## 23. Walk-Forward Backtesting

**Open before advanced models:** BT00.01–06 are the minimal ETF/cash backtest. Ledger extensions for Treasuries and futures are validated only after chapters 21–22.

Notebook: [chapter 23](notebooks/RiskMatch_V3.ipynb#chapitre-23) · Guide chapter 9.

- [x] Study and formalize: Chronology, benchmarks, fees, delayed execution and ledger.
- [x] Document assumptions, formulas, data and units.
- [x] Run the notebook on a fixture and analyze errors.
- [x] Test analytical equivalence, edge cases and robustness.
- [x] Extract code into the shared module.
- [x] Write automated tests and make them pass.
- [x] Add the API contract and relevant screen.
- [ ] Verify local rendering and update documentation.
- [ ] Create a PR, obtain review and merge.

### 23 — A. Detailed Tasks

Experimental implementation: [walk-forward specification](docs/WALK_FORWARD.md). Core and retrospective cohort exact monthly data, dated eligibility, delayed fills, rolling/expanding training, validation-only λ/model selection, frozen final holdout and subsequent prior-only refits, signed fees scenarios, benchmarks, joint moving-block diagnostic, export and local run registry. Detailed formal acceptance remains open for full historical constituents/delistings, actual execution/ADV/tax, dated rolling ML forecasts, individual Treasury/futures common execution and independent review.

- [ ] **CH23.01** — Define initial capital, benchmark, execution timing, decision timestamp, cash-flow convention and rebalance schedule.
- [ ] **CH23.02** — Build event ledger: snapshot → signal → target → orders → fills → costs → cash/P&L/NAV.
- [ ] **CH23.03** — Implement asset-specific trades, coupons/dividends, futures variation margin, short borrow and financing.
- [ ] **CH23.04** — Model fees, half-spread, slippage, price impact vs ADV, market participation, roll and applicable tax assumptions.
- [ ] **CH23.05** — Implement buy-and-hold/rebalanced baseline and reconcile daily position value plus cash against NAV.
- [ ] **CH23.06** — Implement rolling/expanding training/validation/test folds; enforce chronological split and lock final holdout.
- [ ] **CH23.07** — Apply purging/embargo to overlapping labels; fit transformations only on training data.
- [ ] **CH23.08** — Use historical constituents/delisted securities and realistic availability/execution delay.
- [ ] **CH23.09** — Record all experiments including failed/aborted runs, seeds, config hash, dataset hash and version.
- [ ] **CH23.10** — Calculate common metric suite and compare cash, 60/40, 1/N and strategy-specific benchmarks.
- [ ] **CH23.11** — Test future-data perturbation invariance, cost monotonicity on fixed trades, no-trade/no-cost fixtures, rolls and missing quotes.
- [ ] **CH23.12** — Evaluate multiple testing, bootstrap intervals, deflated Sharpe/reality check as appropriate.
- [ ] **CH23.13** — Run parameter sensitivity, subperiod/regime stress, doubled costs, latency and capacity scenarios.
- [ ] **CH23.14** — Export ledger, trades, NAV, drawdown, benchmark metrics and OOS fold-by-fold report.



## 24. Stress and Monte Carlo

Notebook: [chapter 24](notebooks/RiskMatch_V3.ipynb#chapitre-24) · Guide chapter 11.

- [x] Study and formalize: Scenarios, terminal wealth distribution, goals, flows and uncertainty.
- [x] Document assumptions, formulas, data and units.
- [x] Run the notebook on a fixture and analyze errors.
- [x] Test analytical equivalence, edge cases and robustness.
- [x] Extract code into the shared module.
- [x] Write automated tests and make them pass.
- [x] Add the API contract and relevant screen.
- [ ] Verify local rendering and update documentation.
- [ ] Create a PR, obtain review and merge.

### 24 — A. Detailed Tasks

Experimental implementation: [scenario and Monte Carlo specification](docs/STRESS_MC.md). Ten hypothetical scenarios, four historical complete-window replay checks, five correlated path models, strategy-wide gross comparison and selected costed wealth/goal projection, individual Treasury and archived futures examples, six parameter sensitivities. Formal acceptance pending verified execution, actual rate/factor/FX sensitivities, full PIT history, independently validated forecasts and review.

- [ ] **CH24.01** — Define scenario universe: historical dot-com, 2008, 2020 and 2022 when covered; label missing history.
- [ ] **CH24.02** — Define equity crash, recession, inflation, +200bp rates, steepening/flattening, real yields, simultaneous equity/Treasury decline, FX and margin shocks.
- [ ] **CH24.03** — Map scenarios to coherent asset, factor, nominal/real curve, inflation and FX shocks; document assumptions.
- [ ] **CH24.04** — Revalue equities, bonds and futures positions; calculate cash, margin, liquidity and shortfall impact.
- [ ] **CH24.05** — Generate correlated multivariate-normal paths as baseline; verify input covariance and simulated moments.
- [ ] **CH24.06** — Add Student-t, block-bootstrap, regime and copula models; compare tails and temporal dependence.
- [ ] **CH24.07** — Implement W_(t+1)=(W_t+flow_t)(1+r_(t+1))-cost_t, with explicit cash-flow timing and inflation.
- [ ] **CH24.08** — Simulate rebalancing, constraints, sovereign-rate risk, funding and FX.
- [ ] **CH24.09** — Compute P5/25/50/75/95 capital, probability of target success, expected deficit and uncertainty intervals.
- [ ] **CH24.10** — Test reproducible seed, zero volatility, zero return, known deterministic goal, extreme shock and convergence by path count.
- [ ] **CH24.11** — Vary expected returns/covariance, regime probabilities, inflation and costs to distinguish parameter uncertainty from process risk.
- [ ] **CH24.12** — Build fan chart, probability/shortfall report and scenario comparison; label simulated vs historical results.



## 25. Improvement, Matching and Comparison

Two separate workstreams with mandatory delivery order: scientific improvement CH25.15–21 → IMP.01–02, then personalized selection CH25.01–14 and multi-Match allocation CH25.22–28 → MATCH.01. MVP.01–04 tests RiskMatch as soon as the baselines are validated.

Notebook: [chapter 25](notebooks/RiskMatch_V3.ipynb#chapitre-25) · Guide chapter 12.

Research kickoff (2026-11-25): provisional reference and common evaluation windows frozen in [Chapter 25 research protocol](docs/IMPROVEMENT.md). Existing Chapter 23 runs are experimental; formal CH25.15 and final MATCH.01 remain gated. Previously examined holdouts are research comparisons, not fresh independent confirmation.

Experimental implementation: `improvement.py` runs five controlled changes on the chapter 23 ledger. `historical_matches.py` reconciles historical core USD strategy targets against the chapter 24 stress archive. Explore filters on the modeled stress budget and ranks by development returns, stress, goal preferences and optional Discovery score. My Matches combines liked strategies, calculates look-through exposures, joint stress, risk contributions, correlations and benchmark results. Saved budgets are scoped to mandate, deck version and liked strategy IDs. Older synthetic sessions retain their original deck. Full objective coverage, other universes, incremental inter-strategy trading costs, independent validation and formal approval remain open.

- [ ] Study and formalize: Separate scientific portfolio improvement from personalized selection.
- [ ] Document assumptions, formulas, data and units.
- [ ] Run the notebook on a fixture and analyze errors.
- [ ] Test analytical equivalence, edge cases and robustness.
- [ ] Extract code into the shared module.
- [ ] Write automated tests and make them pass.
- [ ] Add the API contract and relevant screen.
- [ ] Verify local rendering and update documentation.
- [ ] Create a PR, obtain review and merge.

### 25 — A. Detailed Tasks

Local research delivery, 2026-11-25 (formal dependencies below remain tracked separately):

- [x] Rebuild USD targets and compare their scenario returns to the frozen stress archive. In the test mandate (20% maximum scenario loss, Discovery 18), 21 cards passed.
- [x] Replay a 60/40 manual allocation and minimum-variance alternative through the API handler. Check funded exposures sum to one and volatility reconciles to risk contributions.
- [x] Execute the chapter 25 notebook example on local historical returns. Exercise Like, allocation, optimizer, paper confirmation and saved budgets through the web interaction test.
- [x] Replay six model specifications, recording turnover, net return differences, volatility and block-bootstrap comparisons.
- [ ] Verify visual rendering over HTTP on the host, independent acceptance and GitHub publication.


- [ ] **CH25.01** — Design candidate generator combining goal, strategy, estimate and optimizer without indiscriminate Cartesian search.
- [ ] **CH25.02** — Require versioned Candidate with positions, funded weights, derivatives notionals, collateral, constraints and provenance.
- [ ] **CH25.03** — Filter hard mandate constraints before presentation; log infeasibility, insufficiency, stale data and margin reasons.
- [ ] **CH25.04** — Evaluate all candidates under the same OOS dates, benchmark, costs, scenarios and currency.
- [ ] **CH25.05** — Identify Pareto-efficient candidates and explicitly choose optimization dimensions; test dominated portfolios.
- [ ] **CH25.06** — Define normalized multi-criteria utility S=sum_j a_j*u_j(x_j) with documented preference weights and no double-counting.
- [ ] **CH25.07** — Analyze sensitivity of ranks to assumptions and weights; compare robust/simple benchmark and retain 3–5 primary finalists.
- [ ] **CH25.08** — Present initial 6–12 diverse candidate cards at most, with identical metrics and dates; offer full list.
- [ ] **CH25.09** — Build card fields: name, objective, allocation, futures notional, return interval, volatility, ES, drawdown, stress, goal probability, costs, turnover, liquidity, currency and benchmark.
- [ ] **CH25.10** — Show loss as money and percent; separate realized/simulated/forecast data and explain compatibility.
- [ ] **CH25.11** — Implement like/dislike/pass/undo with optional reason; preference can never override hard constraint.
- [ ] **CH25.12** — Compare shortlist side-by-side including simple baseline, and explain exclusions and alternatives.
- [ ] **CH25.13** — Require refreshed constraint checks and explicit selection for paper trading; handle none selected/no compatible candidates without forcing a match.
- [ ] **CH25.14** — Test repeated swipes, undo, stale candidates, changed mandate, empty shortlist, infeasible goals and rank stability.
- [ ] **CH25.15** — Freeze a reference allocation and identical OOS folds before measuring incremental improvements.
- [ ] **CH25.16** — Compare empirical and shrinkage covariance: realized risk, weight stability and turnover.
- [ ] **CH25.17** — Compare historical mean, EWMA, CAPM, Black-Litterman and validated predictive models.
- [ ] **CH25.18** — Evaluate concentration caps, L1 turnover penalties, factor diversification and robustness separately.
- [ ] **CH25.19** — Evaluate ensembles, hedges and regime adaptation separately after all incremental costs.
- [ ] **CH25.20** — Remove each component in ablation; measure changes in net return, risk, shortfall and uncertainty.
- [ ] **CH25.21** — Reject improvements that fail holdout or stress robustness; document when to keep the simpler model.
- [ ] **CH25.22** — Create a dedicated My Matches tab with liked compatible strategies, versioned IDs, explanations and individual allocation sliders; provide single-Match and empty states.
- [ ] **CH25.23** — Implement manual nonnegative strategy budgets summing to 100%; aggregate underlying funded holdings by security identity and keep derivatives, collateral and cash separate; reject unsupported exposures.
- [ ] **CH25.24** — Recalculate combined risk from aligned strategy paths and underlying exposures, including covariance, ES, drawdown, concentration, currency, costs and stress; never average nonlinear risk statistics.
- [ ] **CH25.25** — Optimize nonnegative strategy budgets using only liked, eligible strategies, with the same mandate-level limits, comparable observations, costs and explicit objective; return infeasibility rather than silently relaxing constraints.
- [ ] **CH25.26** — Compare manual, optimized and reference allocations on aligned net out-of-sample periods; show consolidated asset weights, duplicated exposures, strategy correlations and risk contribution.
- [ ] **CH25.27** — Persist allocations with candidate and mandate versions; invalidate on changed likes, mandate or stale data; require a fresh aggregate constraint check and explicit paper-only confirmation.
- [ ] **CH25.28** — Test single and multiple Matches, zero/invalid budgets, identical/overlapping holdings, missing common periods, stale versions, combined constraint violations, unsupported derivatives and infeasible optimization.



## 26. Dynamic Management

Notebook: [chapter 26](notebooks/RiskMatch_V3.ipynb#chapitre-26) · Guide chapter 13.

Experimental implementation: `dynamic/policies.py`, `dynamic/report.py`, `/api/dynamic` and the My Matches dynamic simulation panel. Ten reduced-form allocation policies and two baselines use the frozen matched USD sleeve paths, conservative modeled stress limits, lagged signals, recurring flows and a self-financing fee ledger. See [methodology](docs/DYNAMIC.md). Full multi-asset dynamic controls, dated liabilities, market closures, independent validation and formal dependency gates remain open.

Local research delivery (2026-11-25):

- [x] Execute ten policies and two baselines over the 45-month archived test interval with a 60/40 Mean Reversion/Black-Litterman Match.
- [x] Compare fee and quarterly-rebalancing sensitivity, record capital, drift, modeled stress, concentration, cash and trailing risk.
- [x] Verify ledger funding, stress bounds, future-observation invariance and withdrawal shortfall on fixtures.
- [x] Integrate the notebook example and the confirmed paper allocation workflow.
- [ ] Host browser verification, full portfolio/mandate coverage and independent acceptance.

- [ ] Study and formalize: 10 dynamic models, rebalancing, monitoring and costs.
- [ ] Document assumptions, formulas, data and units.
- [ ] Run the notebook on a fixture and analyze errors.
- [ ] Test analytical equivalence, edge cases and robustness.
- [ ] Extract code into the shared module.
- [ ] Write automated tests and make them pass.
- [ ] Add the API contract and relevant screen.
- [ ] Verify local rendering and update documentation.
- [ ] Create a PR, obtain review and merge.

### 26 — A. Detailed Tasks


- [ ] **CH26.01** — Define current positions, weight drift, risk budget, rebalance trigger, transaction costs and cash reserve.
- [ ] **CH26.02** — Implement periodic monthly/quarterly rebalancing and drift threshold baseline; monitor costs avoided.
- [ ] **CH26.03** — Design regime variables and filtered-state estimates; test state uncertainty.
- [ ] **CH26.04** — Implement all 10 dynamic policy models from catalog below, incrementally against fixed policy.
- [ ] **CH26.05** — Track estimated and realized volatility, expected shortfall, exposures, factor drift, margin and concentration.
- [ ] **CH26.06** — Generate proposed simulated trades only when data freshness, constraints and margin checks pass.
- [ ] **CH26.07** — Model multi-period flows, liabilities, costs, turnover and execution delay in policy state.
- [ ] **CH26.08** — Test new contribution, withdrawal, crash, limit violation, stale data, margin call and market closure.
- [ ] **CH26.09** — Compare dynamic vs static portfolios on same dates, net performance, turnover, shortfall and drawdown.
- [ ] **CH26.10** — Build monitoring, drift alerts, policy explainability, proposed orders and human confirmation.
- [ ] **CH26.11** — Record state, decision, model version, before/after constraints and ledger reconciliation for every period.



## 27. Integration and Validation

Notebook: [chapter 27](notebooks/RiskMatch_V3.ipynb#chapitre-27) · Guide chapter 17.

Local implementation (2026-11-25): [integration protocol](docs/INTEGRATION.md), `integration.py`, `/api/paper/export`, downloadable reconciled ZIP, encrypted save backup/restore, deterministic Chapter 27 synthetic notebook example, and a corrected CI allowlist excluding the private-data Chapter 25 cell. Formal dependencies and independent review remain tracked below.

Local validation evidence:

- [x] 45-month Mean Reversion / Black-Litterman MPC paper export through the actual API handler: twelve files, reconciled ledger, deterministic hashes.
- [x] Synthetic export reproducibility and rejection of altered ledger, excess stress, invalid fees and incomplete policy; three targeted export tests.
- [x] 33 web tests including Match confirmation, dynamic ZIP download, encrypted backup import, duplicate handling and restoration with the original PIN.
- [x] All 27 allowlisted synthetic notebook cells execute directly in Python; notebook schema, catalog coverage, dependency DAG and tracked-path exclusions pass.
- [ ] Full HTTP and Jupyter execution on the host: local sandbox denies socket binding. Three HTTP integration tests and nbclient kernel startup fail at binding, before application assertions.
- [ ] Independent financial, behavioral, privacy, security and legal acceptance; publication to GitHub.

- [ ] Study and formalize: Reports, exports, UI tests, security, independent validation and paper trading.
- [ ] Document assumptions, formulas, data and units.
- [ ] Run the notebook on a fixture and analyze errors.
- [ ] Test analytical equivalence, edge cases and robustness.
- [ ] Extract code into the shared module.
- [ ] Write automated tests and make them pass.
- [ ] Add the API contract and relevant screen.
- [ ] Verify local rendering and update documentation.
- [ ] Create a PR, obtain review and merge.

### 27 — A. Detailed Tasks


- [x] **CH27.01** — Define versioned schemas ClientProfile, ConstraintSet, Card, MarketSnapshot, ForecastBundle, RiskReport, PortfolioCandidate, Evaluation and Selection.
  Evidence: src/riskmatch/contracts.py, architecture, synthetic notebook cell g00-contract-demo. Detailed mandate fields remain chapter 01.
- [x] **CH27.02** — Standardize as_of, run_id, versions, units, status, warnings and provenance on every output.
  Evidence: RunMetadata required on all new schema outputs; tests/unit/test_contracts.py verifies UTC, provenance and units. Legacy demo API remains explicitly experimental until CH27.07–08.
- [ ] **CH27.03** — Integrate the ten engines via explicit interfaces; reject failed/infeasible outputs before order simulation.
- [ ] **CH27.04** — Build mandate, behavioral discovery, score, universe/availability, asset analytics and strategy/optimizer configurator screens.
- [ ] **CH27.05** — Build interactive frontier, candidate matching, side-by-side comparison, exposure attribution, stress/fan chart and monitoring screens.
- [ ] **CH27.06** — Export weights.csv, positions.csv, trades.csv, nav.csv, metrics.json, exposures.csv, scenarios.csv, assumptions.json and audit log.
- [x] **CH27.07** — Define API routes for profiles, sessions/cards/responses, risk reports, portfolio runs/candidates/swipes and paper selection.
- [ ] **CH27.08** — Use schema validation, clear errors, idempotency and authorization by resource for multi-user future architecture.
- [x] **CH27.09** — Keep local-only services bound to loopback; verify actual start/stop procedures and port availability.
  Both services explicitly bind loopback and returned HTTP responses; both ports stopped responding after the owner ran STOP.command.
- [ ] **CH27.10** — Add privacy consent, role separation, data minimization, local storage backups and tested restoration.
- [x] **CH27.11** — Verify local-only data and secret exclusions, synthetic-only CI and solo access policy; require collaborator permissions before collaboration.
  Git path checks passed, no persisted notebook code outputs, no matches for sampled private-key/token patterns in tracked text. Not a comprehensive secret or license audit; verify dataset and asset distribution rights separately before redistribution. D003 defers collaborator controls until collaboration.
- [ ] **CH27.12** — Test UI accessibility, touch/keyboard, error/loading/empty states and responsive layouts.
- [ ] **CH27.13** — Execute unit, optimizer, regression, integration, workflow and reproducibility tests; log evidence per backlog task.
- [ ] **CH27.14** — Perform independent financial model, psychometric, privacy/security and applicable legal review before any real-service release.
- [ ] **CH27.15** — Run paper-trading reconciliation and failure drills; keep real order execution disabled.



## Catalog — 11 Client Objectives

Single notebook: chapter(s) 12. Each item is an independent deliverable.

### OBJ01 — Capital Preservation

- [x] **OBJ01.01** — Write the mathematical specification: P(W_T<W_0) and E[(W_0-W_T)+] in nominal and real terms. Specify units, convention, horizon and assumptions.
- [ ] **OBJ01.02** — Prepare dated inputs: initial capital, horizon, inflation, simulated losses. Define schema, provenance, coverage and availability checks.
- [ ] **OBJ01.03** — Implement the objective contract in the notebook using a synthetic fixture, then verify calculations and outputs by hand.
- [ ] **OBJ01.04** — Create the specific test: constant capital and inflation shock. Document expected result and tolerance.
- [ ] **OBJ01.05** — Test missing data, zero denominator/incompatible input and explicit failure without misleading results.
- [ ] **OBJ01.06** — Compare with a simple reference using identical dates, universe, constraints and costs; chronological out-of-sample protocol.
- [ ] **OBJ01.07** — Measure sensitivity to assumptions/parameters and uncertainty; record experiments and limitations.
- [ ] **OBJ01.08** — Extract a typed function into the shared engine; add unit and regression tests, version/config/diagnostics.
- [ ] **OBJ01.09** — Expose results and assumptions through API/UI, check mandate rules and publish a reproducible report.
- [ ] **OBJ01.10** — Attach results and tests to a PR; obtain independent review and check off only after acceptance.

### OBJ02 — Income

- [x] **OBJ02.01** — Write the mathematical specification: net income per period, coverage ratio and income volatility. Specify units, convention, horizon and assumptions.
- [ ] **OBJ02.02** — Prepare dated inputs: coupons, distributions, taxes, dated withdrawals. Define schema, provenance, coverage and availability checks.
- [ ] **OBJ02.03** — Implement the objective contract in the notebook using a synthetic fixture, then verify calculations and outputs by hand.
- [ ] **OBJ02.04** — Create the specific test: missing coupon and withdrawal exceeding income. Document expected result and tolerance.
- [ ] **OBJ02.05** — Test missing data, zero denominator/incompatible input and explicit failure without misleading results.
- [ ] **OBJ02.06** — Compare with a simple reference using identical dates, universe, constraints and costs; chronological out-of-sample protocol.
- [ ] **OBJ02.07** — Measure sensitivity to assumptions/parameters and uncertainty; record experiments and limitations.
- [ ] **OBJ02.08** — Extract a typed function into the shared engine; add unit and regression tests, version/config/diagnostics.
- [ ] **OBJ02.09** — Expose results and assumptions through API/UI, check mandate rules and publish a reproducible report.
- [ ] **OBJ02.10** — Attach results and tests to a PR; obtain independent review and check off only after acceptance.

### OBJ03 — Conservative

- [x] **OBJ03.01** — Write the mathematical specification: minimize risk subject to return and liquidity constraints. Specify units, convention, horizon and assumptions.
- [ ] **OBJ03.02** — Prepare dated inputs: volatility, ES and stress caps. Define schema, provenance, coverage and availability checks.
- [ ] **OBJ03.03** — Implement the objective contract in the notebook using a synthetic fixture, then verify calculations and outputs by hand.
- [ ] **OBJ03.04** — Create the specific test: stress exceeding the cap. Document expected result and tolerance.
- [ ] **OBJ03.05** — Test missing data, zero denominator/incompatible input and explicit failure without misleading results.
- [ ] **OBJ03.06** — Compare with a simple reference using identical dates, universe, constraints and costs; chronological out-of-sample protocol.
- [ ] **OBJ03.07** — Measure sensitivity to assumptions/parameters and uncertainty; record experiments and limitations.
- [ ] **OBJ03.08** — Extract a typed function into the shared engine; add unit and regression tests, version/config/diagnostics.
- [ ] **OBJ03.09** — Expose results and assumptions through API/UI, check mandate rules and publish a reproducible report.
- [ ] **OBJ03.10** — Attach results and tests to a PR; obtain independent review and check off only after acceptance.

### OBJ04 — Balanced

- [x] **OBJ04.01** — Write the mathematical specification: mean-variance utility and risk budget. Specify units, convention, horizon and assumptions.
- [ ] **OBJ04.02** — Prepare dated inputs: expected returns, covariance, risk-return preferences. Define schema, provenance, coverage and availability checks.
- [ ] **OBJ04.03** — Implement the objective contract in the notebook using a synthetic fixture, then verify calculations and outputs by hand.
- [ ] **OBJ04.04** — Create the specific test: two assets with opposing risk characteristics. Document expected result and tolerance.
- [ ] **OBJ04.05** — Test missing data, zero denominator/incompatible input and explicit failure without misleading results.
- [ ] **OBJ04.06** — Compare with a simple reference using identical dates, universe, constraints and costs; chronological out-of-sample protocol.
- [ ] **OBJ04.07** — Measure sensitivity to assumptions/parameters and uncertainty; record experiments and limitations.
- [ ] **OBJ04.08** — Extract a typed function into the shared engine; add unit and regression tests, version/config/diagnostics.
- [ ] **OBJ04.09** — Expose results and assumptions through API/UI, check mandate rules and publish a reproducible report.
- [ ] **OBJ04.10** — Attach results and tests to a PR; obtain independent review and check off only after acceptance.

### OBJ05 — Growth

- [x] **OBJ05.01** — Write the mathematical specification: E[W_T] and real CAGR subject to constraints. Specify units, convention, horizon and assumptions.
- [ ] **OBJ05.02** — Prepare dated inputs: horizon, contributions, inflation. Define schema, provenance, coverage and availability checks.
- [ ] **OBJ05.03** — Implement the objective contract in the notebook using a synthetic fixture, then verify calculations and outputs by hand.
- [ ] **OBJ05.04** — Create the specific test: short versus long horizon and contribution. Document expected result and tolerance.
- [ ] **OBJ05.05** — Test missing data, zero denominator/incompatible input and explicit failure without misleading results.
- [ ] **OBJ05.06** — Compare with a simple reference using identical dates, universe, constraints and costs; chronological out-of-sample protocol.
- [ ] **OBJ05.07** — Measure sensitivity to assumptions/parameters and uncertainty; record experiments and limitations.
- [ ] **OBJ05.08** — Extract a typed function into the shared engine; add unit and regression tests, version/config/diagnostics.
- [ ] **OBJ05.09** — Expose results and assumptions through API/UI, check mandate rules and publish a reproducible report.
- [ ] **OBJ05.10** — Attach results and tests to a PR; obtain independent review and check off only after acceptance.

### OBJ06 — Aggressive Growth

- [x] **OBJ06.01** — Write the mathematical specification: maximize growth subject to volatility/ES/leverage budget. Specify units, convention, horizon and assumptions.
- [ ] **OBJ06.02** — Prepare dated inputs: capital and explicitly validated high loss capacity. Define schema, provenance, coverage and availability checks.
- [ ] **OBJ06.03** — Implement the objective contract in the notebook using a synthetic fixture, then verify calculations and outputs by hand.
- [ ] **OBJ06.04** — Create the specific test: financial capacity conflicting with preferences. Document expected result and tolerance.
- [ ] **OBJ06.05** — Test missing data, zero denominator/incompatible input and explicit failure without misleading results.
- [ ] **OBJ06.06** — Compare with a simple reference using identical dates, universe, constraints and costs; chronological out-of-sample protocol.
- [ ] **OBJ06.07** — Measure sensitivity to assumptions/parameters and uncertainty; record experiments and limitations.
- [ ] **OBJ06.08** — Extract a typed function into the shared engine; add unit and regression tests, version/config/diagnostics.
- [ ] **OBJ06.09** — Expose results and assumptions through API/UI, check mandate rules and publish a reproducible report.
- [ ] **OBJ06.10** — Attach results and tests to a PR; obtain independent review and check off only after acceptance.

### OBJ07 — Inflation Protection

- [x] **OBJ07.01** — Write the mathematical specification: real return (1+r)/(1+π)-1 and CPI beta. Specify units, convention, horizon and assumptions.
- [ ] **OBJ07.02** — Prepare dated inputs: CPI vintages, TIPS, real yields. Define schema, provenance, coverage and availability checks.
- [ ] **OBJ07.03** — Implement the objective contract in the notebook using a synthetic fixture, then verify calculations and outputs by hand.
- [ ] **OBJ07.04** — Create the specific test: unexpected inflation. Document expected result and tolerance.
- [ ] **OBJ07.05** — Test missing data, zero denominator/incompatible input and explicit failure without misleading results.
- [ ] **OBJ07.06** — Compare with a simple reference using identical dates, universe, constraints and costs; chronological out-of-sample protocol.
- [ ] **OBJ07.07** — Measure sensitivity to assumptions/parameters and uncertainty; record experiments and limitations.
- [ ] **OBJ07.08** — Extract a typed function into the shared engine; add unit and regression tests, version/config/diagnostics.
- [ ] **OBJ07.09** — Expose results and assumptions through API/UI, check mandate rules and publish a reproducible report.
- [ ] **OBJ07.10** — Attach results and tests to a PR; obtain independent review and check off only after acceptance.

### OBJ08 — Absolute Return

- [x] **OBJ08.01** — Write the mathematical specification: net excess return over cash and downside. Specify units, convention, horizon and assumptions.
- [ ] **OBJ08.02** — Prepare dated inputs: cash/rf, loss threshold and fees. Define schema, provenance, coverage and availability checks.
- [ ] **OBJ08.03** — Implement the objective contract in the notebook using a synthetic fixture, then verify calculations and outputs by hand.
- [ ] **OBJ08.04** — Create the specific test: strong cash return and negative market. Document expected result and tolerance.
- [ ] **OBJ08.05** — Test missing data, zero denominator/incompatible input and explicit failure without misleading results.
- [ ] **OBJ08.06** — Compare with a simple reference using identical dates, universe, constraints and costs; chronological out-of-sample protocol.
- [ ] **OBJ08.07** — Measure sensitivity to assumptions/parameters and uncertainty; record experiments and limitations.
- [ ] **OBJ08.08** — Extract a typed function into the shared engine; add unit and regression tests, version/config/diagnostics.
- [ ] **OBJ08.09** — Expose results and assumptions through API/UI, check mandate rules and publish a reproducible report.
- [ ] **OBJ08.10** — Attach results and tests to a PR; obtain independent review and check off only after acceptance.

### OBJ09 — Liability-Driven (LDI)

- [x] **OBJ09.01** — Write the mathematical specification: asset-liability PV gap and DV01/key-rate mismatch. Specify units, convention, horizon and assumptions.
- [ ] **OBJ09.02** — Prepare dated inputs: discount curve, dated liabilities, coupons. Define schema, provenance, coverage and availability checks.
- [ ] **OBJ09.03** — Implement the objective contract in the notebook using a synthetic fixture, then verify calculations and outputs by hand.
- [ ] **OBJ09.04** — Create the specific test: known liability and parallel/nonparallel shock. Document expected result and tolerance.
- [ ] **OBJ09.05** — Test missing data, zero denominator/incompatible input and explicit failure without misleading results.
- [ ] **OBJ09.06** — Compare with a simple reference using identical dates, universe, constraints and costs; chronological out-of-sample protocol.
- [ ] **OBJ09.07** — Measure sensitivity to assumptions/parameters and uncertainty; record experiments and limitations.
- [ ] **OBJ09.08** — Extract a typed function into the shared engine; add unit and regression tests, version/config/diagnostics.
- [ ] **OBJ09.09** — Expose results and assumptions through API/UI, check mandate rules and publish a reproducible report.
- [ ] **OBJ09.10** — Attach results and tests to a PR; obtain independent review and check off only after acceptance.

### OBJ10 — Goal-Based

- [x] **OBJ10.01** — Write the mathematical specification: P(W_T≥G), E[(G-W_T)+], shortfall per goal. Specify units, convention, horizon and assumptions.
- [ ] **OBJ10.02** — Prepare dated inputs: multiple dated goals, flows, priorities. Define schema, provenance, coverage and availability checks.
- [ ] **OBJ10.03** — Implement the objective contract in the notebook using a synthetic fixture, then verify calculations and outputs by hand.
- [ ] **OBJ10.04** — Create the specific test: infeasible goal under risk cap. Document expected result and tolerance.
- [ ] **OBJ10.05** — Test missing data, zero denominator/incompatible input and explicit failure without misleading results.
- [ ] **OBJ10.06** — Compare with a simple reference using identical dates, universe, constraints and costs; chronological out-of-sample protocol.
- [ ] **OBJ10.07** — Measure sensitivity to assumptions/parameters and uncertainty; record experiments and limitations.
- [ ] **OBJ10.08** — Extract a typed function into the shared engine; add unit and regression tests, version/config/diagnostics.
- [ ] **OBJ10.09** — Expose results and assumptions through API/UI, check mandate rules and publish a reproducible report.
- [ ] **OBJ10.10** — Attach results and tests to a PR; obtain independent review and check off only after acceptance.

### OBJ11 — Capital Protection

- [x] **OBJ11.01** — Write the mathematical specification: loss below floor, hedge cost and gap stress. Specify units, convention, horizon and assumptions.
- [ ] **OBJ11.02** — Prepare dated inputs: conditional floor, hedging, costs, gap. Define schema, provenance, coverage and availability checks.
- [ ] **OBJ11.03** — Implement the objective contract in the notebook using a synthetic fixture, then verify calculations and outputs by hand.
- [ ] **OBJ11.04** — Create the specific test: gap below floor; no noncontractual guarantee. Document expected result and tolerance.
- [ ] **OBJ11.05** — Test missing data, zero denominator/incompatible input and explicit failure without misleading results.
- [ ] **OBJ11.06** — Compare with a simple reference using identical dates, universe, constraints and costs; chronological out-of-sample protocol.
- [ ] **OBJ11.07** — Measure sensitivity to assumptions/parameters and uncertainty; record experiments and limitations.
- [ ] **OBJ11.08** — Extract a typed function into the shared engine; add unit and regression tests, version/config/diagnostics.
- [ ] **OBJ11.09** — Expose results and assumptions through API/UI, check mandate rules and publish a reproducible report.
- [ ] **OBJ11.10** — Attach results and tests to a PR; obtain independent review and check off only after acceptance.

## Catalog — 22 Construction Methods

Single notebook: chapter(s) 13–18. Each item is an independent deliverable.

### OPT01 — Equal Weight

- [x] **OPT01.01** — Write the mathematical specification: w_i=1/N, projection onto constraints. Specify units, convention, horizon and assumptions.
- [ ] **OPT01.02** — Prepare dated inputs: eligible universe and bounds. Define schema, provenance, coverage and availability checks.
- [ ] **OPT01.03** — Implement the model in the notebook using a synthetic fixture, then verify calculations and outputs by hand.
- [ ] **OPT01.04** — Create the specific test: N=1 and incompatible concentration cap. Document expected result and tolerance.
- [ ] **OPT01.05** — Test missing data, zero denominator/incompatible input and explicit failure without misleading results.
- [ ] **OPT01.06** — Compare with a simple reference using identical dates, universe, constraints and costs; chronological out-of-sample protocol.
- [ ] **OPT01.07** — Measure sensitivity to assumptions/parameters and uncertainty; record experiments and limitations.
- [ ] **OPT01.08** — Extract a typed function into the shared engine; add unit and regression tests, version/config/diagnostics.
- [ ] **OPT01.09** — Expose results and assumptions through API/UI, check mandate rules and publish a reproducible report.
- [ ] **OPT01.10** — Attach results and tests to a PR; obtain independent review and check off only after acceptance.

### OPT02 — Market Cap Weighted

- [x] **OPT02.01** — Write the mathematical specification: w_i=cap_i/sum(cap). Specify units, convention, horizon and assumptions.
- [ ] **OPT02.02** — Prepare dated inputs: dated market caps and membership. Define schema, provenance, coverage and availability checks.
- [ ] **OPT02.03** — Implement the model in the notebook using a synthetic fixture, then verify calculations and outputs by hand.
- [ ] **OPT02.04** — Create the specific test: zero cap, delisting, no survivorship bias. Document expected result and tolerance.
- [ ] **OPT02.05** — Test missing data, zero denominator/incompatible input and explicit failure without misleading results.
- [ ] **OPT02.06** — Compare with a simple reference using identical dates, universe, constraints and costs; chronological out-of-sample protocol.
- [ ] **OPT02.07** — Measure sensitivity to assumptions/parameters and uncertainty; record experiments and limitations.
- [ ] **OPT02.08** — Extract a typed function into the shared engine; add unit and regression tests, version/config/diagnostics.
- [ ] **OPT02.09** — Expose results and assumptions through API/UI, check mandate rules and publish a reproducible report.
- [ ] **OPT02.10** — Attach results and tests to a PR; obtain independent review and check off only after acceptance.

### OPT03 — Minimum Variance

- [x] **OPT03.01** — Write the mathematical specification: min w'Σw. Specify units, convention, horizon and assumptions.
- [ ] **OPT03.02** — Prepare dated inputs: PSD Σ and limits. Define schema, provenance, coverage and availability checks.
- [ ] **OPT03.03** — Implement the model in the notebook using a synthetic fixture, then verify calculations and outputs by hand.
- [ ] **OPT03.04** — Create the specific test: analytical two-asset case and singular covariance. Document expected result and tolerance.
- [ ] **OPT03.05** — Test missing data, zero denominator/incompatible input and explicit failure without misleading results.
- [ ] **OPT03.06** — Compare with a simple reference using identical dates, universe, constraints and costs; chronological out-of-sample protocol.
- [ ] **OPT03.07** — Measure sensitivity to assumptions/parameters and uncertainty; record experiments and limitations.
- [ ] **OPT03.08** — Extract a typed function into the shared engine; add unit and regression tests, version/config/diagnostics.
- [ ] **OPT03.09** — Expose results and assumptions through API/UI, check mandate rules and publish a reproducible report.
- [ ] **OPT03.10** — Attach results and tests to a PR; obtain independent review and check off only after acceptance.

### OPT04 — Maximum Sharpe

- [x] **OPT04.01** — Write the mathematical specification: max (w'μ-rf)/sqrt(w'Σw). Specify units, convention, horizon and assumptions.
- [ ] **OPT04.02** — Prepare dated inputs: μ, Σ, rf. Define schema, provenance, coverage and availability checks.
- [ ] **OPT04.03** — Implement the model in the notebook using a synthetic fixture, then verify calculations and outputs by hand.
- [ ] **OPT04.04** — Create the specific test: negative excess return and zero variance. Document expected result and tolerance.
- [ ] **OPT04.05** — Test missing data, zero denominator/incompatible input and explicit failure without misleading results.
- [ ] **OPT04.06** — Compare with a simple reference using identical dates, universe, constraints and costs; chronological out-of-sample protocol.
- [ ] **OPT04.07** — Measure sensitivity to assumptions/parameters and uncertainty; record experiments and limitations.
- [ ] **OPT04.08** — Extract a typed function into the shared engine; add unit and regression tests, version/config/diagnostics.
- [ ] **OPT04.09** — Expose results and assumptions through API/UI, check mandate rules and publish a reproducible report.
- [ ] **OPT04.10** — Attach results and tests to a PR; obtain independent review and check off only after acceptance.

### OPT05 — Maximum Utility

- [x] **OPT05.01** — Write the mathematical specification: max w'μ-λw'Σw/2. Specify units, convention, horizon and assumptions.
- [ ] **OPT05.02** — Prepare dated inputs: μ, Σ, separately calibrated λ. Define schema, provenance, coverage and availability checks.
- [ ] **OPT05.03** — Implement the model in the notebook using a synthetic fixture, then verify calculations and outputs by hand.
- [ ] **OPT05.04** — Create the specific test: small/large λ and active constraints. Document expected result and tolerance.
- [ ] **OPT05.05** — Test missing data, zero denominator/incompatible input and explicit failure without misleading results.
- [ ] **OPT05.06** — Compare with a simple reference using identical dates, universe, constraints and costs; chronological out-of-sample protocol.
- [ ] **OPT05.07** — Measure sensitivity to assumptions/parameters and uncertainty; record experiments and limitations.
- [ ] **OPT05.08** — Extract a typed function into the shared engine; add unit and regression tests, version/config/diagnostics.
- [ ] **OPT05.09** — Expose results and assumptions through API/UI, check mandate rules and publish a reproducible report.
- [ ] **OPT05.10** — Attach results and tests to a PR; obtain independent review and check off only after acceptance.

### OPT06 — Efficient Frontier

- [x] **OPT06.01** — Write the mathematical specification: minimize variance for each target μ. Specify units, convention, horizon and assumptions.
- [ ] **OPT06.02** — Prepare dated inputs: μ, Σ, target grid. Define schema, provenance, coverage and availability checks.
- [ ] **OPT06.03** — Implement the model in the notebook using a synthetic fixture, then verify calculations and outputs by hand.
- [ ] **OPT06.04** — Create the specific test: monotone frontier and infeasible target. Document expected result and tolerance.
- [ ] **OPT06.05** — Test missing data, zero denominator/incompatible input and explicit failure without misleading results.
- [ ] **OPT06.06** — Compare with a simple reference using identical dates, universe, constraints and costs; chronological out-of-sample protocol.
- [ ] **OPT06.07** — Measure sensitivity to assumptions/parameters and uncertainty; record experiments and limitations.
- [ ] **OPT06.08** — Extract a typed function into the shared engine; add unit and regression tests, version/config/diagnostics.
- [ ] **OPT06.09** — Expose results and assumptions through API/UI, check mandate rules and publish a reproducible report.
- [ ] **OPT06.10** — Attach results and tests to a PR; obtain independent review and check off only after acceptance.

### OPT07 — Black-Litterman

- [x] **OPT07.01** — Write the mathematical specification: Bayesian posterior followed by optimization. Specify units, convention, horizon and assumptions.
- [ ] **OPT07.02** — Prepare dated inputs: market weights, δ, Σ, τ, P,q,Ω. Define schema, provenance, coverage and availability checks.
- [ ] **OPT07.03** — Implement the model in the notebook using a synthetic fixture, then verify calculations and outputs by hand.
- [ ] **OPT07.04** — Create the specific test: no views, weak/strong confidence, conflicting views. Document expected result and tolerance.
- [ ] **OPT07.05** — Test missing data, zero denominator/incompatible input and explicit failure without misleading results.
- [ ] **OPT07.06** — Compare with a simple reference using identical dates, universe, constraints and costs; chronological out-of-sample protocol.
- [ ] **OPT07.07** — Measure sensitivity to assumptions/parameters and uncertainty; record experiments and limitations.
- [ ] **OPT07.08** — Extract a typed function into the shared engine; add unit and regression tests, version/config/diagnostics.
- [ ] **OPT07.09** — Expose results and assumptions through API/UI, check mandate rules and publish a reproducible report.
- [ ] **OPT07.10** — Attach results and tests to a PR; obtain independent review and check off only after acceptance.

### OPT08 — Risk Parity

- [x] **OPT08.01** — Write the mathematical specification: RC_i=w_i(Σw)_i/σp=b_iσp. Specify units, convention, horizon and assumptions.
- [ ] **OPT08.02** — Prepare dated inputs: Σ, budgets b. Define schema, provenance, coverage and availability checks.
- [ ] **OPT08.03** — Implement the model in the notebook using a synthetic fixture, then verify calculations and outputs by hand.
- [ ] **OPT08.04** — Create the specific test: equal variance, perfect correlation and sum of RC. Document expected result and tolerance.
- [ ] **OPT08.05** — Test missing data, zero denominator/incompatible input and explicit failure without misleading results.
- [ ] **OPT08.06** — Compare with a simple reference using identical dates, universe, constraints and costs; chronological out-of-sample protocol.
- [ ] **OPT08.07** — Measure sensitivity to assumptions/parameters and uncertainty; record experiments and limitations.
- [ ] **OPT08.08** — Extract a typed function into the shared engine; add unit and regression tests, version/config/diagnostics.
- [ ] **OPT08.09** — Expose results and assumptions through API/UI, check mandate rules and publish a reproducible report.
- [ ] **OPT08.10** — Attach results and tests to a PR; obtain independent review and check off only after acceptance.

### OPT09 — Hierarchical Risk Parity

- [x] **OPT09.01** — Write the mathematical specification: distance sqrt((1-ρ)/2), clustering, bisection. Specify units, convention, horizon and assumptions.
- [ ] **OPT09.02** — Prepare dated inputs: Σ, correlation, linkage. Define schema, provenance, coverage and availability checks.
- [ ] **OPT09.03** — Implement the model in the notebook using a synthetic fixture, then verify calculations and outputs by hand.
- [ ] **OPT09.04** — Create the specific test: duplicate assets and linkage change. Document expected result and tolerance.
- [ ] **OPT09.05** — Test missing data, zero denominator/incompatible input and explicit failure without misleading results.
- [ ] **OPT09.06** — Compare with a simple reference using identical dates, universe, constraints and costs; chronological out-of-sample protocol.
- [ ] **OPT09.07** — Measure sensitivity to assumptions/parameters and uncertainty; record experiments and limitations.
- [ ] **OPT09.08** — Extract a typed function into the shared engine; add unit and regression tests, version/config/diagnostics.
- [ ] **OPT09.09** — Expose results and assumptions through API/UI, check mandate rules and publish a reproducible report.
- [ ] **OPT09.10** — Attach results and tests to a PR; obtain independent review and check off only after acceptance.

### OPT10 — Hierarchical Equal Risk Contribution

- [x] **OPT10.01** — Write the mathematical specification: hierarchical budgets and within-cluster allocation. Specify units, convention, horizon and assumptions.
- [ ] **OPT10.02** — Prepare dated inputs: clusters, Σ, budgets. Define schema, provenance, coverage and availability checks.
- [ ] **OPT10.03** — Implement the model in the notebook using a synthetic fixture, then verify calculations and outputs by hand.
- [ ] **OPT10.04** — Create the specific test: single cluster and cluster-count stability. Document expected result and tolerance.
- [ ] **OPT10.05** — Test missing data, zero denominator/incompatible input and explicit failure without misleading results.
- [ ] **OPT10.06** — Compare with a simple reference using identical dates, universe, constraints and costs; chronological out-of-sample protocol.
- [ ] **OPT10.07** — Measure sensitivity to assumptions/parameters and uncertainty; record experiments and limitations.
- [ ] **OPT10.08** — Extract a typed function into the shared engine; add unit and regression tests, version/config/diagnostics.
- [ ] **OPT10.09** — Expose results and assumptions through API/UI, check mandate rules and publish a reproducible report.
- [ ] **OPT10.10** — Attach results and tests to a PR; obtain independent review and check off only after acceptance.

### OPT11 — Maximum Diversification

- [x] **OPT11.01** — Write the mathematical specification: max w'σ / σp. Specify units, convention, horizon and assumptions.
- [ ] **OPT11.02** — Prepare dated inputs: Σ, individual σ. Define schema, provenance, coverage and availability checks.
- [ ] **OPT11.03** — Implement the model in the notebook using a synthetic fixture, then verify calculations and outputs by hand.
- [ ] **OPT11.04** — Create the specific test: identical correlation and zero volatility. Document expected result and tolerance.
- [ ] **OPT11.05** — Test missing data, zero denominator/incompatible input and explicit failure without misleading results.
- [ ] **OPT11.06** — Compare with a simple reference using identical dates, universe, constraints and costs; chronological out-of-sample protocol.
- [ ] **OPT11.07** — Measure sensitivity to assumptions/parameters and uncertainty; record experiments and limitations.
- [ ] **OPT11.08** — Extract a typed function into the shared engine; add unit and regression tests, version/config/diagnostics.
- [ ] **OPT11.09** — Expose results and assumptions through API/UI, check mandate rules and publish a reproducible report.
- [ ] **OPT11.10** — Attach results and tests to a PR; obtain independent review and check off only after acceptance.

### OPT12 — Minimum CVaR

- [x] **OPT12.01** — Write the mathematical specification: min z+sum p_s max(L_s-z,0)/(1-α). Specify units, convention, horizon and assumptions.
- [ ] **OPT12.02** — Prepare dated inputs: scenarios, probabilities, α. Define schema, provenance, coverage and availability checks.
- [ ] **OPT12.03** — Implement the model in the notebook using a synthetic fixture, then verify calculations and outputs by hand.
- [ ] **OPT12.04** — Create the specific test: discrete tail and analytical LP case. Document expected result and tolerance.
- [ ] **OPT12.05** — Test missing data, zero denominator/incompatible input and explicit failure without misleading results.
- [ ] **OPT12.06** — Compare with a simple reference using identical dates, universe, constraints and costs; chronological out-of-sample protocol.
- [ ] **OPT12.07** — Measure sensitivity to assumptions/parameters and uncertainty; record experiments and limitations.
- [ ] **OPT12.08** — Extract a typed function into the shared engine; add unit and regression tests, version/config/diagnostics.
- [ ] **OPT12.09** — Expose results and assumptions through API/UI, check mandate rules and publish a reproducible report.
- [ ] **OPT12.10** — Attach results and tests to a PR; obtain independent review and check off only after acceptance.

### OPT13 — Maximum Sortino

- [x] **OPT13.01** — Write the mathematical specification: max (E[r]-MAR)/sqrt(E[min(r-MAR,0)^2]). Specify units, convention, horizon and assumptions.
- [ ] **OPT13.02** — Prepare dated inputs: scenarios, MAR. Define schema, provenance, coverage and availability checks.
- [ ] **OPT13.03** — Implement the model in the notebook using a synthetic fixture, then verify calculations and outputs by hand.
- [ ] **OPT13.04** — Create the specific test: no downside and negative threshold. Document expected result and tolerance.
- [ ] **OPT13.05** — Test missing data, zero denominator/incompatible input and explicit failure without misleading results.
- [ ] **OPT13.06** — Compare with a simple reference using identical dates, universe, constraints and costs; chronological out-of-sample protocol.
- [ ] **OPT13.07** — Measure sensitivity to assumptions/parameters and uncertainty; record experiments and limitations.
- [ ] **OPT13.08** — Extract a typed function into the shared engine; add unit and regression tests, version/config/diagnostics.
- [ ] **OPT13.09** — Expose results and assumptions through API/UI, check mandate rules and publish a reproducible report.
- [ ] **OPT13.10** — Attach results and tests to a PR; obtain independent review and check off only after acceptance.

### OPT14 — Maximum Omega

- [x] **OPT14.01** — Write the mathematical specification: max E[(r-T)+]/E[(T-r)+]. Specify units, convention, horizon and assumptions.
- [ ] **OPT14.02** — Prepare dated inputs: scenarios, threshold T. Define schema, provenance, coverage and availability checks.
- [ ] **OPT14.03** — Implement the model in the notebook using a synthetic fixture, then verify calculations and outputs by hand.
- [ ] **OPT14.04** — Create the specific test: zero downside and equality at threshold. Document expected result and tolerance.
- [ ] **OPT14.05** — Test missing data, zero denominator/incompatible input and explicit failure without misleading results.
- [ ] **OPT14.06** — Compare with a simple reference using identical dates, universe, constraints and costs; chronological out-of-sample protocol.
- [ ] **OPT14.07** — Measure sensitivity to assumptions/parameters and uncertainty; record experiments and limitations.
- [ ] **OPT14.08** — Extract a typed function into the shared engine; add unit and regression tests, version/config/diagnostics.
- [ ] **OPT14.09** — Expose results and assumptions through API/UI, check mandate rules and publish a reproducible report.
- [ ] **OPT14.10** — Attach results and tests to a PR; obtain independent review and check off only after acceptance.

### OPT15 — Minimum Drawdown

- [x] **OPT15.01** — Write the mathematical specification: min max_t(1-NAV_t/peak_t) or CDaR. Specify units, convention, horizon and assumptions.
- [ ] **OPT15.02** — Prepare dated inputs: chronological paths. Define schema, provenance, coverage and availability checks.
- [ ] **OPT15.03** — Implement the model in the notebook using a synthetic fixture, then verify calculations and outputs by hand.
- [ ] **OPT15.04** — Create the specific test: same terminal return, different drawdowns. Document expected result and tolerance.
- [ ] **OPT15.05** — Test missing data, zero denominator/incompatible input and explicit failure without misleading results.
- [ ] **OPT15.06** — Compare with a simple reference using identical dates, universe, constraints and costs; chronological out-of-sample protocol.
- [ ] **OPT15.07** — Measure sensitivity to assumptions/parameters and uncertainty; record experiments and limitations.
- [ ] **OPT15.08** — Extract a typed function into the shared engine; add unit and regression tests, version/config/diagnostics.
- [ ] **OPT15.09** — Expose results and assumptions through API/UI, check mandate rules and publish a reproducible report.
- [ ] **OPT15.10** — Attach results and tests to a PR; obtain independent review and check off only after acceptance.

### OPT16 — Robust Optimization

- [x] **OPT16.01** — Write the mathematical specification: max_w min_θ U(w;θ). Specify units, convention, horizon and assumptions.
- [ ] **OPT16.02** — Prepare dated inputs: μ/Σ uncertainty sets. Define schema, provenance, coverage and availability checks.
- [ ] **OPT16.03** — Implement the model in the notebook using a synthetic fixture, then verify calculations and outputs by hand.
- [ ] **OPT16.04** — Create the specific test: singleton set recovers reference. Document expected result and tolerance.
- [ ] **OPT16.05** — Test missing data, zero denominator/incompatible input and explicit failure without misleading results.
- [ ] **OPT16.06** — Compare with a simple reference using identical dates, universe, constraints and costs; chronological out-of-sample protocol.
- [ ] **OPT16.07** — Measure sensitivity to assumptions/parameters and uncertainty; record experiments and limitations.
- [ ] **OPT16.08** — Extract a typed function into the shared engine; add unit and regression tests, version/config/diagnostics.
- [ ] **OPT16.09** — Expose results and assumptions through API/UI, check mandate rules and publish a reproducible report.
- [ ] **OPT16.10** — Attach results and tests to a PR; obtain independent review and check off only after acceptance.

### OPT17 — Resampled Efficient

- [x] **OPT17.01** — Write the mathematical specification: optimize each draw then aggregate. Specify units, convention, horizon and assumptions.
- [ ] **OPT17.02** — Prepare dated inputs: series, block bootstrap, seed. Define schema, provenance, coverage and availability checks.
- [ ] **OPT17.03** — Implement the model in the notebook using a synthetic fixture, then verify calculations and outputs by hand.
- [ ] **OPT17.04** — Create the specific test: reproducible seed and feasible aggregate weights. Document expected result and tolerance.
- [ ] **OPT17.05** — Test missing data, zero denominator/incompatible input and explicit failure without misleading results.
- [ ] **OPT17.06** — Compare with a simple reference using identical dates, universe, constraints and costs; chronological out-of-sample protocol.
- [ ] **OPT17.07** — Measure sensitivity to assumptions/parameters and uncertainty; record experiments and limitations.
- [ ] **OPT17.08** — Extract a typed function into the shared engine; add unit and regression tests, version/config/diagnostics.
- [ ] **OPT17.09** — Expose results and assumptions through API/UI, check mandate rules and publish a reproducible report.
- [ ] **OPT17.10** — Attach results and tests to a PR; obtain independent review and check off only after acceptance.

### OPT18 — Distributionally Robust

- [x] **OPT18.01** — Write the mathematical specification: optimize worst distribution in ambiguity set. Specify units, convention, horizon and assumptions.
- [ ] **OPT18.02** — Prepare dated inputs: empirical distribution, radius. Define schema, provenance, coverage and availability checks.
- [ ] **OPT18.03** — Implement the model in the notebook using a synthetic fixture, then verify calculations and outputs by hand.
- [ ] **OPT18.04** — Create the specific test: zero radius and radius sensitivity. Document expected result and tolerance.
- [ ] **OPT18.05** — Test missing data, zero denominator/incompatible input and explicit failure without misleading results.
- [ ] **OPT18.06** — Compare with a simple reference using identical dates, universe, constraints and costs; chronological out-of-sample protocol.
- [ ] **OPT18.07** — Measure sensitivity to assumptions/parameters and uncertainty; record experiments and limitations.
- [ ] **OPT18.08** — Extract a typed function into the shared engine; add unit and regression tests, version/config/diagnostics.
- [ ] **OPT18.09** — Expose results and assumptions through API/UI, check mandate rules and publish a reproducible report.
- [ ] **OPT18.10** — Attach results and tests to a PR; obtain independent review and check off only after acceptance.

### OPT19 — Kelly

- [x] **OPT19.01** — Write the mathematical specification: max E[log(1+w'r)], fractional Kelly. Specify units, convention, horizon and assumptions.
- [ ] **OPT19.02** — Prepare dated inputs: return distribution, wealth limits. Define schema, provenance, coverage and availability checks.
- [ ] **OPT19.03** — Implement the model in the notebook using a synthetic fixture, then verify calculations and outputs by hand.
- [ ] **OPT19.04** — Create the specific test: return near -100% and ruin. Document expected result and tolerance.
- [ ] **OPT19.05** — Test missing data, zero denominator/incompatible input and explicit failure without misleading results.
- [ ] **OPT19.06** — Compare with a simple reference using identical dates, universe, constraints and costs; chronological out-of-sample protocol.
- [ ] **OPT19.07** — Measure sensitivity to assumptions/parameters and uncertainty; record experiments and limitations.
- [ ] **OPT19.08** — Extract a typed function into the shared engine; add unit and regression tests, version/config/diagnostics.
- [ ] **OPT19.09** — Expose results and assumptions through API/UI, check mandate rules and publish a reproducible report.
- [ ] **OPT19.10** — Attach results and tests to a PR; obtain independent review and check off only after acceptance.

### OPT20 — Entropy-Based

- [x] **OPT20.01** — Write the mathematical specification: max -sum w log(w). Specify units, convention, horizon and assumptions.
- [ ] **OPT20.02** — Prepare dated inputs: positive weights, risk/return limits. Define schema, provenance, coverage and availability checks.
- [ ] **OPT20.03** — Implement the model in the notebook using a synthetic fixture, then verify calculations and outputs by hand.
- [ ] **OPT20.04** — Create the specific test: unconstrained solution recovers 1/N and 0log0. Document expected result and tolerance.
- [ ] **OPT20.05** — Test missing data, zero denominator/incompatible input and explicit failure without misleading results.
- [ ] **OPT20.06** — Compare with a simple reference using identical dates, universe, constraints and costs; chronological out-of-sample protocol.
- [ ] **OPT20.07** — Measure sensitivity to assumptions/parameters and uncertainty; record experiments and limitations.
- [ ] **OPT20.08** — Extract a typed function into the shared engine; add unit and regression tests, version/config/diagnostics.
- [ ] **OPT20.09** — Expose results and assumptions through API/UI, check mandate rules and publish a reproducible report.
- [ ] **OPT20.10** — Attach results and tests to a PR; obtain independent review and check off only after acceptance.

### OPT21 — Tracking Error Min

- [x] **OPT21.01** — Write the mathematical specification: min (w-b)'Σ(w-b). Specify units, convention, horizon and assumptions.
- [ ] **OPT21.02** — Prepare dated inputs: Σ and benchmark b. Define schema, provenance, coverage and availability checks.
- [ ] **OPT21.03** — Implement the model in the notebook using a synthetic fixture, then verify calculations and outputs by hand.
- [ ] **OPT21.04** — Create the specific test: w=b gives TE=0 and incompatible benchmark. Document expected result and tolerance.
- [ ] **OPT21.05** — Test missing data, zero denominator/incompatible input and explicit failure without misleading results.
- [ ] **OPT21.06** — Compare with a simple reference using identical dates, universe, constraints and costs; chronological out-of-sample protocol.
- [ ] **OPT21.07** — Measure sensitivity to assumptions/parameters and uncertainty; record experiments and limitations.
- [ ] **OPT21.08** — Extract a typed function into the shared engine; add unit and regression tests, version/config/diagnostics.
- [ ] **OPT21.09** — Expose results and assumptions through API/UI, check mandate rules and publish a reproducible report.
- [ ] **OPT21.10** — Attach results and tests to a PR; obtain independent review and check off only after acceptance.

### OPT22 — Maximum Information Ratio

- [x] **OPT22.01** — Write the mathematical specification: max (w-b)'μ/sqrt((w-b)'Σ(w-b)). Specify units, convention, horizon and assumptions.
- [ ] **OPT22.02** — Prepare dated inputs: active α, Σ, benchmark b. Define schema, provenance, coverage and availability checks.
- [ ] **OPT22.03** — Implement the model in the notebook using a synthetic fixture, then verify calculations and outputs by hand.
- [ ] **OPT22.04** — Create the specific test: w=b gives zero denominator. Document expected result and tolerance.
- [ ] **OPT22.05** — Test missing data, zero denominator/incompatible input and explicit failure without misleading results.
- [ ] **OPT22.06** — Compare with a simple reference using identical dates, universe, constraints and costs; chronological out-of-sample protocol.
- [ ] **OPT22.07** — Measure sensitivity to assumptions/parameters and uncertainty; record experiments and limitations.
- [ ] **OPT22.08** — Extract a typed function into the shared engine; add unit and regression tests, version/config/diagnostics.
- [ ] **OPT22.09** — Expose results and assumptions through API/UI, check mandate rules and publish a reproducible report.
- [ ] **OPT22.10** — Attach results and tests to a PR; obtain independent review and check off only after acceptance.

## Catalog — 19 Strategies

Single notebook: chapter(s) 19–20. Each item is an independent deliverable.

### STR01 — Passive

- [x] **STR01.01** — Write the mathematical specification: replication/sampling with tracking error. Specify units, convention, horizon and assumptions.
- [ ] **STR01.02** — Prepare dated inputs: historical membership and index weights. Define schema, provenance, coverage and availability checks.
- [ ] **STR01.03** — Implement the signal and positioning engine in the notebook using a synthetic fixture, then verify calculations and outputs by hand.
- [ ] **STR01.04** — Create the specific test: index reconstitution and fees. Document expected result and tolerance.
- [ ] **STR01.05** — Test missing data, zero denominator/incompatible input and explicit failure without misleading results.
- [ ] **STR01.06** — Compare with a simple reference using identical dates, universe, constraints and costs; chronological out-of-sample protocol.
- [ ] **STR01.07** — Measure sensitivity to assumptions/parameters and uncertainty; record experiments and limitations.
- [ ] **STR01.08** — Extract a typed function into the shared engine; add unit and regression tests, version/config/diagnostics.
- [ ] **STR01.09** — Expose results and assumptions through API/UI, check mandate rules and publish a reproducible report.
- [ ] **STR01.10** — Attach results and tests to a PR; obtain independent review and check off only after acceptance.

### STR02 — Active Long Only

- [x] **STR02.01** — Write the mathematical specification: rank then optimize w≥0. Specify units, convention, horizon and assumptions.
- [ ] **STR02.02** — Prepare dated inputs: dated alpha scores, prices. Define schema, provenance, coverage and availability checks.
- [ ] **STR02.03** — Implement the signal and positioning engine in the notebook using a synthetic fixture, then verify calculations and outputs by hand.
- [ ] **STR02.04** — Create the specific test: constant signal and passive benchmark. Document expected result and tolerance.
- [ ] **STR02.05** — Test missing data, zero denominator/incompatible input and explicit failure without misleading results.
- [ ] **STR02.06** — Compare with a simple reference using identical dates, universe, constraints and costs; chronological out-of-sample protocol.
- [ ] **STR02.07** — Measure sensitivity to assumptions/parameters and uncertainty; record experiments and limitations.
- [ ] **STR02.08** — Extract a typed function into the shared engine; add unit and regression tests, version/config/diagnostics.
- [ ] **STR02.09** — Expose results and assumptions through API/UI, check mandate rules and publish a reproducible report.
- [ ] **STR02.10** — Attach results and tests to a PR; obtain independent review and check off only after acceptance.

### STR03 — Long/Short

- [x] **STR03.01** — Write the mathematical specification: long high scores/short low scores; gross/net limits. Specify units, convention, horizon and assumptions.
- [ ] **STR03.02** — Prepare dated inputs: scores, borrowing availability, borrow cost, collateral. Define schema, provenance, coverage and availability checks.
- [ ] **STR03.03** — Implement the signal and positioning engine in the notebook using a synthetic fixture, then verify calculations and outputs by hand.
- [ ] **STR03.04** — Create the specific test: unavailable shorts and higher borrow costs. Document expected result and tolerance.
- [ ] **STR03.05** — Test missing data, zero denominator/incompatible input and explicit failure without misleading results.
- [ ] **STR03.06** — Compare with a simple reference using identical dates, universe, constraints and costs; chronological out-of-sample protocol.
- [ ] **STR03.07** — Measure sensitivity to assumptions/parameters and uncertainty; record experiments and limitations.
- [ ] **STR03.08** — Extract a typed function into the shared engine; add unit and regression tests, version/config/diagnostics.
- [ ] **STR03.09** — Expose results and assumptions through API/UI, check mandate rules and publish a reproducible report.
- [ ] **STR03.10** — Attach results and tests to a PR; obtain independent review and check off only after acceptance.

### STR04 — Market Neutral

- [x] **STR04.01** — Write the mathematical specification: β'w≈0; optional dollar neutrality. Specify units, convention, horizon and assumptions.
- [ ] **STR04.02** — Prepare dated inputs: β exposures, borrow. Define schema, provenance, coverage and availability checks.
- [ ] **STR04.03** — Implement the signal and positioning engine in the notebook using a synthetic fixture, then verify calculations and outputs by hand.
- [ ] **STR04.04** — Create the specific test: ex-ante neutrality versus realized beta. Document expected result and tolerance.
- [ ] **STR04.05** — Test missing data, zero denominator/incompatible input and explicit failure without misleading results.
- [ ] **STR04.06** — Compare with a simple reference using identical dates, universe, constraints and costs; chronological out-of-sample protocol.
- [ ] **STR04.07** — Measure sensitivity to assumptions/parameters and uncertainty; record experiments and limitations.
- [ ] **STR04.08** — Extract a typed function into the shared engine; add unit and regression tests, version/config/diagnostics.
- [ ] **STR04.09** — Expose results and assumptions through API/UI, check mandate rules and publish a reproducible report.
- [ ] **STR04.10** — Attach results and tests to a PR; obtain independent review and check off only after acceptance.

### STR05 — Global Macro

- [x] **STR05.01** — Write the mathematical specification: dated macro surprise signals. Specify units, convention, horizon and assumptions.
- [ ] **STR05.02** — Prepare dated inputs: growth/inflation/rate vintages. Define schema, provenance, coverage and availability checks.
- [ ] **STR05.03** — Implement the signal and positioning engine in the notebook using a synthetic fixture, then verify calculations and outputs by hand.
- [ ] **STR05.04** — Create the specific test: later revisions do not change earlier signal. Document expected result and tolerance.
- [ ] **STR05.05** — Test missing data, zero denominator/incompatible input and explicit failure without misleading results.
- [ ] **STR05.06** — Compare with a simple reference using identical dates, universe, constraints and costs; chronological out-of-sample protocol.
- [ ] **STR05.07** — Measure sensitivity to assumptions/parameters and uncertainty; record experiments and limitations.
- [ ] **STR05.08** — Extract a typed function into the shared engine; add unit and regression tests, version/config/diagnostics.
- [ ] **STR05.09** — Expose results and assumptions through API/UI, check mandate rules and publish a reproducible report.
- [ ] **STR05.10** — Attach results and tests to a PR; obtain independent review and check off only after acceptance.

### STR06 — Managed Futures / CTA

- [x] **STR06.01** — Write the mathematical specification: time-series momentum + volatility scaling. Specify units, convention, horizon and assumptions.
- [ ] **STR06.02** — Prepare dated inputs: actual contracts, trend, margin. Define schema, provenance, coverage and availability checks.
- [ ] **STR06.03** — Implement the signal and positioning engine in the notebook using a synthetic fixture, then verify calculations and outputs by hand.
- [ ] **STR06.04** — Create the specific test: roll and trendless market. Document expected result and tolerance.
- [ ] **STR06.05** — Test missing data, zero denominator/incompatible input and explicit failure without misleading results.
- [ ] **STR06.06** — Compare with a simple reference using identical dates, universe, constraints and costs; chronological out-of-sample protocol.
- [ ] **STR06.07** — Measure sensitivity to assumptions/parameters and uncertainty; record experiments and limitations.
- [ ] **STR06.08** — Extract a typed function into the shared engine; add unit and regression tests, version/config/diagnostics.
- [ ] **STR06.09** — Expose results and assumptions through API/UI, check mandate rules and publish a reproducible report.
- [ ] **STR06.10** — Attach results and tests to a PR; obtain independent review and check off only after acceptance.

### STR07 — Multi-Strategy

- [x] **STR07.01** — Write the mathematical specification: combine budgets without duplicate exposure. Specify units, convention, horizon and assumptions.
- [ ] **STR07.02** — Prepare dated inputs: sleeves, correlations, costs. Define schema, provenance, coverage and availability checks.
- [ ] **STR07.03** — Implement the signal and positioning engine in the notebook using a synthetic fixture, then verify calculations and outputs by hand.
- [ ] **STR07.04** — Create the specific test: crisis correlation and failed sleeve. Document expected result and tolerance.
- [ ] **STR07.05** — Test missing data, zero denominator/incompatible input and explicit failure without misleading results.
- [ ] **STR07.06** — Compare with a simple reference using identical dates, universe, constraints and costs; chronological out-of-sample protocol.
- [ ] **STR07.07** — Measure sensitivity to assumptions/parameters and uncertainty; record experiments and limitations.
- [ ] **STR07.08** — Extract a typed function into the shared engine; add unit and regression tests, version/config/diagnostics.
- [ ] **STR07.09** — Expose results and assumptions through API/UI, check mandate rules and publish a reproducible report.
- [ ] **STR07.10** — Attach results and tests to a PR; obtain independent review and check off only after acceptance.

### STR08 — Statistical Arbitrage

- [x] **STR08.01** — Write the mathematical specification: cointegration and train-only z-score. Specify units, convention, horizon and assumptions.
- [ ] **STR08.02** — Prepare dated inputs: pairs/spreads, prices, borrow. Define schema, provenance, coverage and availability checks.
- [ ] **STR08.03** — Implement the signal and positioning engine in the notebook using a synthetic fixture, then verify calculations and outputs by hand.
- [ ] **STR08.04** — Create the specific test: relationship breakdown. Document expected result and tolerance.
- [ ] **STR08.05** — Test missing data, zero denominator/incompatible input and explicit failure without misleading results.
- [ ] **STR08.06** — Compare with a simple reference using identical dates, universe, constraints and costs; chronological out-of-sample protocol.
- [ ] **STR08.07** — Measure sensitivity to assumptions/parameters and uncertainty; record experiments and limitations.
- [ ] **STR08.08** — Extract a typed function into the shared engine; add unit and regression tests, version/config/diagnostics.
- [ ] **STR08.09** — Expose results and assumptions through API/UI, check mandate rules and publish a reproducible report.
- [ ] **STR08.10** — Attach results and tests to a PR; obtain independent review and check off only after acceptance.

### STR09 — Factor Investing

- [x] **STR09.01** — Write the mathematical specification: rank and allocate by factor. Specify units, convention, horizon and assumptions.
- [ ] **STR09.02** — Prepare dated inputs: 13 factor scores, PIT data. Define schema, provenance, coverage and availability checks.
- [ ] **STR09.03** — Implement the signal and positioning engine in the notebook using a synthetic fixture, then verify calculations and outputs by hand.
- [ ] **STR09.04** — Create the specific test: neutralization and unavailable factor. Document expected result and tolerance.
- [ ] **STR09.05** — Test missing data, zero denominator/incompatible input and explicit failure without misleading results.
- [ ] **STR09.06** — Compare with a simple reference using identical dates, universe, constraints and costs; chronological out-of-sample protocol.
- [ ] **STR09.07** — Measure sensitivity to assumptions/parameters and uncertainty; record experiments and limitations.
- [ ] **STR09.08** — Extract a typed function into the shared engine; add unit and regression tests, version/config/diagnostics.
- [ ] **STR09.09** — Expose results and assumptions through API/UI, check mandate rules and publish a reproducible report.
- [ ] **STR09.10** — Attach results and tests to a PR; obtain independent review and check off only after acceptance.

### STR10 — Smart Beta

- [x] **STR10.01** — Write the mathematical specification: alternative to cap weighting. Specify units, convention, horizon and assumptions.
- [ ] **STR10.02** — Prepare dated inputs: market cap, fundamentals, factors. Define schema, provenance, coverage and availability checks.
- [ ] **STR10.03** — Implement the signal and positioning engine in the notebook using a synthetic fixture, then verify calculations and outputs by hand.
- [ ] **STR10.04** — Create the specific test: concentration and rebalancing. Document expected result and tolerance.
- [ ] **STR10.05** — Test missing data, zero denominator/incompatible input and explicit failure without misleading results.
- [ ] **STR10.06** — Compare with a simple reference using identical dates, universe, constraints and costs; chronological out-of-sample protocol.
- [ ] **STR10.07** — Measure sensitivity to assumptions/parameters and uncertainty; record experiments and limitations.
- [ ] **STR10.08** — Extract a typed function into the shared engine; add unit and regression tests, version/config/diagnostics.
- [ ] **STR10.09** — Expose results and assumptions through API/UI, check mandate rules and publish a reproducible report.
- [ ] **STR10.10** — Attach results and tests to a PR; obtain independent review and check off only after acceptance.

### STR11 — Carry

- [x] **STR11.01** — Write the mathematical specification: rank net carry by instrument. Specify units, convention, horizon and assumptions.
- [ ] **STR11.02** — Prepare dated inputs: curves, funding, contract prices. Define schema, provenance, coverage and availability checks.
- [ ] **STR11.03** — Implement the signal and positioning engine in the notebook using a synthetic fixture, then verify calculations and outputs by hand.
- [ ] **STR11.04** — Create the specific test: curve inversion and crash. Document expected result and tolerance.
- [ ] **STR11.05** — Test missing data, zero denominator/incompatible input and explicit failure without misleading results.
- [ ] **STR11.06** — Compare with a simple reference using identical dates, universe, constraints and costs; chronological out-of-sample protocol.
- [ ] **STR11.07** — Measure sensitivity to assumptions/parameters and uncertainty; record experiments and limitations.
- [ ] **STR11.08** — Extract a typed function into the shared engine; add unit and regression tests, version/config/diagnostics.
- [ ] **STR11.09** — Expose results and assumptions through API/UI, check mandate rules and publish a reproducible report.
- [ ] **STR11.10** — Attach results and tests to a PR; obtain independent review and check off only after acceptance.

### STR12 — Momentum

- [x] **STR12.01** — Write the mathematical specification: 12–1 months and time-series trend. Specify units, convention, horizon and assumptions.
- [ ] **STR12.02** — Prepare dated inputs: lagged returns. Define schema, provenance, coverage and availability checks.
- [ ] **STR12.03** — Implement the signal and positioning engine in the notebook using a synthetic fixture, then verify calculations and outputs by hand.
- [ ] **STR12.04** — Create the specific test: reversal, no look-ahead. Document expected result and tolerance.
- [ ] **STR12.05** — Test missing data, zero denominator/incompatible input and explicit failure without misleading results.
- [ ] **STR12.06** — Compare with a simple reference using identical dates, universe, constraints and costs; chronological out-of-sample protocol.
- [ ] **STR12.07** — Measure sensitivity to assumptions/parameters and uncertainty; record experiments and limitations.
- [ ] **STR12.08** — Extract a typed function into the shared engine; add unit and regression tests, version/config/diagnostics.
- [ ] **STR12.09** — Expose results and assumptions through API/UI, check mandate rules and publish a reproducible report.
- [ ] **STR12.10** — Attach results and tests to a PR; obtain independent review and check off only after acceptance.

### STR13 — Mean Reversion

- [x] **STR13.01** — Write the mathematical specification: z-score, entry/exit threshold. Specify units, convention, horizon and assumptions.
- [ ] **STR13.02** — Prepare dated inputs: historical price/spread. Define schema, provenance, coverage and availability checks.
- [ ] **STR13.03** — Implement the signal and positioning engine in the notebook using a synthetic fixture, then verify calculations and outputs by hand.
- [ ] **STR13.04** — Create the specific test: nonstationary spread. Document expected result and tolerance.
- [ ] **STR13.05** — Test missing data, zero denominator/incompatible input and explicit failure without misleading results.
- [ ] **STR13.06** — Compare with a simple reference using identical dates, universe, constraints and costs; chronological out-of-sample protocol.
- [ ] **STR13.07** — Measure sensitivity to assumptions/parameters and uncertainty; record experiments and limitations.
- [ ] **STR13.08** — Extract a typed function into the shared engine; add unit and regression tests, version/config/diagnostics.
- [ ] **STR13.09** — Expose results and assumptions through API/UI, check mandate rules and publish a reproducible report.
- [ ] **STR13.10** — Attach results and tests to a PR; obtain independent review and check off only after acceptance.

### STR14 — Tactical Asset Allocation

- [x] **STR14.01** — Write the mathematical specification: bounded deviations and rebalancing. Specify units, convention, horizon and assumptions.
- [ ] **STR14.02** — Prepare dated inputs: strategic allocation, signals. Define schema, provenance, coverage and availability checks.
- [ ] **STR14.03** — Implement the signal and positioning engine in the notebook using a synthetic fixture, then verify calculations and outputs by hand.
- [ ] **STR14.04** — Create the specific test: zero signal recovers strategic allocation. Document expected result and tolerance.
- [ ] **STR14.05** — Test missing data, zero denominator/incompatible input and explicit failure without misleading results.
- [ ] **STR14.06** — Compare with a simple reference using identical dates, universe, constraints and costs; chronological out-of-sample protocol.
- [ ] **STR14.07** — Measure sensitivity to assumptions/parameters and uncertainty; record experiments and limitations.
- [ ] **STR14.08** — Extract a typed function into the shared engine; add unit and regression tests, version/config/diagnostics.
- [ ] **STR14.09** — Expose results and assumptions through API/UI, check mandate rules and publish a reproducible report.
- [ ] **STR14.10** — Attach results and tests to a PR; obtain independent review and check off only after acceptance.

### STR15 — Core-Satellite

- [x] **STR15.01** — Write the mathematical specification: active risk budgets and aggregation. Specify units, convention, horizon and assumptions.
- [ ] **STR15.02** — Prepare dated inputs: core, active sleeves. Define schema, provenance, coverage and availability checks.
- [ ] **STR15.03** — Implement the signal and positioning engine in the notebook using a synthetic fixture, then verify calculations and outputs by hand.
- [ ] **STR15.04** — Create the specific test: missing satellite and duplicates. Document expected result and tolerance.
- [ ] **STR15.05** — Test missing data, zero denominator/incompatible input and explicit failure without misleading results.
- [ ] **STR15.06** — Compare with a simple reference using identical dates, universe, constraints and costs; chronological out-of-sample protocol.
- [ ] **STR15.07** — Measure sensitivity to assumptions/parameters and uncertainty; record experiments and limitations.
- [ ] **STR15.08** — Extract a typed function into the shared engine; add unit and regression tests, version/config/diagnostics.
- [ ] **STR15.09** — Expose results and assumptions through API/UI, check mandate rules and publish a reproducible report.
- [ ] **STR15.10** — Attach results and tests to a PR; obtain independent review and check off only after acceptance.

### STR16 — Volatility Targeting

- [x] **STR16.01** — Write the mathematical specification: scale=min(cap,σ_target/σ_forecast). Specify units, convention, horizon and assumptions.
- [ ] **STR16.02** — Prepare dated inputs: forecast σ, costs, exposure. Define schema, provenance, coverage and availability checks.
- [ ] **STR16.03** — Implement the signal and positioning engine in the notebook using a synthetic fixture, then verify calculations and outputs by hand.
- [ ] **STR16.04** — Create the specific test: zero σ and volatility shock. Document expected result and tolerance.
- [ ] **STR16.05** — Test missing data, zero denominator/incompatible input and explicit failure without misleading results.
- [ ] **STR16.06** — Compare with a simple reference using identical dates, universe, constraints and costs; chronological out-of-sample protocol.
- [ ] **STR16.07** — Measure sensitivity to assumptions/parameters and uncertainty; record experiments and limitations.
- [ ] **STR16.08** — Extract a typed function into the shared engine; add unit and regression tests, version/config/diagnostics.
- [ ] **STR16.09** — Expose results and assumptions through API/UI, check mandate rules and publish a reproducible report.
- [ ] **STR16.10** — Attach results and tests to a PR; obtain independent review and check off only after acceptance.

### STR17 — All Weather

- [x] **STR17.01** — Write the mathematical specification: balance regime and risk exposures. Specify units, convention, horizon and assumptions.
- [ ] **STR17.02** — Prepare dated inputs: inflation, growth, curves. Define schema, provenance, coverage and availability checks.
- [ ] **STR17.03** — Implement the signal and positioning engine in the notebook using a synthetic fixture, then verify calculations and outputs by hand.
- [ ] **STR17.04** — Create the specific test: equities and Treasuries fall together. Document expected result and tolerance.
- [ ] **STR17.05** — Test missing data, zero denominator/incompatible input and explicit failure without misleading results.
- [ ] **STR17.06** — Compare with a simple reference using identical dates, universe, constraints and costs; chronological out-of-sample protocol.
- [ ] **STR17.07** — Measure sensitivity to assumptions/parameters and uncertainty; record experiments and limitations.
- [ ] **STR17.08** — Extract a typed function into the shared engine; add unit and regression tests, version/config/diagnostics.
- [ ] **STR17.09** — Expose results and assumptions through API/UI, check mandate rules and publish a reproducible report.
- [ ] **STR17.10** — Attach results and tests to a PR; obtain independent review and check off only after acceptance.

### STR18 — Regime Switching

- [x] **STR18.01** — Write the mathematical specification: allocate using filtered probabilities. Specify units, convention, horizon and assumptions.
- [ ] **STR18.02** — Prepare dated inputs: features, states, transitions. Define schema, provenance, coverage and availability checks.
- [ ] **STR18.03** — Implement the signal and positioning engine in the notebook using a synthetic fixture, then verify calculations and outputs by hand.
- [ ] **STR18.04** — Create the specific test: regime change and uncertain state. Document expected result and tolerance.
- [ ] **STR18.05** — Test missing data, zero denominator/incompatible input and explicit failure without misleading results.
- [ ] **STR18.06** — Compare with a simple reference using identical dates, universe, constraints and costs; chronological out-of-sample protocol.
- [ ] **STR18.07** — Measure sensitivity to assumptions/parameters and uncertainty; record experiments and limitations.
- [ ] **STR18.08** — Extract a typed function into the shared engine; add unit and regression tests, version/config/diagnostics.
- [ ] **STR18.09** — Expose results and assumptions through API/UI, check mandate rules and publish a reproducible report.
- [ ] **STR18.10** — Attach results and tests to a PR; obtain independent review and check off only after acceptance.

### STR19 — Tail Risk Hedging

- [x] **STR19.01** — Write the mathematical specification: conditional hedge, gap risk and cost. Specify units, convention, horizon and assumptions.
- [ ] **STR19.02** — Prepare dated inputs: scenarios, hedges and costs. Define schema, provenance, coverage and availability checks.
- [ ] **STR19.03** — Implement the signal and positioning engine in the notebook using a synthetic fixture, then verify calculations and outputs by hand.
- [ ] **STR19.04** — Create the specific test: sudden crash and calm-market cost. Document expected result and tolerance.
- [ ] **STR19.05** — Test missing data, zero denominator/incompatible input and explicit failure without misleading results.
- [ ] **STR19.06** — Compare with a simple reference using identical dates, universe, constraints and costs; chronological out-of-sample protocol.
- [ ] **STR19.07** — Measure sensitivity to assumptions/parameters and uncertainty; record experiments and limitations.
- [ ] **STR19.08** — Extract a typed function into the shared engine; add unit and regression tests, version/config/diagnostics.
- [ ] **STR19.09** — Expose results and assumptions through API/UI, check mandate rules and publish a reproducible report.
- [ ] **STR19.10** — Attach results and tests to a PR; obtain independent review and check off only after acceptance.

## Catalog — 13 Factors

Single notebook: chapter(s) 10. Each item is an independent deliverable.

### FAC01 — Market

- [x] **FAC01.01** — Write the mathematical specification: OLS excess-return beta versus market. Specify units, convention, horizon and assumptions.
- [ ] **FAC01.02** — Prepare dated inputs: market total return, rf. Define schema, provenance, coverage and availability checks.
- [ ] **FAC01.03** — Implement the factor and exposure in the notebook using a synthetic fixture, then verify calculations and outputs by hand.
- [ ] **FAC01.04** — Create the specific test: unit beta on market. Document expected result and tolerance.
- [ ] **FAC01.05** — Test missing data, zero denominator/incompatible input and explicit failure without misleading results.
- [ ] **FAC01.06** — Compare with a simple reference using identical dates, universe, constraints and costs; chronological out-of-sample protocol.
- [ ] **FAC01.07** — Measure sensitivity to assumptions/parameters and uncertainty; record experiments and limitations.
- [ ] **FAC01.08** — Extract a typed function into the shared engine; add unit and regression tests, version/config/diagnostics.
- [ ] **FAC01.09** — Expose results and assumptions through API/UI, check mandate rules and publish a reproducible report.
- [ ] **FAC01.10** — Attach results and tests to a PR; obtain independent review and check off only after acceptance.

### FAC02 — Value

- [x] **FAC02.01** — Write the mathematical specification: book-to-market or earnings yield. Specify units, convention, horizon and assumptions.
- [ ] **FAC02.02** — Prepare dated inputs: book equity, earnings, prices available at t. Define schema, provenance, coverage and availability checks.
- [ ] **FAC02.03** — Implement the factor and exposure in the notebook using a synthetic fixture, then verify calculations and outputs by hand.
- [ ] **FAC02.04** — Create the specific test: exclude later financial statements. Document expected result and tolerance.
- [ ] **FAC02.05** — Test missing data, zero denominator/incompatible input and explicit failure without misleading results.
- [ ] **FAC02.06** — Compare with a simple reference using identical dates, universe, constraints and costs; chronological out-of-sample protocol.
- [ ] **FAC02.07** — Measure sensitivity to assumptions/parameters and uncertainty; record experiments and limitations.
- [ ] **FAC02.08** — Extract a typed function into the shared engine; add unit and regression tests, version/config/diagnostics.
- [ ] **FAC02.09** — Expose results and assumptions through API/UI, check mandate rules and publish a reproducible report.
- [ ] **FAC02.10** — Attach results and tests to a PR; obtain independent review and check off only after acceptance.

### FAC03 — Size

- [x] **FAC03.01** — Write the mathematical specification: log market cap, SMB. Specify units, convention, horizon and assumptions.
- [ ] **FAC03.02** — Prepare dated inputs: dated market capitalization. Define schema, provenance, coverage and availability checks.
- [ ] **FAC03.03** — Implement the factor and exposure in the notebook using a synthetic fixture, then verify calculations and outputs by hand.
- [ ] **FAC03.04** — Create the specific test: split does not change economic market cap. Document expected result and tolerance.
- [ ] **FAC03.05** — Test missing data, zero denominator/incompatible input and explicit failure without misleading results.
- [ ] **FAC03.06** — Compare with a simple reference using identical dates, universe, constraints and costs; chronological out-of-sample protocol.
- [ ] **FAC03.07** — Measure sensitivity to assumptions/parameters and uncertainty; record experiments and limitations.
- [ ] **FAC03.08** — Extract a typed function into the shared engine; add unit and regression tests, version/config/diagnostics.
- [ ] **FAC03.09** — Expose results and assumptions through API/UI, check mandate rules and publish a reproducible report.
- [ ] **FAC03.10** — Attach results and tests to a PR; obtain independent review and check off only after acceptance.

### FAC04 — Momentum

- [x] **FAC04.01** — Write the mathematical specification: cumulative return over 12–1 months. Specify units, convention, horizon and assumptions.
- [ ] **FAC04.02** — Prepare dated inputs: lagged total returns. Define schema, provenance, coverage and availability checks.
- [ ] **FAC04.03** — Implement the factor and exposure in the notebook using a synthetic fixture, then verify calculations and outputs by hand.
- [ ] **FAC04.04** — Create the specific test: exclude current month. Document expected result and tolerance.
- [ ] **FAC04.05** — Test missing data, zero denominator/incompatible input and explicit failure without misleading results.
- [ ] **FAC04.06** — Compare with a simple reference using identical dates, universe, constraints and costs; chronological out-of-sample protocol.
- [ ] **FAC04.07** — Measure sensitivity to assumptions/parameters and uncertainty; record experiments and limitations.
- [ ] **FAC04.08** — Extract a typed function into the shared engine; add unit and regression tests, version/config/diagnostics.
- [ ] **FAC04.09** — Expose results and assumptions through API/UI, check mandate rules and publish a reproducible report.
- [ ] **FAC04.10** — Attach results and tests to a PR; obtain independent review and check off only after acceptance.

### FAC05 — Quality

- [x] **FAC05.01** — Write the mathematical specification: composite score with declared signs and weights. Specify units, convention, horizon and assumptions.
- [ ] **FAC05.02** — Prepare dated inputs: profitability, leverage, stability. Define schema, provenance, coverage and availability checks.
- [ ] **FAC05.03** — Implement the factor and exposure in the notebook using a synthetic fixture, then verify calculations and outputs by hand.
- [ ] **FAC05.04** — Create the specific test: missing components and collinearity. Document expected result and tolerance.
- [ ] **FAC05.05** — Test missing data, zero denominator/incompatible input and explicit failure without misleading results.
- [ ] **FAC05.06** — Compare with a simple reference using identical dates, universe, constraints and costs; chronological out-of-sample protocol.
- [ ] **FAC05.07** — Measure sensitivity to assumptions/parameters and uncertainty; record experiments and limitations.
- [ ] **FAC05.08** — Extract a typed function into the shared engine; add unit and regression tests, version/config/diagnostics.
- [ ] **FAC05.09** — Expose results and assumptions through API/UI, check mandate rules and publish a reproducible report.
- [ ] **FAC05.10** — Attach results and tests to a PR; obtain independent review and check off only after acceptance.

### FAC06 — Low Volatility

- [x] **FAC06.01** — Write the mathematical specification: low volatility or beta, inverse score. Specify units, convention, horizon and assumptions.
- [ ] **FAC06.02** — Prepare dated inputs: trailing series. Define schema, provenance, coverage and availability checks.
- [ ] **FAC06.03** — Implement the factor and exposure in the notebook using a synthetic fixture, then verify calculations and outputs by hand.
- [ ] **FAC06.04** — Create the specific test: zero variance and incomplete windows. Document expected result and tolerance.
- [ ] **FAC06.05** — Test missing data, zero denominator/incompatible input and explicit failure without misleading results.
- [ ] **FAC06.06** — Compare with a simple reference using identical dates, universe, constraints and costs; chronological out-of-sample protocol.
- [ ] **FAC06.07** — Measure sensitivity to assumptions/parameters and uncertainty; record experiments and limitations.
- [ ] **FAC06.08** — Extract a typed function into the shared engine; add unit and regression tests, version/config/diagnostics.
- [ ] **FAC06.09** — Expose results and assumptions through API/UI, check mandate rules and publish a reproducible report.
- [ ] **FAC06.10** — Attach results and tests to a PR; obtain independent review and check off only after acceptance.

### FAC07 — Profitability

- [x] **FAC07.01** — Write the mathematical specification: operating profitability / book equity; RMW. Specify units, convention, horizon and assumptions.
- [ ] **FAC07.02** — Prepare dated inputs: operating profit, book equity. Define schema, provenance, coverage and availability checks.
- [ ] **FAC07.03** — Implement the factor and exposure in the notebook using a synthetic fixture, then verify calculations and outputs by hand.
- [ ] **FAC07.04** — Create the specific test: zero/negative book equity. Document expected result and tolerance.
- [ ] **FAC07.05** — Test missing data, zero denominator/incompatible input and explicit failure without misleading results.
- [ ] **FAC07.06** — Compare with a simple reference using identical dates, universe, constraints and costs; chronological out-of-sample protocol.
- [ ] **FAC07.07** — Measure sensitivity to assumptions/parameters and uncertainty; record experiments and limitations.
- [ ] **FAC07.08** — Extract a typed function into the shared engine; add unit and regression tests, version/config/diagnostics.
- [ ] **FAC07.09** — Expose results and assumptions through API/UI, check mandate rules and publish a reproducible report.
- [ ] **FAC07.10** — Attach results and tests to a PR; obtain independent review and check off only after acceptance.

### FAC08 — Investment

- [x] **FAC08.01** — Write the mathematical specification: asset growth; CMA. Specify units, convention, horizon and assumptions.
- [ ] **FAC08.02** — Prepare dated inputs: dated total assets. Define schema, provenance, coverage and availability checks.
- [ ] **FAC08.03** — Implement the factor and exposure in the notebook using a synthetic fixture, then verify calculations and outputs by hand.
- [ ] **FAC08.04** — Create the specific test: change in consolidation scope. Document expected result and tolerance.
- [ ] **FAC08.05** — Test missing data, zero denominator/incompatible input and explicit failure without misleading results.
- [ ] **FAC08.06** — Compare with a simple reference using identical dates, universe, constraints and costs; chronological out-of-sample protocol.
- [ ] **FAC08.07** — Measure sensitivity to assumptions/parameters and uncertainty; record experiments and limitations.
- [ ] **FAC08.08** — Extract a typed function into the shared engine; add unit and regression tests, version/config/diagnostics.
- [ ] **FAC08.09** — Expose results and assumptions through API/UI, check mandate rules and publish a reproducible report.
- [ ] **FAC08.10** — Attach results and tests to a PR; obtain independent review and check off only after acceptance.

### FAC09 — Carry

- [x] **FAC09.01** — Write the mathematical specification: annualized net carry by instrument. Specify units, convention, horizon and assumptions.
- [ ] **FAC09.02** — Prepare dated inputs: curves, spread, roll, funding. Define schema, provenance, coverage and availability checks.
- [ ] **FAC09.03** — Implement the factor and exposure in the notebook using a synthetic fixture, then verify calculations and outputs by hand.
- [ ] **FAC09.04** — Create the specific test: high funding cost and inversion. Document expected result and tolerance.
- [ ] **FAC09.05** — Test missing data, zero denominator/incompatible input and explicit failure without misleading results.
- [ ] **FAC09.06** — Compare with a simple reference using identical dates, universe, constraints and costs; chronological out-of-sample protocol.
- [ ] **FAC09.07** — Measure sensitivity to assumptions/parameters and uncertainty; record experiments and limitations.
- [ ] **FAC09.08** — Extract a typed function into the shared engine; add unit and regression tests, version/config/diagnostics.
- [ ] **FAC09.09** — Expose results and assumptions through API/UI, check mandate rules and publish a reproducible report.
- [ ] **FAC09.10** — Attach results and tests to a PR; obtain independent review and check off only after acceptance.

### FAC10 — Term

- [x] **FAC10.01** — Write the mathematical specification: duration/term-premium and level exposure. Specify units, convention, horizon and assumptions.
- [ ] **FAC10.02** — Prepare dated inputs: government curves, duration. Define schema, provenance, coverage and availability checks.
- [ ] **FAC10.03** — Implement the factor and exposure in the notebook using a synthetic fixture, then verify calculations and outputs by hand.
- [ ] **FAC10.04** — Create the specific test: parallel curve shock. Document expected result and tolerance.
- [ ] **FAC10.05** — Test missing data, zero denominator/incompatible input and explicit failure without misleading results.
- [ ] **FAC10.06** — Compare with a simple reference using identical dates, universe, constraints and costs; chronological out-of-sample protocol.
- [ ] **FAC10.07** — Measure sensitivity to assumptions/parameters and uncertainty; record experiments and limitations.
- [ ] **FAC10.08** — Extract a typed function into the shared engine; add unit and regression tests, version/config/diagnostics.
- [ ] **FAC10.09** — Expose results and assumptions through API/UI, check mandate rules and publish a reproducible report.
- [ ] **FAC10.10** — Attach results and tests to a PR; obtain independent review and check off only after acceptance.

### FAC11 — Treasury Curve

- [x] **FAC11.01** — Write the mathematical specification: slope y10−y2 and curvature 2y5−y2−y10; isolate sensitivities from Term level. Specify units, convention, horizon and assumptions.
- [ ] **FAC11.02** — Prepare dated inputs: dated Treasury 2Y/5Y/10Y curves with consistent convention and timestamp. Define schema, provenance, coverage and availability checks.
- [ ] **FAC11.03** — Implement the factor and exposure in the notebook using a synthetic fixture, then verify calculations and outputs by hand.
- [ ] **FAC11.04** — Create the specific test: parallel shock leaves slope/curvature unchanged, then nonparallel steepening. Document expected result and tolerance.
- [ ] **FAC11.05** — Test missing data, zero denominator/incompatible input and explicit failure without misleading results.
- [ ] **FAC11.06** — Compare with a simple reference using identical dates, universe, constraints and costs; chronological out-of-sample protocol.
- [ ] **FAC11.07** — Measure sensitivity to assumptions/parameters and uncertainty; record experiments and limitations.
- [ ] **FAC11.08** — Extract a typed function into the shared engine; add unit and regression tests, version/config/diagnostics.
- [ ] **FAC11.09** — Expose results and assumptions through API/UI, check mandate rules and publish a reproducible report.
- [ ] **FAC11.10** — Attach results and tests to a PR; obtain independent review and check off only after acceptance.

### FAC12 — Liquidity

- [x] **FAC12.01** — Write the mathematical specification: Amihud |r|/volume $ and spread. Specify units, convention, horizon and assumptions.
- [ ] **FAC12.02** — Prepare dated inputs: volume, prices, bid-ask. Define schema, provenance, coverage and availability checks.
- [ ] **FAC12.03** — Implement the factor and exposure in the notebook using a synthetic fixture, then verify calculations and outputs by hand.
- [ ] **FAC12.04** — Create the specific test: zero ADV and missing quote. Document expected result and tolerance.
- [ ] **FAC12.05** — Test missing data, zero denominator/incompatible input and explicit failure without misleading results.
- [ ] **FAC12.06** — Compare with a simple reference using identical dates, universe, constraints and costs; chronological out-of-sample protocol.
- [ ] **FAC12.07** — Measure sensitivity to assumptions/parameters and uncertainty; record experiments and limitations.
- [ ] **FAC12.08** — Extract a typed function into the shared engine; add unit and regression tests, version/config/diagnostics.
- [ ] **FAC12.09** — Expose results and assumptions through API/UI, check mandate rules and publish a reproducible report.
- [ ] **FAC12.10** — Attach results and tests to a PR; obtain independent review and check off only after acceptance.

### FAC13 — Inflation

- [x] **FAC13.01** — Write the mathematical specification: beta to CPI surprises. Specify units, convention, horizon and assumptions.
- [ ] **FAC13.02** — Prepare dated inputs: CPI vintage, dated forecasts. Define schema, provenance, coverage and availability checks.
- [ ] **FAC13.03** — Implement the factor and exposure in the notebook using a synthetic fixture, then verify calculations and outputs by hand.
- [ ] **FAC13.04** — Create the specific test: exclude future revision. Document expected result and tolerance.
- [ ] **FAC13.05** — Test missing data, zero denominator/incompatible input and explicit failure without misleading results.
- [ ] **FAC13.06** — Compare with a simple reference using identical dates, universe, constraints and costs; chronological out-of-sample protocol.
- [ ] **FAC13.07** — Measure sensitivity to assumptions/parameters and uncertainty; record experiments and limitations.
- [ ] **FAC13.08** — Extract a typed function into the shared engine; add unit and regression tests, version/config/diagnostics.
- [ ] **FAC13.09** — Expose results and assumptions through API/UI, check mandate rules and publish a reproducible report.
- [ ] **FAC13.10** — Attach results and tests to a PR; obtain independent review and check off only after acceptance.

## Catalog — 10 Dynamic Models

Single notebook: chapter(s) 26. Each item is an independent deliverable.

### DYN01 — Hidden Markov Model

- [x] **DYN01.01** — Write the mathematical specification: filtered probability P(S_t|information_t). Specify units, convention, horizon and assumptions.
- [ ] **DYN01.02** — Prepare dated inputs: feature series, states, transition matrix. Define schema, provenance, coverage and availability checks.
- [ ] **DYN01.03** — Implement the dynamic policy in the notebook using a synthetic fixture, then verify calculations and outputs by hand.
- [ ] **DYN01.04** — Create the specific test: future data do not change past state. Document expected result and tolerance.
- [ ] **DYN01.05** — Test missing data, zero denominator/incompatible input and explicit failure without misleading results.
- [ ] **DYN01.06** — Compare with a simple reference using identical dates, universe, constraints and costs; chronological out-of-sample protocol.
- [ ] **DYN01.07** — Measure sensitivity to assumptions/parameters and uncertainty; record experiments and limitations.
- [ ] **DYN01.08** — Extract a typed function into the shared engine; add unit and regression tests, version/config/diagnostics.
- [ ] **DYN01.09** — Expose results and assumptions through API/UI, check mandate rules and publish a reproducible report.
- [ ] **DYN01.10** — Attach results and tests to a PR; obtain independent review and check off only after acceptance.

### DYN02 — Bayesian Updating

- [x] **DYN02.01** — Write the mathematical specification: posterior proportional to likelihood*prior. Specify units, convention, horizon and assumptions.
- [ ] **DYN02.02** — Prepare dated inputs: prior, likelihood, dated observations. Define schema, provenance, coverage and availability checks.
- [ ] **DYN02.03** — Implement the dynamic policy in the notebook using a synthetic fixture, then verify calculations and outputs by hand.
- [ ] **DYN02.04** — Create the specific test: noninformative observation. Document expected result and tolerance.
- [ ] **DYN02.05** — Test missing data, zero denominator/incompatible input and explicit failure without misleading results.
- [ ] **DYN02.06** — Compare with a simple reference using identical dates, universe, constraints and costs; chronological out-of-sample protocol.
- [ ] **DYN02.07** — Measure sensitivity to assumptions/parameters and uncertainty; record experiments and limitations.
- [ ] **DYN02.08** — Extract a typed function into the shared engine; add unit and regression tests, version/config/diagnostics.
- [ ] **DYN02.09** — Expose results and assumptions through API/UI, check mandate rules and publish a reproducible report.
- [ ] **DYN02.10** — Attach results and tests to a PR; obtain independent review and check off only after acceptance.

### DYN03 — Dynamic Risk Budgeting

- [x] **DYN03.01** — Write the mathematical specification: recompute RC and conditional target budget. Specify units, convention, horizon and assumptions.
- [ ] **DYN03.02** — Prepare dated inputs: Σ_t, budgets, current positions. Define schema, provenance, coverage and availability checks.
- [ ] **DYN03.03** — Implement the dynamic policy in the notebook using a synthetic fixture, then verify calculations and outputs by hand.
- [ ] **DYN03.04** — Create the specific test: tight budget and high costs. Document expected result and tolerance.
- [ ] **DYN03.05** — Test missing data, zero denominator/incompatible input and explicit failure without misleading results.
- [ ] **DYN03.06** — Compare with a simple reference using identical dates, universe, constraints and costs; chronological out-of-sample protocol.
- [ ] **DYN03.07** — Measure sensitivity to assumptions/parameters and uncertainty; record experiments and limitations.
- [ ] **DYN03.08** — Extract a typed function into the shared engine; add unit and regression tests, version/config/diagnostics.
- [ ] **DYN03.09** — Expose results and assumptions through API/UI, check mandate rules and publish a reproducible report.
- [ ] **DYN03.10** — Attach results and tests to a PR; obtain independent review and check off only after acceptance.

### DYN04 — Stochastic Optimization

- [x] **DYN04.01** — Write the mathematical specification: max E[U(W_T)] with nonanticipativity. Specify units, convention, horizon and assumptions.
- [ ] **DYN04.02** — Prepare dated inputs: scenario tree, probabilities, flows. Define schema, provenance, coverage and availability checks.
- [ ] **DYN04.03** — Implement the dynamic policy in the notebook using a synthetic fixture, then verify calculations and outputs by hand.
- [ ] **DYN04.04** — Create the specific test: two scenarios share identical states before branching. Document expected result and tolerance.
- [ ] **DYN04.05** — Test missing data, zero denominator/incompatible input and explicit failure without misleading results.
- [ ] **DYN04.06** — Compare with a simple reference using identical dates, universe, constraints and costs; chronological out-of-sample protocol.
- [ ] **DYN04.07** — Measure sensitivity to assumptions/parameters and uncertainty; record experiments and limitations.
- [ ] **DYN04.08** — Extract a typed function into the shared engine; add unit and regression tests, version/config/diagnostics.
- [ ] **DYN04.09** — Expose results and assumptions through API/UI, check mandate rules and publish a reproducible report.
- [ ] **DYN04.10** — Attach results and tests to a PR; obtain independent review and check off only after acceptance.

### DYN05 — Multi-Period Optimization

- [x] **DYN05.01** — Write the mathematical specification: successive w_t with intertemporal constraints. Specify units, convention, horizon and assumptions.
- [ ] **DYN05.02** — Prepare dated inputs: horizon forecasts, costs, flows. Define schema, provenance, coverage and availability checks.
- [ ] **DYN05.03** — Implement the dynamic policy in the notebook using a synthetic fixture, then verify calculations and outputs by hand.
- [ ] **DYN05.04** — Create the specific test: horizon 1 recovers static solution. Document expected result and tolerance.
- [ ] **DYN05.05** — Test missing data, zero denominator/incompatible input and explicit failure without misleading results.
- [ ] **DYN05.06** — Compare with a simple reference using identical dates, universe, constraints and costs; chronological out-of-sample protocol.
- [ ] **DYN05.07** — Measure sensitivity to assumptions/parameters and uncertainty; record experiments and limitations.
- [ ] **DYN05.08** — Extract a typed function into the shared engine; add unit and regression tests, version/config/diagnostics.
- [ ] **DYN05.09** — Expose results and assumptions through API/UI, check mandate rules and publish a reproducible report.
- [ ] **DYN05.10** — Attach results and tests to a PR; obtain independent review and check off only after acceptance.

### DYN06 — Dynamic Programming

- [x] **DYN06.01** — Write the mathematical specification: Bellman V_t=max_a E[reward+V_(t+1)]. Specify units, convention, horizon and assumptions.
- [ ] **DYN06.02** — Prepare dated inputs: wealth/time/regime state. Define schema, provenance, coverage and availability checks.
- [ ] **DYN06.03** — Implement the dynamic policy in the notebook using a synthetic fixture, then verify calculations and outputs by hand.
- [ ] **DYN06.04** — Create the specific test: small analytical grid. Document expected result and tolerance.
- [ ] **DYN06.05** — Test missing data, zero denominator/incompatible input and explicit failure without misleading results.
- [ ] **DYN06.06** — Compare with a simple reference using identical dates, universe, constraints and costs; chronological out-of-sample protocol.
- [ ] **DYN06.07** — Measure sensitivity to assumptions/parameters and uncertainty; record experiments and limitations.
- [ ] **DYN06.08** — Extract a typed function into the shared engine; add unit and regression tests, version/config/diagnostics.
- [ ] **DYN06.09** — Expose results and assumptions through API/UI, check mandate rules and publish a reproducible report.
- [ ] **DYN06.10** — Attach results and tests to a PR; obtain independent review and check off only after acceptance.

### DYN07 — Model Predictive Control

- [x] **DYN07.01** — Write the mathematical specification: optimize over H, apply first decision. Specify units, convention, horizon and assumptions.
- [ ] **DYN07.02** — Prepare dated inputs: current state, horizon H. Define schema, provenance, coverage and availability checks.
- [ ] **DYN07.03** — Implement the dynamic policy in the notebook using a synthetic fixture, then verify calculations and outputs by hand.
- [ ] **DYN07.04** — Create the specific test: horizon 1 and forecast update. Document expected result and tolerance.
- [ ] **DYN07.05** — Test missing data, zero denominator/incompatible input and explicit failure without misleading results.
- [ ] **DYN07.06** — Compare with a simple reference using identical dates, universe, constraints and costs; chronological out-of-sample protocol.
- [ ] **DYN07.07** — Measure sensitivity to assumptions/parameters and uncertainty; record experiments and limitations.
- [ ] **DYN07.08** — Extract a typed function into the shared engine; add unit and regression tests, version/config/diagnostics.
- [ ] **DYN07.09** — Expose results and assumptions through API/UI, check mandate rules and publish a reproducible report.
- [ ] **DYN07.10** — Attach results and tests to a PR; obtain independent review and check off only after acceptance.

### DYN08 — Reinforcement Learning

- [x] **DYN08.01** — Write the mathematical specification: net reward penalized by risk; guardrails. Specify units, convention, horizon and assumptions.
- [ ] **DYN08.02** — Prepare dated inputs: simulator, state/action/reward. Define schema, provenance, coverage and availability checks.
- [ ] **DYN08.03** — Implement the dynamic policy in the notebook using a synthetic fixture, then verify calculations and outputs by hand.
- [ ] **DYN08.04** — Create the specific test: out-of-distribution case, fixed policy comparison, no real orders. Document expected result and tolerance.
- [ ] **DYN08.05** — Test missing data, zero denominator/incompatible input and explicit failure without misleading results.
- [ ] **DYN08.06** — Compare with a simple reference using identical dates, universe, constraints and costs; chronological out-of-sample protocol.
- [ ] **DYN08.07** — Measure sensitivity to assumptions/parameters and uncertainty; record experiments and limitations.
- [ ] **DYN08.08** — Extract a typed function into the shared engine; add unit and regression tests, version/config/diagnostics.
- [ ] **DYN08.09** — Expose results and assumptions through API/UI, check mandate rules and publish a reproducible report.
- [ ] **DYN08.10** — Attach results and tests to a PR; obtain independent review and check off only after acceptance.

### DYN09 — Ensemble Models

- [x] **DYN09.01** — Write the mathematical specification: aggregate using OOS validation. Specify units, convention, horizon and assumptions.
- [ ] **DYN09.02** — Prepare dated inputs: forecasts/weights from multiple models. Define schema, provenance, coverage and availability checks.
- [ ] **DYN09.03** — Implement the dynamic policy in the notebook using a synthetic fixture, then verify calculations and outputs by hand.
- [ ] **DYN09.04** — Create the specific test: missing model and normalized weights. Document expected result and tolerance.
- [ ] **DYN09.05** — Test missing data, zero denominator/incompatible input and explicit failure without misleading results.
- [ ] **DYN09.06** — Compare with a simple reference using identical dates, universe, constraints and costs; chronological out-of-sample protocol.
- [ ] **DYN09.07** — Measure sensitivity to assumptions/parameters and uncertainty; record experiments and limitations.
- [ ] **DYN09.08** — Extract a typed function into the shared engine; add unit and regression tests, version/config/diagnostics.
- [ ] **DYN09.09** — Expose results and assumptions through API/UI, check mandate rules and publish a reproducible report.
- [ ] **DYN09.10** — Attach results and tests to a PR; obtain independent review and check off only after acceptance.

### DYN10 — Robust Control

- [x] **DYN10.01** — Write the mathematical specification: max-min policy under uncertainty. Specify units, convention, horizon and assumptions.
- [ ] **DYN10.02** — Prepare dated inputs: bounded perturbations and current state. Define schema, provenance, coverage and availability checks.
- [ ] **DYN10.03** — Implement the dynamic policy in the notebook using a synthetic fixture, then verify calculations and outputs by hand.
- [ ] **DYN10.04** — Create the specific test: zero perturbation recovers nominal solution. Document expected result and tolerance.
- [ ] **DYN10.05** — Test missing data, zero denominator/incompatible input and explicit failure without misleading results.
- [ ] **DYN10.06** — Compare with a simple reference using identical dates, universe, constraints and costs; chronological out-of-sample protocol.
- [ ] **DYN10.07** — Measure sensitivity to assumptions/parameters and uncertainty; record experiments and limitations.
- [ ] **DYN10.08** — Extract a typed function into the shared engine; add unit and regression tests, version/config/diagnostics.
- [ ] **DYN10.09** — Expose results and assumptions through API/UI, check mandate rules and publish a reproducible report.
- [ ] **DYN10.10** — Attach results and tests to a PR; obtain independent review and check off only after acceptance.

## Cross-Cutting Catalog — Portfolio Metrics


### MET01 — Cumulative Return


- [x] **MET01.01** — Define: prod(1+r)-1; unit, frequency and sign convention.
- [ ] **MET01.02** — Implement using reconciled NAV/returns/positions/benchmark series; distinguish gross/net and nominal/real.
- [ ] **MET01.03** — Test: sequence +10% then -10% = -1%; avoid misleading numbers with insufficient data.
- [ ] **MET01.04** — Compare with an independent reference on the same sample; document windows, tolerance and version.
- [ ] **MET01.05** — Add metric to export and UI with period, benchmark, limitations and provenance.



### MET02 — CAGR


- [x] **MET02.01** — Define: (NAV_T/NAV_0)^(1/years)-1; unit, frequency and sign convention.
- [ ] **MET02.02** — Implement using reconciled NAV/returns/positions/benchmark series; distinguish gross/net and nominal/real.
- [ ] **MET02.03** — Test: two-year horizon with doubled NAV; avoid misleading numbers with insufficient data.
- [ ] **MET02.04** — Compare with an independent reference on the same sample; document windows, tolerance and version.
- [ ] **MET02.05** — Add metric to export and UI with period, benchmark, limitations and provenance.



### MET03 — TWR


- [x] **MET03.01** — Define: product of subperiod returns separating cash flows; unit, frequency and sign convention.
- [ ] **MET03.02** — Implement using reconciled NAV/returns/positions/benchmark series; distinguish gross/net and nominal/real.
- [ ] **MET03.03** — Test: external contribution does not create a return; avoid misleading numbers with insufficient data.
- [ ] **MET03.04** — Compare with an independent reference on the same sample; document windows, tolerance and version.
- [ ] **MET03.05** — Add metric to export and UI with period, benchmark, limitations and provenance.



### MET04 — MWR/IRR


- [x] **MET04.01** — Define: root NPV(dated flows)=0; unit, frequency and sign convention.
- [ ] **MET04.02** — Implement using reconciled NAV/returns/positions/benchmark series; distinguish gross/net and nominal/real.
- [ ] **MET04.03** — Test: flows with no root or multiple roots; avoid misleading numbers with insufficient data.
- [ ] **MET04.04** — Compare with an independent reference on the same sample; document windows, tolerance and version.
- [ ] **MET04.05** — Add metric to export and UI with period, benchmark, limitations and provenance.



### MET05 — Volatility


- [x] **MET05.01** — Define: sd(r)√K; unit, frequency and sign convention.
- [ ] **MET05.02** — Implement using reconciled NAV/returns/positions/benchmark series; distinguish gross/net and nominal/real.
- [ ] **MET05.03** — Test: constant series and explicit K; avoid misleading numbers with insufficient data.
- [ ] **MET05.04** — Compare with an independent reference on the same sample; document windows, tolerance and version.
- [ ] **MET05.05** — Add metric to export and UI with period, benchmark, limitations and provenance.



### MET06 — Sharpe


- [x] **MET06.01** — Define: mean(r-rf)/sd(r-rf)√K; unit, frequency and sign convention.
- [ ] **MET06.02** — Implement using reconciled NAV/returns/positions/benchmark series; distinguish gross/net and nominal/real.
- [ ] **MET06.03** — Test: constant excess return and zero sd; avoid misleading numbers with insufficient data.
- [ ] **MET06.04** — Compare with an independent reference on the same sample; document windows, tolerance and version.
- [ ] **MET06.05** — Add metric to export and UI with period, benchmark, limitations and provenance.



### MET07 — Sortino


- [x] **MET07.01** — Define: excess over MAR / downside deviation; unit, frequency and sign convention.
- [ ] **MET07.02** — Implement using reconciled NAV/returns/positions/benchmark series; distinguish gross/net and nominal/real.
- [ ] **MET07.03** — Test: no losses below MAR; avoid misleading numbers with insufficient data.
- [ ] **MET07.04** — Compare with an independent reference on the same sample; document windows, tolerance and version.
- [ ] **MET07.05** — Add metric to export and UI with period, benchmark, limitations and provenance.



### MET08 — Calmar


- [x] **MET08.01** — Define: CAGR/abs(MDD); unit, frequency and sign convention.
- [ ] **MET08.02** — Implement using reconciled NAV/returns/positions/benchmark series; distinguish gross/net and nominal/real.
- [ ] **MET08.03** — Test: zero MDD; avoid misleading numbers with insufficient data.
- [ ] **MET08.04** — Compare with an independent reference on the same sample; document windows, tolerance and version.
- [ ] **MET08.05** — Add metric to export and UI with period, benchmark, limitations and provenance.



### MET09 — Omega


- [x] **MET09.01** — Define: E[(r-T)+]/E[(T-r)+]; unit, frequency and sign convention.
- [ ] **MET09.02** — Implement using reconciled NAV/returns/positions/benchmark series; distinguish gross/net and nominal/real.
- [ ] **MET09.03** — Test: threshold and zero denominator; avoid misleading numbers with insufficient data.
- [ ] **MET09.04** — Compare with an independent reference on the same sample; document windows, tolerance and version.
- [ ] **MET09.05** — Add metric to export and UI with period, benchmark, limitations and provenance.



### MET10 — Drawdown


- [x] **MET10.01** — Define: NAV/peak-1; minimum, duration, recovery; unit, frequency and sign convention.
- [ ] **MET10.02** — Implement using reconciled NAV/returns/positions/benchmark series; distinguish gross/net and nominal/real.
- [ ] **MET10.03** — Test: new peak and continuous loss; avoid misleading numbers with insufficient data.
- [ ] **MET10.04** — Compare with an independent reference on the same sample; document windows, tolerance and version.
- [ ] **MET10.05** — Add metric to export and UI with period, benchmark, limitations and provenance.



### MET11 — VaR 95/99


- [x] **MET11.01** — Define: loss quantile at level α; unit, frequency and sign convention.
- [ ] **MET11.02** — Implement using reconciled NAV/returns/positions/benchmark series; distinguish gross/net and nominal/real.
- [ ] **MET11.03** — Test: quantile ordering; avoid misleading numbers with insufficient data.
- [ ] **MET11.04** — Compare with an independent reference on the same sample; document windows, tolerance and version.
- [ ] **MET11.05** — Add metric to export and UI with period, benchmark, limitations and provenance.



### MET12 — ES 95/99


- [x] **MET12.01** — Define: upper-tail mean with weighted ties; unit, frequency and sign convention.
- [ ] **MET12.02** — Implement using reconciled NAV/returns/positions/benchmark series; distinguish gross/net and nominal/real.
- [ ] **MET12.03** — Test: discrete tail and small sample; avoid misleading numbers with insufficient data.
- [ ] **MET12.04** — Compare with an independent reference on the same sample; document windows, tolerance and version.
- [ ] **MET12.05** — Add metric to export and UI with period, benchmark, limitations and provenance.



### MET13 — Beta and Alpha


- [x] **MET13.01** — Define: OLS excess returns against benchmark; annualization convention; unit, frequency and sign convention.
- [ ] **MET13.02** — Implement using reconciled NAV/returns/positions/benchmark series; distinguish gross/net and nominal/real.
- [ ] **MET13.03** — Test: identical benchmark series; avoid misleading numbers with insufficient data.
- [ ] **MET13.04** — Compare with an independent reference on the same sample; document windows, tolerance and version.
- [ ] **MET13.05** — Add metric to export and UI with period, benchmark, limitations and provenance.



### MET14 — Tracking Error


- [x] **MET14.01** — Define: sd(rp-rb)√K; unit, frequency and sign convention.
- [ ] **MET14.02** — Implement using reconciled NAV/returns/positions/benchmark series; distinguish gross/net and nominal/real.
- [ ] **MET14.03** — Test: identical benchmark; avoid misleading numbers with insufficient data.
- [ ] **MET14.04** — Compare with an independent reference on the same sample; document windows, tolerance and version.
- [ ] **MET14.05** — Add metric to export and UI with period, benchmark, limitations and provenance.



### MET15 — Information Ratio


- [x] **MET15.01** — Define: mean(rp-rb)√K/sd(rp-rb); unit, frequency and sign convention.
- [ ] **MET15.02** — Implement using reconciled NAV/returns/positions/benchmark series; distinguish gross/net and nominal/real.
- [ ] **MET15.03** — Test: zero TE; avoid misleading numbers with insufficient data.
- [ ] **MET15.04** — Compare with an independent reference on the same sample; document windows, tolerance and version.
- [ ] **MET15.05** — Add metric to export and UI with period, benchmark, limitations and provenance.



### MET16 — HHI and Effective N


- [x] **MET16.01** — Define: sum(w²), 1/HHI long-only; unit, frequency and sign convention.
- [ ] **MET16.02** — Implement using reconciled NAV/returns/positions/benchmark series; distinguish gross/net and nominal/real.
- [ ] **MET16.03** — Test: 1/N and single-asset portfolio; avoid misleading numbers with insufficient data.
- [ ] **MET16.04** — Compare with an independent reference on the same sample; document windows, tolerance and version.
- [ ] **MET16.05** — Add metric to export and UI with period, benchmark, limitations and provenance.



### MET17 — Risk contribution


- [x] **MET17.01** — Define: w_i(Σw)_i/σp; unit, frequency and sign convention.
- [ ] **MET17.02** — Implement using reconciled NAV/returns/positions/benchmark series; distinguish gross/net and nominal/real.
- [ ] **MET17.03** — Test: sum = σp; avoid misleading numbers with insufficient data.
- [ ] **MET17.04** — Compare with an independent reference on the same sample; document windows, tolerance and version.
- [ ] **MET17.05** — Add metric to export and UI with period, benchmark, limitations and provenance.



### MET18 — Exposures


- [x] **MET18.01** — Define: gross/net, FX, sector, factor, DV01/key-rate DV01, notional and margin; unit, frequency and sign convention.
- [ ] **MET18.02** — Implement using reconciled NAV/returns/positions/benchmark series; distinguish gross/net and nominal/real.
- [ ] **MET18.03** — Test: derivative not double counted; avoid misleading numbers with insufficient data.
- [ ] **MET18.04** — Compare with an independent reference on the same sample; document windows, tolerance and version.
- [ ] **MET18.05** — Add metric to export and UI with period, benchmark, limitations and provenance.



### MET19 — Turnover and Costs


- [x] **MET19.01** — Define: sum|Δw|/2 per convention; actual ledger costs; unit, frequency and sign convention.
- [ ] **MET19.02** — Implement using reconciled NAV/returns/positions/benchmark series; distinguish gross/net and nominal/real.
- [ ] **MET19.03** — Test: no trade = no transaction cost; avoid misleading numbers with insufficient data.
- [ ] **MET19.04** — Compare with an independent reference on the same sample; document windows, tolerance and version.
- [ ] **MET19.05** — Add metric to export and UI with period, benchmark, limitations and provenance.



### MET20 — Liquidity


- [x] **MET20.01** — Define: position/(ADV*participation); unit, frequency and sign convention.
- [ ] **MET20.02** — Implement using reconciled NAV/returns/positions/benchmark series; distinguish gross/net and nominal/real.
- [ ] **MET20.03** — Test: zero ADV or stressed ADV; avoid misleading numbers with insufficient data.
- [ ] **MET20.04** — Compare with an independent reference on the same sample; document windows, tolerance and version.
- [ ] **MET20.05** — Add metric to export and UI with period, benchmark, limitations and provenance.



### MET21 — Robustness


- [x] **MET21.01** — Define: weight dispersion, sensitivity and OOS IC; unit, frequency and sign convention.
- [ ] **MET21.02** — Implement using reconciled NAV/returns/positions/benchmark series; distinguish gross/net and nominal/real.
- [ ] **MET21.03** — Test: window and cost variation; avoid misleading numbers with insufficient data.
- [ ] **MET21.04** — Compare with an independent reference on the same sample; document windows, tolerance and version.
- [ ] **MET21.05** — Add metric to export and UI with period, benchmark, limitations and provenance.



### MET22 — Attribution


- [x] **MET22.01** — Define: allocation/selection/factor/carry/roll/FX/costs; unit, frequency and sign convention.
- [ ] **MET22.02** — Implement using reconciled NAV/returns/positions/benchmark series; distinguish gross/net and nominal/real.
- [ ] **MET22.03** — Test: components reconcile to P&L; avoid misleading numbers with insufficient data.
- [ ] **MET22.04** — Compare with an independent reference on the same sample; document windows, tolerance and version.
- [ ] **MET22.05** — Add metric to export and UI with period, benchmark, limitations and provenance.



### MET23 — Goals


- [x] **MET23.01** — Define: P(W_T≥G), expected funding shortfall and coverage; unit, frequency and sign convention.
- [ ] **MET23.02** — Implement using reconciled NAV/returns/positions/benchmark series; distinguish gross/net and nominal/real.
- [ ] **MET23.03** — Test: horizon with known cash flow; avoid misleading numbers with insufficient data.
- [ ] **MET23.04** — Compare with an independent reference on the same sample; document windows, tolerance and version.
- [ ] **MET23.05** — Add metric to export and UI with period, benchmark, limitations and provenance.



## Final Validation

- [ ] No real orders; independent quantitative, behavioral and security review.
- [ ] Verify all 75 catalog entries, fees, FX risk, stress, constraints and audit.
