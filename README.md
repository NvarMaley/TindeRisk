# RiskMatch

This repository mirrors the local RiskMatch workspace, including research data and excluding `Theory/`. Four large inputs are stored as lossless compressed chunks. After cloning, run `python3 research/restore_large_data.py` before running data checks. See [data restoration](data/archive_parts_README.md).

RiskMatch is a planned English-language web app for people investing toward a financial goal. A short factual intake and adaptive swipe interview establish a mandate. The research engine will estimate which combinations of net return and risk are attainable within it. The client will compare feasible options, select an allocation and review it as markets or personal circumstances change.

Read the [detailed project guide](PROJECT_GUIDE.md) for the study setup and eleven subsequent steps, research methods, worked examples and rationale behind each client decision.

For card authors and report writers, the [questionnaire design and research rationale](questions/QUESTIONNAIRE_DESIGN.md) records the core allocation, adaptive branches, scoring assumptions and validation plan. The [card-by-card guide](questions/GUIDE_DES_CARTES.md) lists every English prompt with a French interpretation and its effect on the client profile.

## Run the factual intake and risk interview

With Python 3.12 in a dedicated app environment:

```sh
python -m pip install -r requirements-app.txt
python -m streamlit run app/intake.py
```

The four screens lead to a dated cash ladder, available investment capital, and a comparison of desired and required returns. Select **Open risk interview** from the mandate review. Swipe or press right for yes, left for no, and U for unsure. You can finish early, resume, correct any choice and return to the payment schedule. Answers and corrections are held in the current session. Run the intake checks with `python -m unittest discover -s tests -p 'test_intake*.py'`.

## Where to begin

The workspace now includes local market, macro, WRDS and laboratory inputs and previously prepared tables. See the [data inventory and import checks](data/README_data.md) for coverage, known gaps and the reproducible verification command. The [prepared study panels](data/prepared_v1/) and [cleaning record](research/cleaning/README.md) describe the 3.2 release. The [historical return and risk analysis](research/descriptive/README.md) reports CHF wealth, drawdowns, tail losses and holding-level risk contributions for section 4.1. The [shock and episode analysis](research/shocks/README.md) compares the same market shocks across two allocations in CHF for section 4.2. The [chapter 5 experiment report](research/experiments/README.md) records historical forecast scores, Black–Litterman views, funded trading policies and admission decisions. The [study source catalogue](research/source_catalogue/README.md) maps H01–H07 to raw snapshots and includes the offline fixture. Section 1.1 of the [checklist](CHECKLIST.md) records the course scope and reproducible setup. Run `python -I -S tests/check_course_examples.py` with CPython 3.12.6 for the synthetic checks. Local course materials are in `Theory/`. The checklist indexes the supplied Markdown sources and gives relevant readings by task. Separate imported findings from results independently reproduced here. The local app includes the factual intake and the versioned adaptive interview. When reusing an input, record its provenance, rights and verification in this workspace. The project repository is [TindeRisk](https://github.com/NvarMaley/TindeRisk).

1. Read the [checklist](CHECKLIST.md) in chapter order. Each numbered task specifies a method and evidence required for completion. Dependencies and deferred work are called out at chapter boundaries.
2. Open [RiskMatch.ipynb](RiskMatch.ipynb) with a Python 3.12 Jupyter kernel and run all cells from the project root. The core calculations use the Python standard library and invented inputs. The optional optimization lab uses the dependencies listed below. An optional local cell checks the imported ETF panel when available. The worked calculations are accounting checks. They do not estimate a real client's tolerance or forecast a real asset.
3. For each completed task, tick its box, record the command, sample and outcome under the matching notebook chapter, and add any material decision to the [journal](DECISION_LOG.md). Keep inconclusive and rejected experiments in the record.

### QARM delivery scope

For the course, demonstrate one investment strategy end to end: turn a client's dated withdrawal into a reserve, screen eligible assets, sweep risk limits with constrained mean–variance optimization, compare with a simple allocation and show whether weights change under covariance or cost assumptions. Let the client change an input in Streamlit and inspect the result. Link the working app and GitHub code and rehearse a 15-minute client pitch including live questions. Use the CHF 50,000 / CHF 15,000 withdrawal as one reproducible example. H01–H07, extended forecasting and ongoing monitoring remain on the broader product roadmap. Select extensions for the presentation when their measured effect changes the client decision.

The quantitative extension compares a classical frontier with one that penalizes uncertainty in expected returns. A shadow-price check verifies the local value of the risk constraint, and a reverse stress identifies the withdrawal funding boundary. Install `python -m pip install -r requirements-frontier.txt` for the optional synthetic solver example and figure. The empirical comparison remains open.

## Product decisions carried forward

- Four short factual screens followed by one statement at a time. Right means yes, left means no, and uncertainty is allowed. The bank contains 60 hypothetical scenarios including 15 common cards. The route allows up to 25 answers.
- Report willingness to bear risk separately from the capacity to absorb losses. Protect scheduled withdrawals and household reserves. Record desired return separately from the return required to fund the goal.
- Study assets by research question and client eligibility. There is no fixed ETF count. Test common macro shocks across candidate allocations. Independent evaluation after costs governs which methods enter the catalogue.
- Present a range of opportunities along the estimated feasible frontier in the client's spending currency. Keep historical outcomes, conditional forecasts and stress scenarios identifiable.
- Start monitoring with authorized closing data. Explain hold and rebalance alternatives and obtain confirmation. A stale quote, an infeasible goal or an uncertain profile has an explicit user-facing outcome.
- Deliver a reproducible GitHub project, Streamlit web app and a 15-minute client presentation. Verify the applicable course brief when setting up the new project.

## What the team will validate

The questionnaire uses hypothetical choices and synthetic routes. Each family has a worked question, alternative explanations and a stated consequence for the profile. See the [behavioral rationale](questions/QUESTIONNAIRE_DESIGN.md#how-to-interpret-hypothetical-answers-in-the-report). In the portfolio experiment, freeze a mandate and compare a feasible fixed mix, classical frontier and robust frontier after identical costs. A fictional mandate can support that second experiment today. For a given forecast target, compare a simple reference, standalone models and preregistered combinations at common dates. A forecast improvement reaches the portfolio only after a separate after-cost evaluation. Client reviews distinguish the experimental one-year tolerance band, a short-horizon risk signal and the dated long-term funding scenario. An inconclusive discretionary trade retains the current feasible holding.

## Directory guide

The table describes intended contents. The factual intake, notebook, research scripts and import verifier can be run locally. The adaptive interview uses questions/profile_v1.json and src/riskmatch/interview.py.

| Location | Intended contents |
|---|---|
| `app/` | Streamlit screens and browser swipe interaction |
| `questions/` | Versioned card bank, branch table and separate validation items |
| `src/riskmatch/` | Interview, data, forecasting, optimization, accounting and monitoring code |
| `research/` | Study register, protocols, source references and reproducible experiments |
| `data/raw/`, `data/processed/` | Local authorized inputs and derived tables, excluded from future Git tracking |
| `data/demo/` | Synthetic market bundle and local historical CHF walkthrough (see data inventory) |
| `tests/` | Unit, temporal-integrity, portfolio-accounting and browser checks |

Candidate tools include Python, pandas, NumPy, DuckDB, Parquet, statsmodels, arch, scikit-learn, SciPy, CVXPY, Streamlit, pytest and Jupyter. Pin a dependency when adopting it and record its version with the first reproducible result.
