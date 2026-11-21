"""Run against a local Streamlit server with RISKMATCH_APP_URL set."""

import json
import os

import pytest

from riskmatch import intake
from riskmatch.profile_session import Interview


@pytest.mark.skipif(
    not os.getenv("RISKMATCH_APP_URL"), reason="requires a running local profile app"
)
def test_mobile_swipe_validation_and_restored_review(tmp_path):
    playwright = pytest.importorskip("playwright.sync_api")
    url = os.environ["RISKMATCH_APP_URL"]
    with playwright.sync_playwright() as manager:
        browser = manager.chromium.launch(
            executable_path=os.getenv("RISKMATCH_CHROME"), headless=True
        )
        context = browser.new_context(
            viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True
        )
        page = context.new_page()
        page.goto(url)
        page.get_by_role("button", name="Use the CHF example").click()
        goal = page.get_by_role("textbox", name="What are you saving for?")
        playwright.expect(goal).to_have_value("Home down payment")
        for title in (
            "Upcoming withdrawals",
            "Household reserve",
            "Investment preferences",
        ):
            page.get_by_role("button", name="Continue", exact=True).click()
            page.get_by_role("heading", name=title, exact=True).wait_for()
        page.get_by_text(
            "Include the four research validation cards", exact=True
        ).click()
        page.get_by_role("spinbutton", name="Pilot participant number (optional)").fill(
            "42"
        )
        page.get_by_role("button", name="Start cards").click()
        expected = Interview(intake.sample(), 42, True)
        swiped = set()
        for _ in range(120):
            stage, key = expected.current()
            if stage == "review":
                break
            card = expected.items[key]
            statement = expected.statement()
            heading = page.get_by_role("heading", name=statement["text"], exact=True)
            heading.wait_for()
            article = page.locator("article.card")
            if key.startswith("C"):
                choice = card["answers"].index(card["correct"])
            elif key == "B01":
                choice = 0  # Decline reducing exposure, then endorse keeping the allocation.
            elif key.startswith(("A", "L", "V")):
                choice = int(card.get("phi_threshold", 0) > 3)
            else:
                choice = statement["right"]
            direction = "right" if statement["right"] == choice else "left"
            if key.startswith("A") and direction not in swiped:
                heading.scroll_into_view_if_needed()
                assert page.evaluate(
                    "document.documentElement.scrollWidth <= innerWidth"
                )
                box = heading.bounding_box()
                x, y = box["x"] + box["width"] / 2, box["y"] + 8
                offset = 85 if direction == "right" else -85
                devtools = context.new_cdp_session(page)
                for kind, points in [
                    ("touchStart", [{"x": x, "y": y}]),
                    ("touchMove", [{"x": x + offset, "y": y}]),
                    ("touchEnd", []),
                ]:
                    devtools.send(
                        "Input.dispatchTouchEvent",
                        {"type": kind, "touchPoints": points},
                    )
                swiped.add(direction)
            else:
                arrow = "ArrowRight" if direction == "right" else "ArrowLeft"
                article.press(arrow)
            expected.apply(
                dict(
                    action="swipe",
                    id=key,
                    direction=direction,
                    step=expected.step,
                    seconds=0,
                )
            )
            # Some cards repeat the prompt. Wait for the previous component instance to unmount.
            page.locator(f".st-key-{key}_{len(expected.events) - 1}").wait_for(
                state="detached"
            )
        assert swiped == {"left", "right"} and expected.current() == ("review", None)
        page.get_by_role("button", name="Confirm this profile").click()
        page.get_by_text("Profile reviewed and confirmed.", exact=True).wait_for()
        with page.expect_download() as dl:
            page.get_by_role("button", name="Download profile.json").click()
        export = tmp_path / "profile.json"
        dl.value.save_as(export)
        payload = json.loads(export.read_text())
        assert payload["result"]["confirmed"]
        assert payload["result"]["answers"] == expected.answers
        assert len(payload["result"]["holdouts"]) == 4
        assert payload["result"]["capacity"]["free"] == 35000
        # A fresh browser session reads the file and recalculates the result.
        restored = context.new_page()
        restored.goto(url)
        restored.get_by_text("Resume from a profile file", exact=True).click()
        restored.locator('input[type="file"]').set_input_files(export)
        restored.get_by_role("button", name="Restore this session").click()
        restored.get_by_text("Profile reviewed and confirmed.", exact=True).wait_for()
        restored.get_by_role("button", name="Revisit this card").click()
        restored.get_by_role(
            "heading", name=expected.cards["C1"]["swipe"]["statements"][0]["text"]
        ).wait_for()
        browser.close()


@pytest.mark.skipif(
    not os.getenv("RISKMATCH_APP_URL"), reason="requires a running local profile app"
)
def test_desktop_keyboard_and_indeterminate_profile():
    playwright = pytest.importorskip("playwright.sync_api")
    with playwright.sync_playwright() as manager:
        browser = manager.chromium.launch(
            executable_path=os.getenv("RISKMATCH_CHROME"), headless=True
        )
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto(os.environ["RISKMATCH_APP_URL"])
        capital = page.get_by_role("textbox", name="Starting investment")
        capital.fill("4000–2000")
        page.get_by_role("button", name="Continue", exact=True).click()
        page.get_by_text("Check the lower and upper values for capital.").wait_for()
        capital.fill("")
        for title in (
            "Upcoming withdrawals",
            "Household reserve",
            "Investment preferences",
        ):
            page.get_by_role("button", name="Continue", exact=True).click()
            page.get_by_role("heading", name=title, exact=True).wait_for()
        page.get_by_role("button", name="Start cards").click()
        for key, direction in (("C1", "ArrowLeft"), ("C2", "ArrowRight")):
            article = page.locator("article.card")
            heading = "CHF 9,000" if key == "C1" else "CHF 11,000"
            article.filter(has_text=heading + " is the lowest balance").wait_for()
            assert article.get_by_role("button").count() == 0
            if key == "C1":
                box = article.bounding_box()
                x, y = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
                for dx in (10, -85):
                    page.mouse.move(x, y)
                    page.mouse.down()
                    page.mouse.move(x + dx, y, steps=4)
                    page.mouse.up()
                    if dx == 10:
                        assert article.filter(
                            has_text=heading + " is the lowest balance"
                        ).is_visible()
            else:
                article.press(direction)
        page.get_by_text("Undetermined", exact=True).first.wait_for()
        page.get_by_text("Too few understood choices.", exact=False).wait_for()
        page.get_by_role("button", name="Confirm this profile").click()
        page.get_by_text("Profile reviewed and confirmed.", exact=True).wait_for()
        browser.close()
