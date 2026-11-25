# RiskMatch — V3

**Understand risk. Explore strategies. Build a suitable portfolio.**

A collaborative quantitative US multi-asset research and development platform. RiskMatch combines portfolio discovery cards with a reproducible quantitative engine. V3 currently contains a demonstration Web App and shared engine using synthetic data; no financial model or questionnaire has been independently validated.

**Treasury-only fixed-income universe:** T-Bills, Treasury Notes, Treasury Bonds, TIPS and bond ETFs with verified exclusively Treasury exposure. No corporate debt, MBS, agencies, municipal debt or mixed bond ETFs. US equities, REITs, eligible futures and USD cash remain in scope. Treasury Curve (slope/curvature) replaces the original Credit factor, retaining 13 factors.

## User Experience

1. Mandate: goals, investable wealth, horizon, cash flows, constraints, base currency and financial loss capacity.
2. RiskMatch Discovery: balanced 30-card sessions sampled from a 60-card bilingual bank (Yes to accept the proposed switch, No to keep the starting option, plus unsure, skip and undo), with a separately consented local session.
3. Profile: exploratory risk-aversion score 1–30 (30 = strong aversion), uncertainty, consistency and separate preferences. The score is neither a diagnosis nor automatic calibration of λ.
4. Quantitative engine: candidate generation, optimization, simulations and out-of-sample testing.
5. RiskMatch Explore: swipe among mandate-compatible portfolios with comparable risk, costs, losses and goals.
6. Final comparison: likes create a shortlist, not a trade. Explicit informed paper selection only.

The original V2 animated opening and visual/audio identity are retained. The interface offers English and French, with English as the project and API language. After the opening, users must select an existing local simulation save and enter its four-digit PIN, or create a new save with a name and four-digit PIN. The studio navigation is hidden until a save is unlocked. Each save has independent simulation state. No online account or real client data.

## Documentation

- [Detailed A–Z checklist](CHECKLIST_A_Z.md): chapter tickets, 75 catalog entries, metrics, tests and validation gates.
- [Quantitative guide](docs/QUANT_GUIDE_A_Z.md): universe, data, 11 objectives, 22 construction methods, 19 strategies, 13 factors and 10 dynamic models.
- [Behavioral protocol](docs/RISKMATCH_BEHAVIORAL.md): cards, scoring, research and validation.
- [Draft behavioral pilot](docs/BEHAVIORAL_PILOT.md): study design and synthetic analysis readiness; no human validation yet.
- [Portfolio matching](docs/PORTFOLIO_MATCHING.md): UX, filtering, ranking and confirmation.
- [Architecture](docs/ARCHITECTURE.md): components, contracts and flow.
- [Roadmap](docs/ROADMAP.md): execution order, milestones and acceptance criteria.
- [Dependency registry](docs/TASK_DEPENDENCIES.csv): direct prerequisites and topological order; `python scripts/task_dependencies.py --ready` lists available tickets.
- [Data and security](docs/DATA_SECURITY.md): licenses, privacy and controls.
- [Contributing](CONTRIBUTING.md): branches, reviews and conventions.
- [Experiment registry](docs/EXPERIMENT_REGISTRY.md): run IDs, data versions and validation evidence.
- [Client mandate](docs/CLIENT_MANDATE.md): Chapter 01 input schema, deterministic funding calculations and constraints.
- [US universe](docs/US_UNIVERSE.md): issuer-sourced ETF candidate catalog, dated identity, liquidity, coverage, Treasury-only rules and gated extensions.
- [Data acquisition](docs/DATA_ACQUISITION_PLAN.md): verified local coverage, public downloads and precise missing WRDS fields.
- [Data monitoring](docs/DATA_MONITORING_PLAN.md): current Treasury identity/holdings checks, provider comparison and future refresh architecture.

## Start on Mac

1. Install Python 3.12 (the shared development and CI baseline), then double-click `INSTALL.command`. It creates an isolated `.venv` and installs the pinned dependencies from `requirements.lock`. An older environment that inherits system packages must be stopped and renamed to `.venv-legacy` before rerunning the installer.
2. Double-click `START.command`. Web App: http://127.0.0.1:3000 ; JupyterLab: http://127.0.0.1:8888/lab (authenticated link in `.run/jupyter.log`).
3. Open the [checklist](CHECKLIST_A_Z.md) and [single notebook](notebooks/RiskMatch_V3.ipynb). Follow prerequisites and work on chapters 01 and 12 together.
4. Double-click `STOP.command` to stop the V3 services.

If macOS prevents opening a .command file, run the same script in Terminal from this directory. Both services are strictly bound to 127.0.0.1; port 8888 must be available.

```bash
./INSTALL.command
./START.command
# Local tests (no server required)
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests/unit
.venv/bin/python scripts/check_notebooks.py
.venv/bin/python scripts/execute_notebook.py
.venv/bin/python scripts/check_git_exclusions.py
.venv/bin/python scripts/task_dependencies.py --check
.venv/bin/python scripts/task_dependencies.py --ready
```

## Research Cycle

One notebook with 27 numbered chapters, a navigable table of contents, reproducible numerical fixtures, detailed methodology, a live checklist display and historical evidence cells. Each chapter uses the shared engine in `src/riskmatch/` and the same server handlers that power `apps/web/`. The [academic review](docs/PROFESSOR_REVIEW.md) records chapter-by-chapter test results and remaining validation gates.

Generate the local executed historical review copy with `.venv/bin/python scripts/execute_notebook.py --historical --save-outputs`. It is saved in `data/reports/RiskMatch_V3_professeur.ipynb` and requires the original local research archives. The public source notebook contains portable synthetic results. See the [reproduction guide](notebooks/README.md).

The prototype uses a local Python standard-library HTTP server and HTML/CSS/JS. No Node web dependencies are required. React/FastAPI remain planned. The complete structural mandate and experimental 60-card bank (30 per session) are implemented, with exploratory score, coverage, sensitivity and separate dimensions. Six predefined USD allocations remain a stress-only demonstration, with synthetic metrics, shortlist and paper selection. Horizon and financial goals are collected but do not yet change allocation construction. Market feasibility, human behavioral validation, real data, optimizers and costs remain planned.

## Publish on GitHub

The shared V3 repository is [TindeRisk](https://github.com/NvarMaley/TindeRisk).
The original V2 remains accessible in its Git history. Work through feature
branches and reviewed pull requests as described in CONTRIBUTING.md.
Never publish client data, API keys, licensed data or the private historical
notebook. The existing separate RiskMatch- repository was the V3 working source.

## Positioning

Research and paper trading initially. Obtain independent model and applicable regulatory review (including Switzerland if offered there) before personalized real investment advice or execution. No guaranteed returns or incentives to increase risk.
