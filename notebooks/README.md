# RiskMatch V3 research notebook

Open [RiskMatch_V3.ipynb](RiskMatch_V3.ipynb) for the 27 chapters. Run commands from the repository root with Python 3.12.

1. Install the pinned environment with `./INSTALL.command`.
2. Start `.venv/bin/jupyter lab notebooks/RiskMatch_V3.ipynb`. Select **Restart Kernel and Run All Cells**. The default run uses versioned examples and seeded synthetic series. Each chapter displays its corresponding entries from the current [checklist](../CHECKLIST_A_Z.md). Catalogs and cross-cutting tasks are grouped with the relevant chapters.
3. For a non-interactive replay, run `.venv/bin/python scripts/execute_notebook.py`. It checks every code cell in order and leaves the notebook file untouched. Add `--in-process` to run with IPython on machines that restrict local kernel ports. Add `--save-outputs` to update the portable outputs.
4. On the machine holding the frozen historical inputs, run `.venv/bin/python scripts/execute_notebook.py --historical --save-outputs`, or start Jupyter with `RISKMATCH_NOTEBOOK_HISTORY=1 .venv/bin/jupyter lab notebooks/RiskMatch_V3.ipynb`. The command generates the complete local review copy at `data/reports/RiskMatch_V3_professeur.ipynb`. All chapters replay the same server handlers used by the web app, with full JSON results, tables, candidate weights, holding-period paths and archive checks. The source notebook remains portable. The historical copy defaults to historical mode. See [matching](../docs/PORTFOLIO_MATCHING.md) and [data acquisition](../docs/DATA_ACQUISITION_PLAN.md). The engine checks the archive versions. Keep historical outputs private pending rights review.

Saved calculation outputs illustrate the portable run. Dated evidence in chapter notes documents earlier research. Replaying the notebook does not reacquire vendor data or retrain every archived universe-wide experiment.

The client sections describe the [simplified mandate](../docs/CLIENT_MANDATE.md),
the [30 fixed Discovery questions](../docs/RISKMATCH_BEHAVIORAL.md) and the
[568-instrument USD portfolio panel plus cash](../docs/PERSONALIZED_MATCHING.md).
