from datetime import date
from pathlib import Path
from zipfile import ZipFile


def test_factor_frequency_and_percent_units(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2]/"scripts"))
    from pit_supplemental import factor_rows
    archive = tmp_path/"F-F_fixture.zip"
    with ZipFile(archive, "w") as stream:
        stream.writestr("fixture.csv", ",Mom,RF\n202402,2.5,0.4\n202403,-99.99,0.1\n2024,10,1\n")
    assert list(factor_rows(archive,"fixture")) == [
        ("Mom",date(2024,2,29),"monthly",0.025,"fixture"),
        ("RF",date(2024,2,29),"monthly",0.004,"fixture"),
        ("RF",date(2024,3,31),"monthly",0.001,"fixture"),
    ]


def test_sparse_vintage_cells_keep_source_column(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2]/"scripts"))
    from pit_supplemental import macro_rows
    file = tmp_path/"macro.xlsx"
    with ZipFile(file,"w") as stream:
        stream.writestr("xl/worksheets/sheet1.xml", """<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
        <sheetData><row><c r="A1"><v>DATE</v></c><c r="B1"><v>V1</v></c><c r="C1"><v>V2</v></c></row>
        <row><c r="A2"><v>2024:Q2</v></c><c r="C2"><v>101</v></c></row></sheetData></worksheet>""")
    assert list(macro_rows(file,"real_output","fixture")) == [
        ("real_output",date(2024,4,1),"V2",101.0,"fixture")
    ]
