"""Real Chromium desktop and mobile acceptance on the exported offline demo."""

import argparse, json, os, time
from pathlib import Path
from playwright.sync_api import sync_playwright, expect


def run(out, url):
    out.mkdir(exist_ok=True, parents=True)
    checks = []
    timings = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=os.environ.get("CHROME_PATH") or None
        )
        for mobile in [False, True]:
            label = "mobile" if mobile else "desktop"
            ctx = browser.new_context(
                viewport=dict(width=390 if mobile else 1200, height=850),
                is_mobile=mobile,
                has_touch=mobile,
            )
            page = ctx.new_page()
            page.set_default_timeout(15000)
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            ctx.route(
                "**/*",
                lambda route: (
                    route.continue_()
                    if route.request.url.startswith((url, "data:", "blob:"))
                    else route.abort()
                ),
            )

            def button(name):
                page.get_by_role("button", name=name, exact=True).click()
                page.wait_for_timeout(550)

            def verify(name, loc, expected):
                expect(loc).to_contain_text(expected, timeout=15000)
                checks.append(
                    dict(
                        device=label,
                        case=name,
                        expected=expected,
                        actual=loc.first.inner_text()[:220],
                        status="pass",
                    )
                )
                print(label, name, flush=True)

            def shot(name):
                page.screenshot(
                    path=str(out / (label + "-" + name + ".png")), animations="disabled"
                )

            start = time.perf_counter()
            try:
                page.goto(url)
                button("Load fictional course mandate")
                expect(
                    page.get_by_role("textbox", name="What are you saving for?")
                ).to_have_value("Fictional eight-year goal")
                for k, title in [
                    ("Continue", "Resources"),
                    ("Continue", "Protected money"),
                    ("Continue", "Expectations and preferences"),
                    ("Review mandate", "Your mandate"),
                ]:
                    button(k)
                    expect(
                        page.get_by_role("heading", name=title, exact=True)
                    ).to_be_visible()
                button("Open risk interview")
                button("Finish with my current answers")
                button("Compare fictional portfolios")
                verify(
                    "unresolved tolerance",
                    page.get_by_text("Risk interval ·"),
                    "comprehension unresolved",
                )
                verify(
                    "failed signal and unresolved comparison",
                    page.get_by_text("No signal has independent approval"),
                    "choice remains open",
                )
                expect(page.get_by_text("XLU", exact=True).first).to_be_visible()
                shot("options")
                button("Save example selection")
                page.get_by_text(
                    "Store this fictional mandate and allocation on this app host",
                    exact=True,
                ).click()
                button("Confirm and open demo account")
                verify(
                    "funded account",
                    page.get_by_text("15,000.00", exact=True),
                    "15,000.00",
                )
                button("Receive next feed update")
                page.get_by_text("Update the fictional mandate", exact=True).click()
                field = page.get_by_role("spinbutton", name="Required CHF payment")
                field.fill("35000")
                field.press("Enter")
                button("Confirm mandate revision")
                button("Compare holding and trading")
                button("Confirm simulated change")
                verify(
                    "confirmed trade",
                    page.get_by_text("Last review response"),
                    "accept",
                )
                button("Receive next feed update")
                if page.get_by_text("Last refresh 2026-11-24", exact=False).count():
                    button("Receive next feed update")
                verify(
                    "stale feed",
                    page.get_by_text("stale FX. Last reliable valuation"),
                    "proposals suspended",
                )
                expect(
                    page.get_by_role("button", name="Compare holding and trading")
                ).to_be_disabled()
                page.get_by_text(
                    "Portfolio monitor", exact=True
                ).last.scroll_into_view_if_needed()
                shot("stale")
                page.goto(url)
                button("Load fictional course mandate")
                expect(
                    page.get_by_role("textbox", name="What are you saving for?")
                ).to_have_value("Fictional eight-year goal")
                button("Continue")
                amt = page.get_by_role("textbox", name="Starting capital")
                amt.fill("10000")
                amt.press("Tab")
                button("Continue")
                expect(
                    page.get_by_role("heading", name="Protected money")
                ).to_be_visible()
                button("Continue")
                expect(
                    page.get_by_role("heading", name="Expectations and preferences")
                ).to_be_visible()
                button("Review mandate")
                verify(
                    "infeasible bill",
                    page.get_by_text(
                        "Funding shortfall: 5,000.00 CHF", exact=False
                    ).first,
                    "5,000.00 CHF",
                )
                shot("shortfall")
                timings[label] = round(time.perf_counter() - start, 2)
                if errors:
                    raise ValueError(errors)
            except Exception as exc:
                checks.append(
                    dict(
                        device=label,
                        case="journey failure",
                        status="failed",
                        actual=str(exc)[:500],
                    )
                )
                (out / "checks.json").write_text(json.dumps(checks, indent=2) + "\n")
                page.screenshot(path="/tmp/rm-browser-failure.png")
                print(page.locator("body").inner_text()[-2500:], flush=True)
                raise
            finally:
                ctx.close()
        browser.close()
    (out / "timing.json").write_text(json.dumps(timings, indent=2) + "\n")
    (out / "checks.json").write_text(json.dumps(checks, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--url", default="http://127.0.0.1:8593")
    a = parser.parse_args()
    run(a.output, a.url)
