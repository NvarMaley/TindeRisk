import unittest
import numpy as np
from riskmatch.dynamic.policies import POLICIES, simulate, targets


class DynamicTests(unittest.TestCase):
    def fixture(self):
        rng=np.random.default_rng(26)
        return rng.normal(.004,.035,(48,2)),np.full(48,.001),list(range(48))

    def test_policies_and_cash_ledger(self):
        x,c,d=self.fixture()
        for p in ("static","drift",*POLICIES):
            r=simulate(x,c,d,30,100000,p,[.6,.4],.15,.2,contribution=500)
            self.assertEqual(r["status"],"computed")
            self.assertEqual(len(r["ledger"]),18)
            self.assertGreaterEqual(r["fees"],0)
            for row in r["ledger"]:
                self.assertLessEqual(row["stress_estimate"],.15+1e-8)
                self.assertAlmostEqual(sum(row["weights"]),1)

    def test_future_does_not_change_decisions(self):
        x,c,d=self.fixture()
        for p in POLICIES:
            original=simulate(x,c,d,30,100000,p,[.6,.4],.2,.2)
            modified=x.copy();modified[35:]*=-1
            later=simulate(modified,c,d,30,100000,p,[.6,.4],.2,.2)
            self.assertEqual(original["ledger"][:5],later["ledger"][:5])
        self.assertEqual(set(targets(x[:20,0],.5,.001)),set(POLICIES))

    def test_shortfall(self):
        x,c,d=self.fixture()
        r=simulate(x,c,d,30,100,"static",[.6,.4],.2,.2,withdrawal=200)
        self.assertEqual(r["shortfall"],100)
