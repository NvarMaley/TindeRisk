from playwright.sync_api import sync_playwright, expect
import os

with sync_playwright() as p:
    b = p.chromium.launch(executable_path=os.getenv("CHROME_PATH"), headless=True)
    for mobile in (False, True):
        context = b.new_context(
            has_touch=mobile,
            is_mobile=mobile,
            viewport={"width": 390 if mobile else 1100, "height": 850},
        )
        page = context.new_page()
        page.goto(os.getenv("RISK_MATCH_URL", "http://127.0.0.1:8501"))

        def button(label):
            page.get_by_role("button", name=label, exact=True).click()

        for label, next_title in [
            ("Continue", "Resources"),
            ("Continue", "Protected money"),
            ("Continue", "Expectations and preferences"),
            ("Review mandate", "Your mandate"),
        ]:
            button(label)
            expect(page.get_by_role("heading", name=next_title, exact=True)).to_be_visible()
        button("Open risk interview")
        f = page.frame_locator("iframe").last
        stmt = f.locator("#statement")
        expect(stmt).to_contain_text("CHF 900", timeout=12000)
        main = f.locator("main")
        main.scroll_into_view_if_needed()
        box = stmt.bounding_box()
        x = box["x"] + 30
        y = box["y"] + 8
        if mobile:
            session = context.new_cdp_session(page)

            def drag(dx):
                for action, points in [
                    ("touchStart", [{"x": x, "y": y}]),
                    ("touchMove", [{"x": x + dx, "y": y}]),
                    ("touchEnd", []),
                ]:
                    session.send(
                        "Input.dispatchTouchEvent",
                        {"type": action, "touchPoints": points},
                    )
        else:

            def drag(dx):
                page.mouse.move(x, y)
                page.mouse.down()
                page.mouse.move(x + dx, y, steps=3)
                page.mouse.up()

        drag(15)
        expect(stmt).to_contain_text("CHF 900")
        drag(90)
        expect(stmt).to_contain_text("comfortable")
        main.focus()
        main.press("ArrowLeft")
        expect(stmt).to_contain_text("guaranteed payment")
        f.get_by_role("button", name="Unsure").click()
        expect(f.locator("#context")).to_contain_text("CHF 1,080")
        button("Finish with my current answers")
        expect(page.get_by_text("3 scenarios answered", exact=False)).to_be_visible()
        button("Resume interview")
        expect(stmt).to_be_visible()
        page.get_by_text("Review or correct a choice", exact=True).click()
        button("Answer this scenario again")
        expect(f.locator("#context")).to_contain_text("CHF 1,020")
        f.get_by_role("button", name="Yes →").evaluate("(b)=>{b.click();b.click()}")
        expect(f.locator("#context")).to_contain_text("CHF 1,080")
        button("Finish with my current answers")
        expect(page.get_by_text("3 scenarios answered", exact=False)).to_be_visible()
        print(
            "PASS",
            "touch" if mobile else "desktop",
            "short drag, right swipe, keyboard left, unsure, stop and resume",
        )
        context.close()
    b.close()
