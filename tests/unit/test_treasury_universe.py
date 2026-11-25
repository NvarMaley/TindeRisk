import unittest

from riskmatch.market_data.universe import Holding, treasury_eligible, treasury_etf_eligible


class TreasuryUniverseTests(unittest.TestCase):
    def test_treasury_families(self):
        for instrument in ("treasury_bill", "treasury_note", "treasury_bond", "tips"):
            self.assertTrue(treasury_eligible(Holding(instrument, "US_TREASURY")))

    def test_exclusions(self):
        for instrument, issuer in (
            ("corporate_bond", "US_COMPANY"),
            ("municipal_bond", "US_CITY"),
            ("agency_bond", "US_AGENCY"),
            ("mbs", "US_AGENCY"),
            ("treasury_bond", "FOREIGN_GOVERNMENT"),
            ("unknown", "US_TREASURY"),
            ("treasury_note", ""),
        ):
            self.assertFalse(treasury_eligible(Holding(instrument, issuer)))
        self.assertFalse(treasury_eligible(Holding("treasury_bill", "US_TREASURY", "EUR")))

    def test_etf_fail_closed(self):
        treasury = Holding("treasury_note", "US_TREASURY")
        cash = Holding("cash", "CUSTODIAN")
        credit = Holding("corporate_bond", "US_COMPANY")
        self.assertTrue(treasury_etf_eligible((treasury, cash), verified_as_of=True))
        self.assertFalse(treasury_etf_eligible((treasury, credit), verified_as_of=True))
        self.assertFalse(treasury_etf_eligible((treasury,), verified_as_of=False))
        self.assertFalse(treasury_etf_eligible((cash,), verified_as_of=True))
        self.assertFalse(treasury_etf_eligible((), verified_as_of=True))
