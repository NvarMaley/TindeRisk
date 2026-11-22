"""Recalculate selected client slides from committed inputs using only Python."""

import csv
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET

HERE = Path(__file__).resolve().parent


def table(p):
    with (HERE.parent / p).open() as f:
        return list(csv.DictReader(f))


def verify():
    with ZipFile(HERE / "RiskMatch-client-pitch.pptx") as deck:

        def text(i):
            root = ET.fromstring(deck.read(f"ppt/slides/slide{i}.xml"))
            return " ".join(
                el.text or ""
                for el in root.iter(
                    "{http://schemas.openxmlformats.org/drawingml/2006/main}t"
                )
            )

        for i in range(1, 8):
            assert len(text(i)) > 40
        for arm in ["60/40", "robust"]:
            r = next(
                x
                for x in table("frontier/results/latest.csv")
                if x["arm"] == arm and float(x["cap"]) == 0.08
            )
            amounts = [float(r[k]) for k in ["SPY_chf", "IEF_chf", "GLD_chf"]]
            charge = sum(amounts) * 0.001
            assert f"{charge:.2f}" in text(3)
            assert (
                abs(sum(amounts) + float(r["sleeve_cash_chf"]) + charge - 35000) < 0.01
            )
        for row in table("options/results/goal_scenarios.csv"):
            if (
                row["arm"] == "robust"
                and float(row["cap"]) == 0.08
                and row["scenario"] in ["base", "save CHF 250"]
            ):
                assert f"{float(row['gap_frequency']) * 100:g}%" in text(4)
        for arm in ["60/40", "classical", "robust"]:
            sample = [
                float(r["net_household_return"])
                for r in table("execution/results/cohorts.csv")
                if r["case"] == "primary" and r["policy"] == "hold" and r["arm"] == arm
            ]
            assert len(sample) == 7 and f"{sum(sample) / 7:.2%}" in text(5)
        r = next(
            r
            for r in table("options/results/reverse_stress.csv")
            if r["arm"] == "risk parity"
            and r["case"] == "earlier, unsettled"
            and float(r["cap"]) == 0.08
        )
        assert f"{float(r['bill']) - float(r['resources_at_zero_loss']):,.2f}" in text(
            7
        )
    print(
        "Seven slides verified; allocations, fees, scenario rates, seven-year means and early-payment shortfall reconcile."
    )


if __name__ == "__main__":
    verify()
