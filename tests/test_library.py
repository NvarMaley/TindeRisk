from importlib.util import find_spec
from unittest import TestCase, skipUnless


@skipUnless(find_spec("duckdb") and find_spec("exchange_calendars"), "Catalogue option required")
class MarketLibraryTest(TestCase):
    def test_identity_reuse_is_date_bound(self):
        import pandas as pd
        from riskmatch_v2.library.controls import identity_at
        table=pd.DataFrame([[10,"ABC","2020-01-01","2023-05-10"],[22,"ABC","2024-02-01","2026-12-31"]],
                           columns=["permno","ticker","id_from","id_to"])
        self.assertEqual(identity_at(table,"ABC","2022-12-01"),10)
        self.assertIsNone(identity_at(table,"ABC","2023-12-01"))
        self.assertEqual(identity_at(table,"ABC","2025-12-01"),22)
        table.loc[1,"id_from"]="2021-01-01"
        self.assertIsNone(identity_at(table,"ABC","2022-12-01"))

    def test_events_fx_calendar_and_missing_prices(self):
        import exchange_calendars as xc
        import pandas as pd
        import numpy as np
        from riskmatch_v2.library.controls import align_sessions, corporate_return, chf_return
        # 2 new shares worth 51 plus 1 dividend per new share on a 100 investment.
        usd=corporate_return(100,51,1,2)
        self.assertAlmostEqual(usd,.04)
        self.assertAlmostEqual(chf_return(usd,.9,.81),-.064)
        self.assertAlmostEqual(chf_return(usd,1/.9,1/.81,"USD/CHF"),-.064)
        days=xc.get_calendar("XNYS").sessions_in_range("2025-07-03","2025-07-09")
        self.assertEqual(days.strftime("%Y-%m-%d").tolist(),["2025-07-03","2025-07-07","2025-07-08","2025-07-09"])
        frame=pd.DataFrame({"adjusted":[100,104,110]},index=days[[0,1,3]])
        aligned=align_sessions(frame,days,pd.Series([.9,.81,.85,.86],index=days))
        self.assertAlmostEqual(aligned.return_chf.iloc[1],-.064)
        self.assertTrue(np.isnan(aligned.return_chf.iloc[3]))
        self.assertEqual(aligned.reason.tolist(),["BASE_PRIX_ABSENTE","OK","PRIX_ABSENT","BASE_PRIX_ABSENTE"])
        with self.assertRaises(ValueError):
            align_sessions(pd.concat([frame,frame]),days,pd.Series(dtype=float))

    def test_tail_risk_and_drawdown_by_hand(self):
        import numpy as np
        from riskmatch_v2.library.statistics import sheet
        dates=np.array(["2024-12-31","2025-01-31","2025-02-28","2025-03-31"],dtype="datetime64[D]")
        s=sheet(3,[-.10,0,.20],[1,1,1,1],dates)
        self.assertAlmostEqual(s["cumulative"],.08)
        self.assertAlmostEqual(s["variance"],.28)
        self.assertAlmostEqual(s["max_drawdown"],-.1)
        self.assertEqual(s["recovery_days"],90)
        self.assertEqual(s["trough_to_recovery_days"],59)
        self.assertEqual(s["tail_n"],1)
        self.assertAlmostEqual(s["es95"],.1)
        missing=sheet(3,[-.10,0,.20],[1,np.nan,1,1],dates)
        self.assertEqual(missing["observations"],1)
        self.assertAlmostEqual(missing["cumulative"],.08)
        partial=sheet(3,[np.nan,0,-.20],[1,1,1,1],dates)
        self.assertIsNone(partial["cumulative"])
        self.assertFalse(partial["full_sample"])
        self.assertEqual(sheet(3,[.10,0,-.20],[1]*4,dates)["recovery_state"],"unrecovered")

    def test_deferred_announcement_revision_and_future_shock(self):
        import pandas as pd
        from riskmatch_v2.library.controls import visible
        df=pd.DataFrame([["X","2025-01-01","2025-01-30T21:04Z",1],
                         ["X","2025-01-01","2025-02-10T12:00Z",2]],columns=["series","day","available","value"])
        def at(cut):
            return visible(df,cut,["series","day"])
        self.assertTrue(at("2025-01-30T21:00Z").empty)
        self.assertEqual(at("2025-01-31T14:30Z").value.tolist(),[1])
        self.assertEqual(at("2025-02-10T12:00Z").value.tolist(),[2])
        df.loc[1,"value"]=-999
        self.assertEqual(at("2025-01-31T14:30Z").value.tolist(),[1])

    def test_eligibility_needs_each_positive_check(self):
        from riskmatch_v2.library.controls import disposition
        policy=dict(decision_utc="2026-11-23T14:00Z",last_closed_us_session="2026-11-20",risk_months_required=36)
        row=dict.fromkeys(["identified","mandate_scope","listed","access","lot","settlement","liquid","fees","distinct","class_terms"],True)
        row.update(role="instrument",price_day="2026-11-20",fx_day="2026-11-20",available="2026-11-21T08:00Z",history=36,currency="USD")
        self.assertEqual(disposition(row,policy),[])
        for changes,reason in [({"ended":True},"SORTIE_OBSERVEE"),({"price_day":"2025-12-31"},"PRIX_NON_FRAIS"),
                               ({"history":3},"HISTORIQUE_RISQUE"),({"access":None},"ACCES_COMPTE"),
                               ({"available":"2026-11-24T15:00Z"},"SOURCE_INDISPONIBLE"),({"role":"factor"},"ROLE_NON_INVESTISSABLE")]:
            self.assertIn(reason,disposition(row|changes,policy))
        older=policy|dict(decision_utc="2025-12-31T21:01Z",last_closed_us_session="2025-12-31")
        historical=row|dict(price_day="2025-12-31",fx_day="2025-12-31",available="2025-12-31T21:00Z")
        self.assertEqual(disposition(historical,older),[])
        self.assertIn("SORTIE_OBSERVEE",disposition(historical|dict(ended=True),policy))

    def test_holdings_vintages_unknown_and_shared_issuer(self):
        import pandas as pd
        from riskmatch_v2.library.controls import exposure,exclusion_status
        df=pd.DataFrame([["F","2025-12-30","2025-12-31T09:00Z","A",.5],
                         ["F","2025-12-30","2025-12-31T09:00Z",None,.3],
                         ["G","2025-12-30","2025-12-31T09:00Z","A",.2],
                         ["F","2026-02-24","2026-02-25T10:00Z","B",1.0]],
                        columns=["fund","day","available","issuer","weight"])
        w={"F":.5,"G":.3,"stockA":.2}
        r=exposure(w,df,{"stockA":"A"},"2026-01-02T10:00Z")
        self.assertAlmostEqual(r["issuers"]["A"],.51)
        self.assertAlmostEqual(r["unknown_net"],.49)
        self.assertEqual(exclusion_status(r,{"B"},True),"suspendu")
        self.assertEqual(exclusion_status(r,{"A"},True),"excluded")
        self.assertEqual(exclusion_status(r,{"B"},False),"partial coverage")
        later=exposure(w,df,{"stockA":"A"},"2026-03-01T10:00Z")
        self.assertAlmostEqual(later["issuers"]["A"],.26)
        self.assertAlmostEqual(later["issuers"]["B"],.5)

    def test_crsp_distributions_conflicts_and_outdated_identity(self):
        import csv
        from pathlib import Path
        from tempfile import TemporaryDirectory
        import pandas as pd
        from riskmatch_v2.library.sources import crsp

        fields = ("PERMNO PERMCO Ticker CUSIP9 IssuerNm PrimaryExch SICCD USIncFlg SecurityType "
                  "SecuritySubType ShareType TradingStatusFlg SecInfoStartDt SecInfoEndDt SecurityBegDt "
                  "SecurityEndDt MthCalDt MthPrcDt MthPrevDt MthPrc MthRet MthVol MthDelFlg MthRetFlg "
                  "DelPaymentType DisExDt DisDivAmt DisFacShr DisSeqNbr DisType DisPaymentType DisPayDt "
                  "DelReasonType").split()
        base = dict(PERMNO=100, PERMCO=10, Ticker="X", SecInfoStartDt="2024-01-01",
                    SecInfoEndDt="2025-03-31", SecurityBegDt="2024-01-01", SecurityEndDt="2025-03-31",
                    MthCalDt="2025-03-31", MthPrc=25, MthRet=.02, MthDelFlg="Y",
                    DelPaymentType="cash", DisExDt="2025-03-24", DisDivAmt=.5, DisSeqNbr=1)
        with TemporaryDirectory() as folder:
            stage = Path(folder)
            with (stage/"input.csv").open("w", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=fields)
                writer.writeheader()
                writer.writerows([base, base | dict(DisDivAmt=.2, DisSeqNbr=2),
                                  base | dict(PERMNO=200), base | dict(PERMNO=200, MthRet=.9),
                                  base | dict(PERMNO=300, SecInfoEndDt="2025-02-28")])
            con = crsp(stage, stage/"input.csv")
            con.close()
            months = pd.read_parquet(stage/"stock_months.parquet")
            self.assertEqual(months.permno.tolist(), [100])
            self.assertAlmostEqual(months.local_return.iloc[0], .02)
            self.assertEqual(months.exit_payment.iloc[0], "cash")
            events = pd.read_parquet(stage/"stock_events.parquet")
            self.assertEqual(len(events[events.permno == 100]), 2)
            rejects = pd.read_parquet(stage/"stock_quarantine.parquet")
            self.assertEqual(dict(zip(rejects.permno, rejects.reason)),
                             {200: "VERSIONS_EN_CONFLIT", 300: "IDENTITE_HORS_DATE"})
