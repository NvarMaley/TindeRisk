from datetime import date
import hashlib, json, sys, unittest, shutil, tempfile
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "src"))
from riskmatch.catalogue import approved, CAT


class Catalogue(unittest.TestCase):
    def test_release_and_gate(self):
        args = (
            date(2026, 11, 23),
            "CHF",
            "illustrative CHF 50000",
            "synthetic local demonstration",
        )
        r = approved("demo/manual/v1", *args)
        self.assertEqual(35000 * 0.5 * r["cost_bp"] / 10000, 17.5)
        self.assertIsNone(approved("H06/v2/cross-instrument sentiment", *args))
        self.assertIsNone(approved("demo/manual/v2", *args))
        self.assertIsNone(approved(r["id"], date(2027, 11, 23), *args[1:]))
        self.assertIsNone(approved(r["id"], *args[:-1], "live trading"))
        with tempfile.TemporaryDirectory() as d:
            dst = Path(d)
            [
                shutil.copy(CAT / n, dst / n)
                for n in ["catalogue.sig", "signer.pem", "catalogue.json"]
            ]
            with (dst / "catalogue.json").open("a") as f:
                f.write(" ")
            with self.assertRaises(ValueError):
                approved(r["id"], *args, directory=dst)


if __name__ == "__main__":
    unittest.main()
