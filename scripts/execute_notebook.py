"""Replay the complete research notebook from a fresh kernel."""

import argparse
import os
from pathlib import Path
import sys
import tempfile

import nbformat
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--historical", action="store_true", help="Also replay the private frozen USD case.")
    parser.add_argument("--in-process", action="store_true", help="Use IPython directly when local kernel ports are unavailable.")
    parser.add_argument("--save-outputs", action="store_true",
                        help="Save portable results in the main notebook, or historical results in data/reports.")
    args = parser.parse_args()
    notebook = nbformat.read(ROOT / "notebooks/RiskMatch_V3.ipynb", as_version=4)
    with tempfile.TemporaryDirectory(prefix="riskmatch-notebook-") as runtime:
        env = dict(os.environ, JUPYTER_RUNTIME_DIR=runtime, IPYTHONDIR=str(Path(runtime) / "ipython"),
                   RISKMATCH_NOTEBOOK_HISTORY=str(int(args.historical)))
        # Resolve python3 to the same interpreter that launched the replay.
        env["PATH"] = str(Path(sys.executable).parent) + os.pathsep + env.get("PATH", "")
        if args.in_process:
            os.environ.update(env)
            os.chdir(ROOT)
            from IPython.core.interactiveshell import InteractiveShell
            from IPython.utils.capture import capture_output
            from traitlets.config import Config

            config = Config()
            config.HistoryManager.enabled = False
            shell = InteractiveShell.instance(config=config)
            count = 0
            for cell in notebook.cells:
                if cell.cell_type == "code":
                    count += 1
                    values = []
                    shell.displayhook.write_output_prompt = lambda: None
                    shell.displayhook.write_format_data = lambda data, metadata=None: values.append((data, metadata or {}))
                    with capture_output() as captured:
                        result = shell.run_cell(cell.source, store_history=True)
                    if not result.success:
                        print(f"Failed in cell {cell.id}", file=sys.stderr)
                        result.raise_error()
                    cell.execution_count = count
                    cell.outputs = []
                    for name in ("stdout", "stderr"):
                        value = getattr(captured, name)
                        if value:
                            cell.outputs.append(nbformat.v4.new_output("stream", name=name, text=value))
                    for output in captured.outputs:
                        cell.outputs.append(nbformat.v4.new_output("display_data", data=output.data,
                                                                    metadata=output.metadata))
                    for data, metadata in values:
                        cell.outputs.append(nbformat.v4.new_output("execute_result", data=data,
                                                                    metadata=metadata, execution_count=count))
                    if args.save_outputs:
                        print(f"Executed {count}: {cell.id}", flush=True)
        else:
            NotebookClient(notebook, kernel_name="python3", timeout=300,
                           resources={"metadata": {"path": str(ROOT)}}).execute(env=env)
    count = sum(c.cell_type == "code" for c in notebook.cells)
    if args.save_outputs:
        target = ROOT / ("data/reports/RiskMatch_V3_professeur.ipynb" if args.historical
                         else "notebooks/RiskMatch_V3.ipynb")
        if args.historical:
            # This copy lives one directory deeper and defaults to historical replay.
            for cell in notebook.cells:
                if cell.id == "8f95cdb2":
                    cell.source = cell.source.replace('get("RISKMATCH_NOTEBOOK_HISTORY", "0")',
                                                      'get("RISKMATCH_NOTEBOOK_HISTORY", "1")')
                elif cell.cell_type == "markdown":
                    cell.source = cell.source.replace("](../", "](../../")
            notebook.cells[0].source += ("\n\n**Local historical review copy.** The saved outputs are from "
                                         "private local research archives. Review redistribution rights before sharing.")
        target.parent.mkdir(parents=True, exist_ok=True)
        nbformat.validate(notebook)
        nbformat.write(notebook, target)
        if args.historical:
            target.chmod(0o600)
        print(f"Executed all {count} code cells. Saved: {target}")
    else:
        print(f"Executed all {count} code cells. Historical mode: {args.historical}. No outputs written.")


if __name__ == "__main__":
    main()
