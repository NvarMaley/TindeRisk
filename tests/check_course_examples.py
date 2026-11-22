"""Run the course demonstration's synthetic notebook fixtures using only Python."""
import json
import math
from pathlib import Path
from unittest import TestCase, main

ROOT = Path(__file__).resolve().parents[1]
CELLS = {
    cell["id"]: "".join(cell["source"])
    for cell in json.loads((ROOT / "RiskMatch.ipynb").read_text())["cells"]
    if cell["cell_type"] == "code"
}


class CourseExamples(TestCase):
    def example(self, cell_id):
        namespace = {"isclose": math.isclose}
        exec(compile(CELLS[cell_id], f"RiskMatch.ipynb#{cell_id}", "exec"), namespace)
        return namespace

    def test_funding_and_tolerance(self):
        review = self.example("281bc0c7")["review_example"]
        self.assertEqual(review(6, 6, 5000)[:2], (15000, 35000))
        self.assertEqual(review(6, 24, 5000)[:2], (10000, 40000))

    def test_minimum_variance(self):
        case = self.example("2e95540c")
        self.assertAlmostEqual(case["portfolio_variance"](case["w1"]), 0.008)

    def test_withdrawal_boundary(self):
        boundary = self.example("b8d84927")["first_shortfall_boundary"]
        self.assertAlmostEqual(boundary(12000, 10000, 15000)[1], 0.7)


if __name__ == "__main__":
    main()
