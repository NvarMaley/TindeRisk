# Collaborating on the Project

## Getting Started

```bash
git clone https://github.com/NvarMaley/TindeRisk.git
cd TindeRisk
python --version                 # use Python 3.12
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app/Home.py
```

## Basic Rules

1. Select a task in [`CHECKLIST.md`](CHECKLIST.md) and assign its ID to yourself.
2. Create a short-lived branch: `feature/questionnaire`, `feature/backtest`, etc.
3. One task = one small, testable pull request.
4. Update the checklist only after the work has been verified.
5. Never push secrets, personal data, or large raw files.
6. Every function added to `src/` must have at least one test in `tests/`.

## Where to Work

| Need | Location |
|---|---|
| Download / clean data | `src/data_loader.py`, `data/` |
| Question bank and questionnaire engine | `questions/`, `src/questionnaire.py`, `src/profiling.py` |
| Estimators and strategies | `src/estimation.py`, `src/optim.py` |
| Signals and regimes | `src/signals.py` |
| Backtesting and monitoring | `src/backtest.py`, `src/monitoring.py` |
| User interface | `app/` |
| Experiments and figures | `RiskMatch_pipeline.ipynb` |
| Tests | `tests/` |

## Checks Before Opening a Pull Request

```bash
make check
make app
```

The pull request must also pass GitHub CI. A task is complete only after another person has reviewed the code, tests, documentation, and reproducible evidence.

