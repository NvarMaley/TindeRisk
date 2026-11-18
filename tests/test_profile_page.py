from streamlit.testing.v1 import AppTest

from src.paths import ROOT


def test_profile_form_shows_a_capped_category_and_blocks_unresolved_reference():
    page = next((ROOT / "app/pages").glob("1_*_Profile.py"))
    app = AppTest.from_file(str(page)).run(timeout=30)
    assert not app.exception
    assert any("academic prototype" in notice.value for notice in app.info)
    choices = {
        "F01": "2_to_lt_5y", "F02": "none", "F03": "ge_6m", "F04": "no_payment",
        "F05": "increase_risk", "F06": "ge_20pct", "F07": "larger_swings",
        "F09": "can_decline", "F10": "gain_25", "F11": "growth",
        "F13": "disallow", "F14": "standard",
    }
    for key, value in choices.items():
        app.radio(key=key).set_value(value)
    app.multiselect(key="F08").set_value(["funds"])
    app.multiselect(key="F12").set_value(["none"])
    app.button[0].click().run()
    assert not app.exception
    assert any("Balanced" in heading.value for heading in app.subheader)
    assert app.session_state["risk_band"] == "balanced"
    assert app.session_state["profile"]["risk"]["effective_volatility"] == .08
    assert any("risk aversion" in metric.label.lower() for metric in app.expander[0].metric)

    app.radio(key="F13").set_value("unsure")
    app.button[0].click().run()
    assert not app.exception
    assert app.session_state["risk_band"] is None
    assert any("Clarify" in warning.value for warning in app.warning)
