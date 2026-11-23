"""Run against the local Streamlit questionnaire with Playwright and Google Chrome."""
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from time import sleep

from playwright.sync_api import expect, sync_playwright

URL = os.environ.get("RISKMATCH_TEST_URL", "http://127.0.0.1:8501")
ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads((ROOT / "reports/02-questionnaire/cas.json").read_text())
from riskmatch_v2.interview import CARDS, route


def screen(page):
    return page.frame_locator('iframe[title*="riskmatch_card"]')


def question(page, key):
    expect(screen(page).locator("h2")).to_have_text(CARDS[key]["text"], timeout=20000)


def desktop(page):
    page.goto(URL.rstrip("/") + "/?view=research")
    question(page, "C01")
    frame = screen(page)
    frame.locator("article").focus()
    page.keyboard.press("ArrowLeft")
    question(page, "C02")
    # A short drag is cancelled.
    box = frame.locator("h2").bounding_box()
    x, y = box["x"] + 60, box["y"] + 8
    page.mouse.move(x,y)
    page.mouse.down()
    page.mouse.move(x+20,y)
    page.mouse.up()
    question(page, "C02")
    page.wait_for_timeout(420)
    frame.locator("button.primary").dblclick()
    question(page,"T01")
    page.wait_for_timeout(420)
    question(page,"T01")
    case = CASES["common"] | CASES["cases"][0]["answers"] | {"C01":"no","C02":"yes"}
    answers = {"C01":"no","C02":"yes"}
    for key, card in CARDS.items():
        if key in answers or key not in route(answers):
            continue
        question(page, key)
        value = case.get(key,"skip")
        page.wait_for_timeout(400)
        if value == "skip":
            frame.get_by_role("button", name="Unsure / skip").click()
        elif card["kind"] == "binary":
            frame.get_by_role("button", name=card["options"][value]).click()
        else:
            rows = value if isinstance(value,list) else [value]
            for index,row in enumerate(rows):
                if isinstance(value,list):
                    frame.get_by_text("Add row").click()
                group = frame.locator("fieldset").nth(index)
                for spec in card["fields"]:
                    el = group.locator(f'[name="{spec["id"]}"]')
                    if spec["type"] == "select":
                        el.select_option(row[spec["id"]])
                    else:
                        el.fill(str(row[spec["id"]]))
            frame.get_by_text("Confirm", exact=True).click()
        answers[key] = value
    expect(page.get_by_text("Your summary")).to_be_visible()
    page.get_by_role("button",name="Confirm this version of my answers").click()
    expect(page.get_by_text("What annual volatility do you accept?", exact=True)).to_be_visible()
    page.get_by_role("button", name="Profile",exact=True).click()
    page.get_by_text("Questionnaire versions",exact=True).click()
    with TemporaryDirectory(dir=ROOT) as tmp:
        with page.expect_download() as event:
            page.get_by_text("Export this version to JSON").click()
        target = Path(tmp) / "v1.json"
        event.value.save_as(target)
        assert json.loads(target.read_bytes())["portrait"]["liquidity"]["investable_chf"]["low"] == 35000
    page.get_by_text("Review or correct a response",exact=True).click()
    selected = page.get_by_role("combobox", name="Card to be reviewed")
    selected.click()
    selected.fill("F03")
    selected.press("Enter")
    page.get_by_text("Fix this card",exact=True).click()
    question(page,"F03")
    frame.locator('[name=low]').fill("20000")
    frame.locator('[name=high]').fill("20000")
    frame.get_by_text("Confirm",exact=True).click()
    expect(page.get_by_text("Investable balance · CHF 30,000.00")).to_be_visible()
    page.get_by_role("button",name="Confirm this version of my answers").click()
    expect(page.get_by_text("Questionnaire version 2",exact=False)).to_be_visible()
    expect(page.get_by_text("What annual volatility do you accept?")).to_be_visible()
    page.get_by_role("combobox", name="Your request").click()
    page.get_by_role("option", name="Target range").click()
    page.get_by_text("Centre and margin", exact=True).click()
    for label, val in (("Target (%)","40"),("Margin (percentage points)","2")):
        widget = page.get_by_role("spinbutton", name=label, exact=True)
        widget.fill(val)
        widget.press("Enter")
    expect(page.get_by_text("Review your request · Target range from 38% to 42% (inclusive) · CHF investment sleeve")).to_be_visible()
    page.get_by_role("radiogroup", name="In these scenarios", exact=False).get_by_text("yes", exact=True).click()
    page.get_by_role("radiogroup", name="Would you be comfortable keeping", exact=False).get_by_text("no", exact=True).click()
    page.get_by_role("button", name="Confirm my risk request").click()
    expect(page.get_by_text("Latest recorded decision",exact=False)).to_contain_text("to be clarified")
    expect(page.get_by_text("What annual volatility do you accept?", exact=True)).to_be_visible()
    page.get_by_role("button", name="Profile",exact=True).click()
    page.get_by_text("Questionnaire versions",exact=True).click()
    with TemporaryDirectory(dir=ROOT) as tmp:
        with page.expect_download() as event:
            page.get_by_text("Export this version to JSON").click()
        target = Path(tmp) / "risque.json"
        event.value.save_as(target)
        risk = json.loads(target.read_bytes())["risk_review"]
        assert risk["choice"]["low"] == 0.38 and risk["choice"]["high"] == 0.42
        assert risk["state"] == "to be clarified" and not risk["ranking_authorized"]
    page.get_by_role("button",name="Mandate",exact=True).click()
    page.get_by_role("combobox", name="Your request").click()
    page.get_by_role("option", name="I remain undecided").click()
    page.get_by_role("button", name="Save my indecision").click()
    expect(page.get_by_text("Latest recorded decision",exact=False)).to_contain_text("pending confirmation")


def mobile(browser):
    context = browser.new_context(is_mobile=True, has_touch=True, viewport={"width":390,"height":844})
    page=context.new_page()
    page.goto(URL.rstrip("/") + "/?view=research")
    question(page,"C01")
    dev=context.new_cdp_session(page)
    def swipe(dx, cancel=False):
        box=screen(page).locator("h2").bounding_box()
        x,y=box["x"]+box["width"]/2, box["y"]+12
        dev.send("Input.dispatchTouchEvent",{"type":"touchStart","touchPoints":[{"x":x,"y":y}]})
        dev.send("Input.dispatchTouchEvent",{"type":"touchMove","touchPoints":[{"x":x+dx,"y":y}]})
        dev.send("Input.dispatchTouchEvent",{"type":"touchCancel" if cancel else "touchEnd","touchPoints":[]})
    swipe(18)
    question(page,"C01")
    swipe(75,cancel=True)
    question(page,"C01")
    swipe(-90)
    question(page,"C02")
    sleep(.45)
    swipe(90)
    question(page,"T01")
    sleep(.45)
    screen(page).get_by_role("button",name="Unsure / skip").tap()
    question(page,"G00")
    context.close()


if __name__ == "__main__":
    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel="chrome",headless=True)
        desktop(browser.new_page())
        mobile(browser)
        print("Computer path, export, correction and successful emulated tactile gestures.")
