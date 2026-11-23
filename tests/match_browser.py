"""Exercise the local five-screen simulator in Chrome on desktop and emulated mobile."""

import argparse
import json
from pathlib import Path

from parcours_navigateur import question, screen
from playwright.sync_api import expect, sync_playwright

from riskmatch_v2.interview import CARDS


def journey(browser, url, phone, capture):
    size = {"width": 390, "height": 844} if phone else {"width": 1440, "height": 930}
    context = browser.new_context(
        viewport=size,
        has_touch=phone,
        is_mobile=phone,
        reduced_motion="reduce" if phone else "no-preference",
    )
    page = context.new_page()
    page.set_default_timeout(30000)
    expect.set_options(timeout=30000)
    device = "mobile" if phone else "desktop"
    captured = []

    def picture(name, anchor=None):
        if anchor and capture:
            anchor.scroll_into_view_if_needed()
        else:
            page.locator('[data-testid="stMain"]').evaluate("(e) => e.scrollTo(0, 0)")
        page.wait_for_timeout(350)
        assert page.locator('[data-testid="stMain"]').evaluate(
            "(e) => e.scrollWidth <= e.clientWidth + 1"
        )
        if capture:
            target = f"{name}-{device}.jpg"
            page.screenshot(path=capture / target, type="jpeg", quality=83)
            captured.append(target)

    def button(name):
        return page.get_by_role("button", name=name, exact=True)

    def radio(group, value):
        page.get_by_role("radiogroup", name=group, exact=False).get_by_text(
            value, exact=True
        ).click()

    page.goto(url.rstrip("/") + "/?view=research")
    question(page, "C01")
    picture("profile")
    if phone:
        page.set_viewport_size({"width": 844, "height": 390})
        question(page, "C01")
        page.set_viewport_size(size)
        question(page, "C01")
    else:
        # The same left branch is independently exercised by keyboard and touch.
        screen(page).get_by_role(
            "button", name=CARDS["C01"]["options"]["no"], exact=False
        ).click()
        question(page, "C02")
        page.reload()
        question(page, "C01")
    button("Try a fictional profile").click()
    button("Confirm this version of my answers").click()
    page.get_by_role("combobox", name="Your request").click()
    page.get_by_role("option", name="Volatility cap").click()
    cap = page.get_by_role("spinbutton", name="Annual ceiling (%)")
    cap.fill("12")
    cap.press("Enter")
    radio("In these scenarios", "yes")
    radio("Would you be comfortable keeping", "yes")
    button("Confirm my risk request").click()
    button("Compare portfolios").click()
    expect(page.get_by_text("Browse portfolios", exact=True)).to_be_visible()
    expect(page.locator('[data-testid="stPlotlyChart"]').first).to_be_visible()
    picture("compare", page.locator('[data-testid="stPlotlyChart"]').first)
    page.get_by_role("button", name="Choose this portfolio", exact=True).and_(
        page.locator(":enabled")
    ).first.click()
    button("Cancel draft").click()
    radio("Selection", "Compose an allocation")
    radio("Allocation method", "Sharpe")
    expect(button("Choose this blend")).to_be_enabled()
    radio("Allocation method", "Manual")
    val = page.get_by_role("spinbutton", name="Return (%)", exact=True)
    val.fill("60")
    val.press("Enter")
    expect(
        page.get_by_role("spinbutton", name="Diversification (%)", exact=True)
    ).to_have_value("40")
    button("Choose this blend").click()
    expect(page.get_by_text("Confirmed match", exact=True)).to_have_count(0)
    button("Confirm simulated match").click()
    expect(page.get_by_text("Confirmed match", exact=True)).to_be_visible()
    if phone:
        assert (
            page.locator(".rm13-heart").evaluate(
                "(e) => getComputedStyle(e).animationName"
            )
            == "none"
        )
    picture("match")
    button("See my portfolio").click()
    expect(page.get_by_text("Account value", exact=True).first).to_be_visible()
    page.get_by_role("button", name="Advance to simulated close", exact=False).click()
    expect(page.get_by_text("CHF simulation · 2026-11-02", exact=False)).to_be_visible()
    page.get_by_text("Record a simulated cash flow", exact=True).click()
    amount = page.get_by_role("spinbutton", name="Amount (CHF)", exact=True)
    amount.fill("1000")
    previous_value = page.locator('[data-testid="stMetricValue"]').first.inner_text()
    button("Record cash flow").click()
    expect(page.locator('[data-testid="stMetricValue"]').first).not_to_have_text(
        previous_value
    )
    page.get_by_text("Price and FX freshness", exact=True).click()
    expect(
        page.get_by_text(
            "Closing simulation · live portfolio pricing is unavailable", exact=True
        )
    ).to_be_visible()
    expect(page.get_by_text("Intraday source check · IBM", exact=False)).to_be_visible()
    freshness_seen_utc = page.evaluate("new Date().toISOString()")
    page.get_by_text("Price and FX freshness", exact=True).click()
    picture("portfolio", page.locator('[data-testid="stPlotlyChart"]').first)
    button("Request a review").click()
    expect(page.get_by_text("Oil exposure review", exact=True)).to_be_visible()
    page.get_by_text("Flag oil exposure as a concern", exact=True).click()
    expect(page.get_by_text("Client-reported risk", exact=False).first).to_be_visible()
    expect(button("Choose oil revision")).to_be_enabled()
    picture("review", page.locator('[data-testid="stPlotlyChart"]').first)
    button("Choose oil revision").click()
    button("Confirm simulated revision").click()
    expect(
        page.get_by_text("Simulated portfolio version 2 is recorded.", exact=False)
    ).to_be_visible()
    button("See my portfolio").click()
    expect(page.get_by_text("Portfolio v2 ·", exact=False)).to_be_visible()
    page.get_by_text("Demo data and access", exact=True).click()
    button("Prepare dossier export").click()
    with page.expect_download() as event:
        button("Download prepared dossier").click()
    exported = json.loads(event.value.path().read_bytes())
    assert len(exported["portfolios"]) == 2 and len(exported["trades"]) > 0
    page.get_by_text("Show my recovery key", exact=True).click()
    recovery = page.locator('[data-testid="stCode"] code').inner_text()
    page.reload()
    question(page, "C01")
    page.get_by_text("Demo data and access", exact=True).click()
    page.get_by_label("Recovery key for another saved demo").fill(recovery)
    button("Reopen saved demo").click()
    expect(page.get_by_text("Portfolio v2 ·", exact=False)).to_be_visible()
    # Delete only the fictional dossier that this test created.
    page.get_by_text("Demo data and access", exact=True).click()
    page.get_by_text(
        "Delete this fictional dossier, including all its versions and simulated trades",
        exact=True,
    ).click()
    button("Delete dossier").click()
    question(page, "C01")
    context.close()
    return {
        "viewport": size,
        "freshness_panel_observed_utc": freshness_seen_utc,
        "reduced_motion": phone,
        "matched_version": 1,
        "oil_revision_version": 2,
        "manual_return_pct": 60,
        "manual_diversification_pct": 40,
        "booked_deposit_chf": 1000,
        "exported_and_reopened_version": 2,
        "single_choice_cancelled": True,
        "sharpe_suggestion_selectable": True,
        "screenshots": captured,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8501")
    parser.add_argument("--capture", type=Path)
    parser.add_argument("--evidence-file", type=Path)
    args = parser.parse_args()
    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel="chrome", headless=True)
        evidence = {
            "browser": "Google Chrome",
            "mobile_method": "touch and viewport emulation",
        }
        for phone in (False, True):
            evidence["mobile" if phone else "desktop"] = journey(
                browser, args.url, phone, args.capture
            )
        if args.evidence_file:
            args.evidence_file.write_text(json.dumps(evidence, indent=2) + "\n")
        if args.capture:
            (args.capture / "browser.json").write_text(
                json.dumps(evidence, indent=2) + "\n"
            )
        print(
            "Five screens, 60/40 match, cancellation and confirmed oil revision passed on both viewports."
        )
