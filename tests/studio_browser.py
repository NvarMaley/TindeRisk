"""Exercise the client journey in desktop Chrome and mobile emulation using a disposable ledger."""

import argparse
import json
import threading
from functools import partial
from pathlib import Path
from tempfile import TemporaryDirectory

from playwright.sync_api import expect, sync_playwright

from riskmatch_v2 import studio

FACTS = {
    "capital": "50000",
    "protected": "15000",
    "loss": "15000",
    "goal": "55000",
    "due": "2030-10-30",
    "target": "5",
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
    for k, v in FACTS.items():
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
    while not page.get_by_role("button", name="Calculate my matches").count():
        card.wait_for(timeout=10000)
        key = card.get_attribute("data-card-id")
        assert key not in answered, key
        answered.append(key)
        approve = key in YES
        if len(answered) == 1:
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
    expect(page.locator("#calculate")).to_be_enabled()
    profile = page.locator(".reveal h1").inner_text()
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
    if report and not phone:
        page.screenshot(path=report / "contender.jpg", quality=82)
    page.locator('[data-vote="yes"]').click()
    expect(page.locator(".remove")).to_have_count(1)
    page.locator('[data-vote="yes"]').click()
    expect(page.locator(".remove")).to_have_count(2)
    cycles = page.evaluate("window.cherryVotes")
    assert len(cycles) == len(answered) + 2, cycles
    assert [c["direction"] for c in cycles[: len(answered)]] == [
        "right" if k in YES else "left" for k in answered
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
    page.locator("#manual").click()
    expect(page.locator("#draft")).to_be_visible(timeout=30000)
    page.locator("#auto").click()
    expect(page.locator("#auto")).to_be_enabled(timeout=30000)
    page.locator("#draft").click()
    expect(page.locator("#confirm")).to_be_visible()
    page.locator("#confirm").click()
    page.locator("#openbook").click()
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
    expect(page.locator('[data-go="tracking"]')).to_be_visible()
    assert not errors, errors
    page.close()
    return {
        "device": "phone" if phone else "desktop",
        "answered": len(answered),
        "cherry_transitions": len(cycles),
        "swipe_sounds": len(sounds),
        "jazz_pauses_during_cards": 0,
        "reduced_motion": phone,
        "profile": profile,
        "manual_and_suggested_blend": True,
        "confirmed": True,
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
            receipt = [journey(url, browser, device, dest) for device in (False, True)]
            browser.close()
            if dest:
                (dest / "browser-check.json").write_text(
                    json.dumps(receipt, indent=2) + "\n"
                )
            print(receipt)
        finally:
            server.shutdown()


if __name__ == "__main__":
    main()
