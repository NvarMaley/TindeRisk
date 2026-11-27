# RiskMatch — V3

**Understand risk. Explore strategies. Build a suitable portfolio.**

A collaborative quantitative US multi-asset research and development platform. RiskMatch combines portfolio discovery cards with a reproducible quantitative engine. V3 currently contains a demonstration Web App and shared engine using synthetic data; no financial model or questionnaire has been independently validated.

**Treasury-only fixed-income universe:** T-Bills, Treasury Notes, Treasury Bonds, TIPS and bond ETFs with verified exclusively Treasury exposure. No corporate debt, MBS, agencies, municipal debt or mixed bond ETFs. US equities, REITs, eligible futures and USD cash remain in scope. Treasury Curve (slope/curvature) replaces the original Credit factor, retaining 13 factors.

## QARM II course demonstration

[Open the Streamlit demonstration](https://nvarmaley.github.io/TindeRisk/) and
compare two loss limits for a fictional investment mandate. The demonstration
runs the project's constrained optimizer on reproducible synthetic returns.
[Local launch and deployment instructions](apps/course_demo/README.md).

## User Experience

1. Mandate: goals, investable wealth, horizon, cash flows, constraints, base currency and financial loss capacity.
2. RiskMatch Discovery: a fixed bilingual questionnaire with the same 30 cards in every session (Yes to accept the proposed switch, No to keep the starting option, plus unsure, skip and undo), with a separately consented local session.
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

The prototype uses a local Python standard-library HTTP server and HTML/CSS/JS. No Node web dependencies are required. The client Universe and full-mandate Match route share a dated set of US stocks, equity ETFs and US Treasury ETFs with 60 consecutive months of usable total returns through 31 December 2025, plus a USD cash proxy. The client form offers ten goals, and Discovery uses 30 fixed cards with a prudence index and experimental loss-aversion ranges. Historical performance, scenario losses, goal projections and the chosen sleeve allocation are computed by the shared quantitative engine. See the [mandate](docs/CLIENT_MANDATE.md), [Discovery rules](docs/RISKMATCH_BEHAVIORAL.md) and [personalized construction methodology](docs/PERSONALIZED_MATCHING.md) for the current implementation.

## Publish on GitHub

The shared V3 repository is [TindeRisk](https://github.com/NvarMaley/TindeRisk).
The original V2 remains accessible in its Git history. Work through feature
branches and reviewed pull requests as described in CONTRIBUTING.md.
Never publish client data, API keys, licensed data or the private historical
notebook. The existing separate RiskMatch- repository was the V3 working source.

## Positioning

Research and paper trading initially. Obtain independent model and applicable regulatory review (including Switzerland if offered there) before personalized real investment advice or execution. No guaranteed returns or incentives to increase risk.

### Paper portfolio tracking

Configure `APCA_API_KEY_ID` and `APCA_API_SECRET_KEY` in a local `.env` file using
`.env.example` as a reference, or export them before starting the server.
`ALPACA_DATA_FEED` defaults to `iex`. Use `sip` or `delayed_sip` only if your
Alpaca account has access to that feed.

In **My Matches**, confirm a historical or personalized allocation with
market-traded holdings. For a previously confirmed local save, evaluate and
confirm the allocation again to initialize tracking. Only symbols are sent
to Alpaca. A complete set of quotes establishes the initial simulated holdings.
The page shows the quote timestamps, position drift and value since the first
complete valuation. It refreshes every minute while open. You can keep the
original positions or select quarterly paper rebalancing. A due rebalance
uses the first complete set of recent prices that the open page receives.
The local save holds the positions, recent valuations and rebalance log.
The tracked result reflects price changes, excluding dividends, corporate
actions and trading costs.

## Course review

The original client interface is the app in `apps/web`, also displayed by the
[Streamlit wrapper](apps/streamlit/README.md). It needs the original RiskMatch
server and its verified local archives for the portfolio workflow. The
portable notebook in `notebooks/` runs numerical examples with data supplied
in the repository. Historical notebook outputs are generated locally from the
authorized research archive.

The Research menu provides the asset universe, sources and missing data,
strategy catalogue and methodology. The [current data guide](docs/UNIVERS_DONNEES_STRATEGIES.md)
and [course review](docs/PROFESSOR_REVIEW.md) describe the active 60-month
portfolio panel. Earlier full manuals document historical iterations. The
live quote feature needs an Alpaca feed configured on the host.
