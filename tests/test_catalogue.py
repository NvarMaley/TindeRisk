from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from riskmatch_v2.catalogue import describe, equal_weight_reference, instrument_panel, load_catalogue


class CatalogueTest(unittest.TestCase):
    def test_packaged_catalogue_filters_dates_and_factors(self):
        panel = instrument_panel(load_catalogue(), date(2025, 3, 31))
        self.assertEqual(len(panel), 5)
        self.assertNotIn("DEMO_OIL", panel)
        reference = equal_weight_reference(panel)
        self.assertEqual(len(reference), 3)
        self.assertAlmostEqual(reference[date(2025, 1, 31)], 0.0058)

    def test_reference_compounds_only_shared_dates(self):
        days = [date(2025, month, 28) for month in range(1, 4)]
        panel = {"A": dict(zip(days, (0.10, -0.10, 0.50))),
                 "B": dict(zip(days[:2], (0.0, -0.10)))}
        report = describe(list(equal_weight_reference(panel).values()))
        self.assertAlmostEqual(report["cumulative_return"], 1.05 * 0.90 - 1)
        self.assertEqual(report["observations"], 2)

    def test_explicit_import_rejects_duplicate_asset_dates(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "returns.csv"
            header = "date,asset_id,asset_class,role,return_chf,source\n"
            row = "2025-01-31,A,stock,instrument,0.01,test\n"
            path.write_text(header + row, encoding="utf-8")
            self.assertEqual(load_catalogue(path)[0].source, "test")
            path.write_text(header + row * 2, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Invalid catalog row 3"):
                load_catalogue(path)
