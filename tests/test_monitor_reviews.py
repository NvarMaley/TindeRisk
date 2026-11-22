import sys, tempfile, unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from riskmatch.monitor import create, advance, history
from riskmatch.reviews import revise, prepare, respond, shadows


class Reviews(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.p = Path(self.tmp.name) / "db"
        self.t = create([0.4, 0.28, 0], 0.08, "fixture", True, self.p)

    def test_single_confirmation_and_shadow(self):
        revise(self.t, 1, 35000, "2026-11-30", 0.08, self.p)
        r = prepare(self.t, path=self.p)
        self.assertEqual(r["status"], "proposal")
        self.assertLess(r["trade_shortfall"], 0.01)
        with ThreadPoolExecutor(2) as exe:
            ans = list(
                exe.map(
                    lambda _: respond(self.t, r["review_id"], "accept", self.p), [1, 2]
                )
            )
        self.assertCountEqual(ans, ["accept", "already recorded"])
        advance(self.t, 0, self.p)
        s, e = history(self.t, self.p)
        self.assertEqual(sum(x["kind"] == "decision" for x in e), 1)
        self.assertTrue(shadows(e))

    def test_stale_decline_and_settlement(self):
        revise(self.t, 1, 40000, "2026-11-23", 0.08, self.p)
        r = prepare(self.t, False, True, self.p)
        self.assertGreater(r["trade_shortfall"], 0)
        self.assertEqual(respond(self.t, r["review_id"], "decline", self.p), "decline")
        r = prepare(self.t, True, False, self.p)
        advance(self.t, 0, self.p)
        self.assertEqual(respond(self.t, r["review_id"], "accept", self.p), "expired")
        advance(self.t, 1, self.p)
        self.assertEqual(prepare(self.t, path=self.p)["status"], "suspended")


if __name__ == "__main__":
    unittest.main()
