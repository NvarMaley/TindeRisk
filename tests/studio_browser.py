"""Exercise the client journey in desktop Chrome and mobile emulation using a disposable ledger."""

import argparse
import json
import threading
from functools import partial
from pathlib import Path
from tempfile import TemporaryDirectory
from time import monotonic

from playwright.sync_api import expect, sync_playwright

from riskmatch_v2 import studio

FACTS = {
    "capital": "50000",
    "protected": "15000",
    "loss": "15000",
    "goal": "55000",
    "due": "2030-10-30",
    "target": "5",
    "reserve_rate": "1",
}
YES = {
    "C01",
    "C02",
    "T01",
    "G00",
    "G01",
    "G03",
    "L00",
    "L01",
    "L02",
    "L03",
    "L04",
    "D01",
    "D03",
    "H01",
    "S01",
}


def create_named_save(view, name, pin="0427"):
    save = view.locator("#save-form")
    save.locator("select").select_option("new")
    save.locator('[name="name"]').fill(name)
    save.locator('[name="pin"]').fill(pin)
    save.locator('[name="confirmation"]').fill(pin)
    view.get_by_role("button", name="Create save").click()


def unlock_named_save(view, name, pin="0427"):
    save = view.locator("#save-form")
    save.locator("select").select_option(label=name)
    save.locator('[name="pin"]').fill(pin)
    view.get_by_role("button", name="Unlock save").click()


def journey(url, browser, phone, report):
    page = browser.new_page(
        viewport={"width": 393 if phone else 1380, "height": 840},
        reduced_motion="reduce" if phone else "no-preference",
        is_mobile=phone,
        has_touch=phone,
    )
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(url)
    page.get_by_role("button", name="Press to start").click()
    intro_started = monotonic()
    expect(page.locator("#save-form")).to_be_visible(timeout=15000)
    assert monotonic() - intro_started >= (5.0 if phone else 8.0)
    jazz = page.locator("audio[loop]")
    expect(jazz).to_have_js_property("volume", 0.66)
    assert jazz.evaluate("audio => audio.duration > 250 && !audio.paused")
    expect(
        page.get_by_role("button", name="RiskMatch home").locator("b")
    ).to_have_count(2)
    name = "Phone replay" if phone else "Desktop replay"
    create_named_save(page, name)
    for k, v in FACTS.items():
        if k == "target":
            page.get_by_text("Optional preferences", exact=True).click()
        page.locator(f"#brief [name={k}]").fill(v)
    assert not page.get_by_label("volatility", exact=False).count()
    page.locator("#brief button[type=submit]").click()
    card = page.locator("[data-card-id]")
    # Record the animation while its outgoing card is still present, before the route changes.
    page.evaluate("""() => {
      window.cherryVotes = [];
      window.swipeSounds = [];
      window.jazzPauses = 0;
      const jazz = document.querySelector("audio[loop]");
      jazz.addEventListener("pause",()=>window.jazzPauses++);
      const originalStart = AudioBufferSourceNode.prototype.start;
      AudioBufferSourceNode.prototype.start = function(...args) {
        const result = originalStart.apply(this,args);
        const pcm = this.buffer.getChannelData(0);
        window.swipeSounds.push({
          duration: this.buffer.duration, musicPlaying: !jazz.paused,
          energy: pcm.reduce((sum,v)=>sum+v*v,0)/pcm.length
        });
        return result;
      };
      new MutationObserver(records => {
        for (const record of records) for (const layer of record.addedNodes) {
          if (!layer.classList?.contains("swipe-cherry")) continue;
          const pad = layer.parentElement;
          const [animation] = layer.firstElementChild.getAnimations();
          const vote = {
            cycle: animation?.animationName, direction: layer.dataset.direction,
            leaving: Boolean(pad.querySelector(".fly-no, .fly-yes")),
            deck: pad.querySelector(".candidate") ? "portfolio" : "calibration",
            completed: false
          };
          window.cherryVotes.push(vote);
          if (animation) animation.finished.then(() => { vote.completed = true; });
        }
      }).observe(document.querySelector("#studio"),{childList: true, subtree: true});
    }""")
    answered = []
    swiped = []
    while not page.get_by_role("button", name="Calculate my matches").count():
        card.wait_for(timeout=10000)
        key = card.get_attribute("data-card-id")
        assert key not in answered, key
        answered.append(key)
        approve = key in YES
        explicit = {
            "G00": "yes",
            "G01": "certain",
            "G02": "gamble",
            "G03": "certain",
            "D01": "reduce",
            "V01": "wider" if phone else "lower",
            "V02": "lower",
            "V03": "wider",
        }
        if key not in explicit:
            swiped.append(key)
        if key in explicit:
            if key == "D01":
                expect(
                    page.get_by_role("button", name="Review the plan before acting")
                ).to_be_visible()
            expect(page.locator("[data-vote]")).to_have_count(0)
            page.locator(f'[data-decision="{explicit[key]}"]').click()
        elif len(answered) == 1:
            page.evaluate("""() => {
              window.mastAtSwipe = document.querySelector('.mast');
              window.mastBefore = window.mastAtSwipe.getBoundingClientRect().toJSON();
              window.horizontalSwipeShift = false;
              window.measureSwipe = true;
              function measure() {
                const studio = document.querySelector('#studio');
                const mast = document.querySelector('.mast');
                if (studio.scrollLeft || Math.abs(mast.getBoundingClientRect().left-window.mastBefore.left) > .5) {
                  window.horizontalSwipeShift = true;
                }
                if (window.measureSwipe) requestAnimationFrame(measure);
              }
              requestAnimationFrame(measure);
            }""")
            box = card.bounding_box()
            x = box["x"] + box["width"] / 2
            y = box["y"] + box["height"] / 2
            offset = 100 if approve else -100
            if phone:
                session = page.context.new_cdp_session(page)
                for step in range(7):
                    session.send(
                        "Input.dispatchTouchEvent",
                        {
                            "type": "touchStart" if step == 0 else "touchMove",
                            "touchPoints": [{"x": x + offset * step / 6, "y": y}],
                        },
                    )
                session.send(
                    "Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []}
                )
                session.detach()
            else:
                page.mouse.move(x, y)
                page.mouse.down()
                page.mouse.move(x + offset, y, steps=10)
                page.mouse.up()
        elif len(answered) == 3:
            card.press("ArrowRight" if approve else "ArrowLeft")
        else:
            page.locator('[data-vote="' + ("yes" if approve else "no") + '"]').click()
        expect(page.locator(f'[data-card-id="{key}"]')).to_have_count(0)
        if len(answered) == 1:
            assert page.evaluate("""() => {
              window.measureSwipe = false;
              const mast = document.querySelector('.mast');
              const rect = mast.getBoundingClientRect();
              return mast === window.mastAtSwipe && !window.horizontalSwipeShift &&
                Math.abs(rect.top - window.mastBefore.top) < .5;
            }""")
    expect(page.locator("#calculate")).to_be_enabled()
    profile = page.locator(".reveal h1").inner_text()
    zone_panel = page.get_by_role(
        "heading", name="Estimated annual volatility"
    ).locator("..")
    expect(zone_panel).to_be_visible()
    expect(zone_panel).to_contain_text("Derived from your portfolio choices")
    expect(zone_panel).to_contain_text("Risk aversion · γ")
    zone = zone_panel.locator(".lede").inner_text()
    assert "%" in zone and ("V03" in answered) != phone
    expect(
        page.get_by_text(
            "You would reduce the portfolio’s risk after the fall.", exact=True
        )
    ).to_be_visible()
    if report and not phone:
        page.screenshot(path=report / "profile.jpg", quality=82)
    page.locator("#library").click()
    page.get_by_role("searchbox").fill("GLD")
    page.get_by_role("button", name="Inspect GLD ·", exact=False).click()
    expect(page.locator(".lib-data-pane table").first).to_be_visible()
    if report and not phone:
        page.screenshot(path=report / "asset.jpg", quality=82)
    page.locator('[data-go="profile"]').last.click()
    page.locator("#calculate").click()
    expect(page.locator(".candidate")).to_be_visible(timeout=30000)
    expect(jazz).to_have_js_property("volume", 0.40)
    expect(
        page.get_by_text("Your estimated zone", exact=True).locator("..")
    ).to_contain_text(zone)
    page.locator("#goal-comparison > summary").click()
    expect(page.get_by_role("heading", name="What the goal would take")).to_be_visible()
    expect(page.get_by_role("heading", name="What fits your profile")).to_be_visible()
    expect(page.get_by_text("Change in 2008 stress replay")).to_be_visible()
    page.locator("#goal-comparison > summary").click()
    if report and not phone:
        page.screenshot(path=report / "contender.jpg", quality=82)
    page.locator('[data-vote="yes"]').click()
    expect(page.locator(".remove")).to_have_count(1)
    page.locator(".reel").get_by_role("button", name="Cash reserve").click()
    page.locator('[data-vote="yes"]').click()
    expect(page.locator(".remove")).to_have_count(2)
    cycles = page.evaluate("window.cherryVotes")
    assert len(cycles) == len(swiped) + 2, cycles
    assert [c["direction"] for c in cycles[: len(swiped)]] == [
        "right" if k in YES else "left" for k in swiped
    ]
    assert all(c["leaving"] and c["completed"] for c in cycles), cycles
    assert all(
        c["cycle"] == ("cherry-still" if phone else "cherry-rebound") for c in cycles
    )
    assert [c["deck"] for c in cycles[-2:]] == ["portfolio", "portfolio"]
    sounds = page.evaluate("window.swipeSounds")
    assert len(sounds) == len(cycles)
    for sound, cycle in zip(sounds, cycles, strict=True):
        expected_duration = 0.32 if cycle["direction"] == "right" else 0.13
        assert abs(sound["duration"] - expected_duration) < 0.001
        assert sound["energy"] > 0.0001 and sound["musicPlaying"]
    assert page.evaluate("window.jazzPauses") == 0
    page.locator("#compose").click()
    nums = page.locator(".mixrow input[type=number]")
    nums.nth(0).fill("60")
    nums.nth(1).fill("40")
    amounts = page.locator(".mixrow output").all_text_contents()
    assert ["".join(c for c in amount if c.isdigit()) for amount in amounts] == [
        "2100000",
        "1400000",
    ]
    page.locator("#manual").click()
    expect(page.locator("#draft")).to_be_visible(timeout=30000)
    page.get_by_text("Goal, model sensitivity & cost", exact=True).click()
    expect(page.get_by_text("Projected CHF reserve", exact=True)).to_be_visible()
    expect(
        page.get_by_text("Assumed CHF savings rate", exact=True).locator("..")
    ).to_contain_text("1.0%")
    page.locator("#auto").click()
    expect(page.locator("#auto")).to_be_enabled(timeout=30000)
    page.locator("#draft").click()
    expect(page.locator("#confirm")).to_be_visible()
    page.locator("#confirm").click()
    expect(jazz).to_have_js_property("volume", 0.40)
    page.locator("#openbook").click()
    expect(jazz).to_have_js_property("volume", 0.66)
    expect(page.locator("#live")).to_contain_text("feed")
    expect(page.locator("#chart circle")).to_have_count(1)
    page.locator("#advance").click()
    expect(page.locator("#chart circle")).to_have_count(2)
    page.get_by_text("Record a simulated cash flow", exact=True).click()
    page.locator("#flow input").fill("100")
    page.locator("#flow button").click()
    expect(page.locator("#flow input")).to_have_count(1)
    expect(page.locator("#flow input")).to_have_value("")
    page.locator("#series").select_option("twr")
    if report and not phone:
        page.screenshot(path=report / "account.jpg", quality=82)
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth+1")
    page.reload()
    page.get_by_role("button", name="Press to start").click()
    expect(page.locator("#save-form")).to_be_visible(timeout=15000)
    expect(page.locator('[data-go="tracking"]')).to_have_count(0)
    unlock_named_save(page, name)
    expect(page.locator('[data-go="tracking"]')).to_be_visible()
    assert not errors, errors
    page.close()
    return {
        "device": "phone" if phone else "desktop",
        "answered": len(answered),
        "explicit_decisions": len(answered) - len(swiped),
        "estimated_volatility_zone": zone,
        "adaptive_portfolio_card": "V03" in answered,
        "cherry_transitions": len(cycles),
        "swipe_sounds": len(sounds),
        "jazz_pauses_during_cards": 0,
        "reduced_motion": phone,
        "profile": profile,
        "manual_and_suggested_blend": True,
        "reserve_projection_and_chf_split": True,
        "confirmed": True,
        "pin_required_after_reload": True,
        "goal_comparison": True,
        "soundtrack_and_stable_swipes": True,
        "simulated_closes": 2,
        "cash_deposit_chf": 100,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--record", action="store_true")
    args = parser.parse_args()
    dest = studio.ROOT / "reports/studio" if args.record else None
    with TemporaryDirectory() as temp, sync_playwright() as p:
        studio.ACCOUNTS = Path(temp)
        server = studio.ThreadingHTTPServer(
            ("127.0.0.1", 0), partial(studio.Handler, directory=studio.WEB)
        )
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            browser = p.chromium.launch(channel="chrome")
            url = f"http://127.0.0.1:{server.server_port}"
            receipt = [journey(url, browser, device, None) for device in (False, True)]
            browser.close()
            if dest:
                (dest / "volatility-browser-check.json").write_text(
                    json.dumps(receipt, indent=2) + "\n"
                )
            print(receipt)
        finally:
            server.shutdown()


if __name__ == "__main__":
    main()
