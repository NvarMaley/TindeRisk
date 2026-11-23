"""Regressions for close valuation, cash settlement and simulated confirmations."""

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from riskmatch_v2.matching.ledger import Ledger, replay_evidence

D1 = "2026-10-26"
D2 = "2026-10-27"
D3 = "2026-10-28"


def mark(day, price=10.0, fx=1.0):
    return {
        "price": price,
        "fx": fx,
        "price_at": day + "T20:00:00Z",
        "fx_at": day + "T19:00:00Z",
    }


class MatchLedgerTests(unittest.TestCase):
    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name)
        self.book = Ledger.create(self.directory)
        self.book.save_mandate({"demo": "fictional"})
        self.book.flow(D1, 1000, "initial")
        self.book.mark(D1, {"A": mark(D1)})

    def test_draft_must_match_inputs_used_during_calculation(self):
        old = self.book.account(D1)
        self.book.flow(D1, 100, "during-calculation")
        with self.assertRaisesRegex(ValueError, "changed during"):
            self.book.propose(
                D1, {"A": 5}, {"Example": 1}, expected_revision=old["revision"]
            )
        self.book.save_mandate({"new": "fictional"})
        with self.assertRaisesRegex(ValueError, "changed during"):
            self.book.propose(
                D1, {"A": 5}, {"Example": 1}, expected_mandate=old["mandate_version"]
            )

    def test_hand_replay_and_confirmation_races(self):
        evidence = replay_evidence(self.directory)
        self.assertTrue(all(evidence["controls"].values()))
        self.assertAlmostEqual(evidence["entry_fee_chf"], 0.6)
        self.assertAlmostEqual(evidence["hand_ledger"][-1]["twr"], evidence["hand_twr"])
        self.assertEqual(evidence["confirmation_versions"], [2, 2])
        self.assertEqual(evidence["revision_movements"], 2)

    def test_flow_neutral_returns_and_settlement(self):
        first = self.book.propose(D1, {"A": 50}, {"Original": 1}, fee_rate=0.0)
        self.book.confirm(first, D1)
        self.book.mark(D2, {"A": mark(D2)})
        self.book.flow(D2, -100, "withdrawal")
        sale = self.book.propose(
            D2, {"A": 20}, {"Lower risk": 1}, fee_rate=0.0, settlement_day=D3
        )
        self.book.confirm(sale, D2)
        self.assertEqual(self.book.account(D2)["cash"], 700)
        self.assertEqual(self.book.account(D2)["settled_cash"], 400)
        self.assertEqual(self.book.account(D3)["settled_cash"], 700)
        self.assertEqual(self.book.history()[-1]["twr"], 0)
        with self.assertRaisesRegex(ValueError, "settled"):
            self.book.flow(D2, -401)
        self.book.flow(D3, 200, "extra")
        self.assertEqual(self.book.account(D3)["value"], 1100)
        self.assertEqual(self.book.history()[-1]["twr"], 0)

    def test_quote_revisions_invalidate_new_fills_and_preserve_old(self):
        first = self.book.propose(D1, {"A": 40}, {"First": 1})
        self.book.confirm(first, D1)
        pending = self.book.propose(D1, {"A": 35}, {"Second": 1})
        self.assertFalse(self.book.mark(D1, {"A": mark(D1)}))
        self.assertTrue(self.book.mark(D1, {"A": mark(D1, 11)}))
        with self.assertRaisesRegex(ValueError, "current"):
            self.book.confirm(pending, D1)
        self.assertEqual(self.book.proposal(pending)["status"], "obsolete")
        export = self.book.export()
        self.assertEqual(len(export["quotes"]), 2)
        self.assertEqual(export["trades"][0]["price"], 10)
        self.assertEqual(export["portfolios"][0]["targets"], {"A": 40})
        self.assertAlmostEqual(self.book.account(D1)["value"], 1039.6)
        self.assertAlmostEqual(sum(self.book.account(D1)["weights"].values()), 1.0)

    def test_marks_need_timestamp_and_whole_targets(self):
        with self.assertRaisesRegex(ValueError, "UTC offsets"):
            self.book.mark(D1, {"A": dict(mark(D1), fx_at=D1 + "T19:00")})
        with self.assertRaisesRegex(ValueError, "future"):
            self.book.mark(D1, {"A": mark(D2)})
        with self.assertRaisesRegex(ValueError, "whole units"):
            self.book.propose(D1, {"A": 0.5}, {"Example": 1})
        self.book.mark(D2, {"A": dict(mark(D2), fx_at=D1 + "T19:00Z")})
        with self.assertRaisesRegex(ValueError, "stale"):
            self.book.propose(D2, {"A": 1}, {"Example": 1})
        self.assertEqual(self.book.latest_day(), D2)

    def test_old_tab_cannot_match_against_an_already_superseded_session(self):
        self.book.mark(D2, {"A": mark(D2)})
        with self.assertRaisesRegex(ValueError, "predates"):
            self.book.propose(D1, {"A": 1}, {"Example": 1})
        self.assertEqual(self.book.account(D1)["value"], 1000)
        self.book.save_mandate(
            {"demo": "fictional", "blocked_reason": "Budget requires confirmation."}
        )
        with self.assertRaisesRegex(ValueError, "Budget requires confirmation"):
            self.book.propose(D2, {}, {"Cash": 1})

    def test_flow_retry_and_mandate_reopening(self):
        self.book.flow(D1, 1000, "initial")
        with self.assertRaisesRegex(ValueError, "identifier"):
            self.book.flow(D1, 2000, "initial")
        self.assertEqual(self.book.account(D1)["value"], 1000)
        self.assertEqual(self.book.save_mandate({"demo": "fictional"}), 1)
        self.book.invalidate_mandate()
        reopened = Ledger(self.directory, self.book.token)
        self.assertIsNone(reopened.current_mandate())
        self.assertEqual(
            reopened.latest_mandate(),
            {"version": 1, "active": False, "payload": {"demo": "fictional"}},
        )
        with self.assertRaisesRegex(ValueError, "mandate"):
            reopened.propose(D1, {}, {"Cash": 1})
        self.assertEqual(
            reopened.save_mandate({"demo": "fictional", "ceiling": 0.15}), 2
        )
        self.assertEqual(len(reopened.export()["mandates"]), 2)

    def test_capability_absent_from_export_and_two_accounts_isolated(self):
        other = Ledger.create(self.directory)
        self.assertEqual(other.export()["flows"], [])
        self.assertIsNone(other.latest_day())
        self.assertIsNone(other.latest_mandate())
        self.assertNotIn(self.book.token, json.dumps(self.book.export()))
        self.assertTrue(
            all(p.stat().st_mode & 0o077 == 0 for p in self.directory.glob("*.sqlite3"))
        )
        original = self.book.token
        self.book.delete()
        with self.assertRaisesRegex(ValueError, "Unknown"):
            Ledger(self.directory, original)
        with self.assertRaisesRegex(ValueError, "Unknown"):
            self.book.export()
        self.assertEqual(other.export()["trades"], [])


if __name__ == "__main__":
    unittest.main()
