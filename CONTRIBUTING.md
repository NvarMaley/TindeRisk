# Contributing

TindeRisk is the shared V3 repository. Use feature branches and reviewed pull requests with green CI. Protect the default branch and verify collaborator permissions before further shared development.

1. Choose an available ticket using `python scripts/task_dependencies.py --ready`. Open an issue with ID, goal, assumptions, acceptance criteria, dependencies and owner.
2. Create branch `feature/infra-01-environment` (pattern `feature/<ticket>-<slug>`) from main. Use commit messages such as `INFRA.01: lock Python environment`. No direct commits to main once protection is configured.
3. Add tests, formula documentation, units, sources, limitations and seed where applicable.
4. Run `pytest` and `ruff check .`; open a linked PR.
5. At least one review; independent quantitative review for models and security review for personal data. Squash merge after green CI.

Use English for code, documentation, notebook, issues and PRs. Web UI provides EN/FR localization. Use Python type hints, public docstrings, snake_case, UTC timestamps and explicit currencies. Separate live data and fixtures; no performance results without period, benchmark and costs. Document architecture decisions in docs/ through PR. Do not add licenses without co-author agreement.

Evidence: ticket owner, direct dependencies, notebook cell/section, implementation reference, test output, experiment run ID, UI evidence when applicable, limitations and reviewed PR. Update the A–Z checklist only when all acceptance criteria pass. Python 3.12 and `requirements.lock` are the common baseline; local data never enters Git. See [experiment registry](docs/EXPERIMENT_REGISTRY.md).
