"""Validate checklist coverage against the original guide and master notebook."""
from pathlib import Path
import re
import nbformat

root = Path(__file__).resolve().parents[1]
guide = (root / "docs/QUANT_GUIDE_A_Z.md").read_text()
checklist = (root / "CHECKLIST_A_Z.md").read_text()
notebook = nbformat.read(root / "notebooks/RiskMatch_V3.ipynb", as_version=4)

for chapter in range(1, 28):
    assert f"## {chapter:02}." in checklist
    assert f"notebooks/RiskMatch_V3.ipynb#chapitre-{chapter:02}" in checklist
    assert any(f'id="chapitre-{chapter:02}"' in cell.source for cell in notebook.cells)
    assert re.search(rf"\*\*CH{chapter:02}\.01\*\*", checklist)

for section, prefix, expected in [(5, "OBJ", 11), (6, "OPT", 22), (7, "STR", 19), (13, "DYN", 10)]:
    part = guide.split(f"## {section}. ", 1)[1].split("\n## ", 1)[0]
    names = [line.split("|")[1].strip() for line in part.splitlines() if line.startswith("| ")]
    names = [name for name in names if name not in ("Objective", "Method", "Strategy")]
    assert len(names) == expected, (section, names)
    for i, name in enumerate(names, 1):
        assert f"### {prefix}{i:02} — {name}\n" in checklist, name
        assert len(re.findall(rf"\*\*{prefix}{i:02}\.\d{{2}}\*\*", checklist)) == 10, name

factors = ["Market", "Value", "Size", "Momentum", "Quality", "Low Volatility", "Profitability",
           "Investment", "Carry", "Term", "Treasury Curve", "Liquidity", "Inflation"]
for i, name in enumerate(factors, 1):
    assert f"### FAC{i:02} — {name}\n" in checklist, name
    assert len(re.findall(rf"\*\*FAC{i:02}\.\d{{2}}\*\*", checklist)) == 10, name

ids = re.findall(r"^- \[[ xX]\] \*\*([A-Z0-9.]+)\*\*", checklist, re.M)
assert len(ids) == len(set(ids)), "Duplicate task IDs"
assert len(ids) >= 1200
assert len(re.findall(r"^### MET\d{2} —", checklist, re.M)) == 23
total = len(re.findall(r"^- \[[ xX]\]", checklist, re.M))
print(f"Verified coverage: 27 chapters, 75 catalog entries, 23 metrics, {len(ids)} identified tickets, {total} checkboxes.")
