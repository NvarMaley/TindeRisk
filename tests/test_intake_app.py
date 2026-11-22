"""Walk through the intake, including back navigation and a corrected withdrawal."""

from datetime import date
from pathlib import Path
import unittest
from streamlit.testing.v1 import AppTest


class IntakeApp(unittest.TestCase):
    def test_walkthrough(self):
        app = AppTest.from_file(
            str(Path(__file__).resolve().parents[1] / "app/intake.py")
        ).run()

        def click(label):
            next(b for b in app.button if b.label == label).click().run()
            self.assertFalse(list(app.exception))

        app.text_input(key="input_goal").input("House")
        app.selectbox(key="input_currency").select("CHF")
        app.date_input(key="input_start").set_value(date(2027, 1, 1))
        app.date_input(key="input_end").set_value(date(2029, 1, 1))
        app.text_input(key="input_target").input("35000")
        click("Continue")
        app.text_input(key="input_capital").input("-1")
        click("Continue")
        self.assertTrue(list(app.error))
        app.text_input(key="input_capital").input("50000")
        app.selectbox(key="input_goal_list").select("Complete")
        click("Continue")
        app.text_input(key="input_buffer").input("0")
        click("Add withdrawal")
        app.date_input(key="day0").set_value(date(2028, 1, 1))
        app.text_input(key="amount0").input("10000")
        app.selectbox(key="input_bill_list").select("Complete")
        click("Continue")
        click("Back")
        self.assertEqual(app.text_input(key="amount0").value, "10000")
        app.text_input(key="amount0").input("15000")
        click("Continue")
        app.text_input(key="input_desired").input("5")
        click("Review mandate")
        self.assertIn("Your mandate", [t.value for t in app.title])
        self.assertTrue(any("35,000.00 CHF" in t.value for t in app.markdown))
        history = app.session_state["history"]
        self.assertTrue(
            any(
                e["before"]["flows"]
                and e["before"]["flows"][0]["amount"] == "10000"
                and e["after"]["flows"][0]["amount"] == "15000"
                for e in history
            )
        )


if __name__ == "__main__":
    unittest.main()
