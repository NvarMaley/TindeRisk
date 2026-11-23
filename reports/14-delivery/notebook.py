"""Execute the entire V2 notebook in a new kernel running this exact interpreter."""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import nbformat
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parents[2]


def run(save=False):
    path = ROOT / "RiskMatch_V2.ipynb"
    notebook = nbformat.read(path, as_version=4)
    with TemporaryDirectory() as temp:
        kernel = Path(temp) / "kernels/riskmatch-release"
        kernel.mkdir(parents=True)
        spec = {
            "argv": [
                sys.executable,
                "-m",
                "ipykernel_launcher",
                "-f",
                "{connection_file}",
            ],
            "display_name": "RiskMatch release",
            "language": "python",
        }
        (kernel / "kernel.json").write_text(json.dumps(spec))
        os.environ["JUPYTER_PATH"] = (
            temp + os.pathsep + os.environ.get("JUPYTER_PATH", "")
        )
        client = NotebookClient(
            notebook,
            kernel_name="riskmatch-release",
            timeout=300,
            record_timing=False,
            resources={"metadata": {"path": str(ROOT)}},
        )
        client.execute()
    nbformat.validate(notebook)
    checklist = (ROOT / "CHECKLIST.md").read_text()
    items = {
        n: m
        for m, n in re.findall(
            r"^- \[([ x])\] \*\*(\d+(?:\.\d+)?)\.?(?= )", checklist, re.MULTILINE
        )
    }
    sections = []
    for c in notebook.cells:
        if c.cell_type == "markdown":
            for target in re.findall(r"\]\(([^ )\n]+)\)", c.source):
                if not target.startswith(("#", "https:", "http:")):
                    assert (ROOT / target.split("#")[0]).exists(), target
            step = re.match(r"### (\d+(?:\.\d+)?) · ", c.source)
            if step:
                n = step.group(1)
                assert f"- [{items[n]}]" in c.source
                sections.append(n)
    assert sections == list(items)
    codes = [c for c in notebook.cells if c.cell_type == "code"]
    assert all(c.execution_count for c in codes)
    if save:
        nbformat.write(notebook, path)
    print(
        json.dumps(
            {
                "checklist_items": len(items),
                "executed_cells": len(codes),
                "embedded_figures": sum(
                    "image/png" in o.get("data", {}) for c in codes for o in c.outputs
                ),
                "errors": 0,
            }
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--save", action="store_true")
    run(parser.parse_args().save)
