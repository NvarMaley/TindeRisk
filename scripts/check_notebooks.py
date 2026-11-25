from pathlib import Path
import hashlib
import re
import nbformat

paths = sorted(Path("notebooks").glob("*.ipynb"))
assert [p.name for p in paths] == ["RiskMatch_V3.ipynb"], paths
notebook = nbformat.read(paths[0], as_version=4)
nbformat.validate(notebook)
for number in range(1, 28):
    assert any(f'id="chapitre-{number:02}"' in c.source for c in notebook.cells), number
    assert any(c.id == f"evidence-{number:02}" and c.cell_type == "code" for c in notebook.cells), number
    assert any(c.id == f"checklist-{number:02}" and c.cell_type == "code" for c in notebook.cells), number
code = [c for c in notebook.cells if c.cell_type == "code"]
assert all(c.execution_count == i and c.outputs for i, c in enumerate(code, 1))
assert not any(o.output_type == "error" for c in code for o in c.outputs)
setup = next(c for c in code if c.id == "8f95cdb2")
assert any("Mode historique : False" in o.get("text", "") for o in setup.outputs)
rendered = "".join(o.get("data", {}).get("text/html", "") for c in code
                   if c.id == setup.id or c.id.startswith("checklist-") for o in c.outputs)
checklist = Path("CHECKLIST_A_Z.md").read_text()
assert rendered.count("<div>☑ ") + rendered.count("<div>☐ ") == len(re.findall(r"^- \[[ xX]\]", checklist, re.M))
assert any(hashlib.sha256(checklist.encode()).hexdigest() in o.get("text", "") for o in setup.outputs)
print(f"Single notebook validated: 27 chapters, {len(code)} executed cells, complete checklist display.")
