"""Exercise the dated options page and session-only choice."""

import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]


class OptionsApp(unittest.TestCase):
    def test_choice_capacity_and_unresolved_profile(self):
        at = AppTest.from_file(
            str(ROOT / "app/pages/1_Portfolio_options.py"), default_timeout=20
        ).run()
        self.assertFalse(at.exception)
        at.radio[0].set_value(0.04).run()
        at.selectbox[0].set_value("robust").run()
        at.selectbox[1].set_value("save CHF 250").run()
        self.assertEqual(len(at.metric), 3)
        at.selectbox[2].set_value("one-sided").run()
        self.assertTrue(any("unresolved" in msg.value for msg in at.info))
        at.button[0].click().run()
        self.assertEqual(at.session_state["example_option_choice"][1], 0.04)
        self.assertFalse(at.exception)


if __name__ == "__main__":
    unittest.main()
