"""Verify real scrolling and audio playback through both studio entry points."""

import argparse
import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


def scroll_down(page, phone):
    if not phone:
        page.mouse.move(420, 350)
        page.mouse.wheel(0, 1800)
        return
    session = page.context.new_cdp_session(page)
    try:
        for _ in range(6):
            for i in range(11):
                session.send(
                    "Input.dispatchTouchEvent",
                    {
                        "type": "touchStart" if i == 0 else "touchMove",
                        "touchPoints": [{"x": 50, "y": 490 - 34 * i}],
                    },
                )
            session.send(
                "Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []}
            )
    finally:
        session.detach()


def exercise(browser, url, embedded, phone):
    page = browser.new_page(
        viewport={"width": 393 if phone else 1050, "height": 580},
        is_mobile=phone,
        has_touch=phone,
    )
    page.goto(url)
    view = page.frame_locator('iframe[title*="client_studio"]') if embedded else page
    start = view.get_by_role("button", name="Press to start")
    start.wait_for()
    sound = view.get_by_role("button", name="Sound", exact=True)
    jazz = view.locator("audio[loop]")
    cues = view.locator("audio:not([loop])")
    # Same-origin embeds can receive autoplay permission from the host browser.
    mode = jazz.evaluate("""async a => {
        const deadline = performance.now() + 5000;
        while (performance.now() < deadline) {
          if (!a.paused && a.currentTime > 0) return 'autoplay';
          if (document.querySelector('.sound-toggle[data-playback="awaiting-interaction"]')) return 'gesture';
          await new Promise(resolve => setTimeout(resolve, 30));
        }
        throw Error('Idle screen neither played music nor offered playback');
    }""")
    if mode == "gesture":
        assert jazz.evaluate("a=>a.paused")
        expect(sound).to_have_attribute("aria-pressed", "true")
        # Normal keyboard navigation unlocks playback without starting the title or touching Sound.
        start.press("Tab")
    assert not view.get_by_role("button", name="Play music", exact=True).count()
    if not phone:
        assert mode == "autoplay"
    expect(jazz).to_have_js_property("paused", False)
    expect(jazz).not_to_have_js_property("currentTime", 0)
    assert jazz.evaluate("a=>!a.muted && a.volume > 0")
    expect(view.locator('.rm-intro[data-phase="idle"]')).to_be_visible()
    assert cues.evaluate("a=>a.paused && a.currentTime===0")
    start.click()
    expect(jazz).to_have_js_property("paused", False)
    expect(cues).to_have_js_property("paused", False)
    expect(view.locator("#brief")).to_be_visible(timeout=15000)
    assert jazz.evaluate("a=>a.currentTime>0 && a.duration>40 && !a.paused")
    assert cues.evaluate("a=>a.currentTime>2 && a.paused")
    # Emulate a visibility event and verify the application keeps the same media clock running.
    elapsed = jazz.evaluate("""a => {
      Object.defineProperty(document, 'hidden', {configurable:true, value:true});
      document.dispatchEvent(new Event('visibilitychange'));
      return a.currentTime;
    }""")
    expect(jazz).to_have_js_property("paused", False)
    expect(jazz).not_to_have_js_property("currentTime", elapsed)
    jazz.evaluate("""() => {
      delete document.hidden;
      document.dispatchEvent(new Event('visibilitychange'));
    }""")
    sound.click()
    expect(jazz).to_have_js_property("paused", True)
    sound.click()
    expect(jazz).to_have_js_property("paused", False)
    submit = view.locator("#brief button[type=submit]")
    expect(submit).not_to_be_in_viewport()
    scroll_down(page, phone)
    expect(submit).to_be_in_viewport(ratio=1, timeout=8000)
    # Native validation on an empty form should move focus back to the first field.
    submit.click()
    expect(view.locator("#brief [name=capital]")).to_be_focused()
    sound.click()
    page.reload()
    expect(sound).to_have_attribute("aria-pressed", "false")
    start.click()
    expect(view.locator("#brief")).to_be_visible(timeout=15000)
    assert jazz.evaluate("a=>a.paused") and cues.evaluate("a=>a.paused")
    page.close()
    return {
        "entry": "Streamlit" if embedded else "Standalone",
        "input": "Touch swipe" if phone else "Mouse wheel",
        "idle_music_start": mode,
        "submit_reached": True,
        "jazz_and_cues_played": True,
        "music_before_start": True,
        "title_cues_waited_for_start": True,
        "mute_persisted": True,
        "continued_on_visibility_change": True,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--standalone", default="http://127.0.0.1:8766")
    parser.add_argument("--streamlit", default="http://127.0.0.1:8663")
    parser.add_argument("--record", action="store_true")
    args = parser.parse_args()
    with sync_playwright() as p:
        result = []
        for phone in (False, True):
            policy = (
                "document-user-activation-required"
                if phone
                else "no-user-gesture-required"
            )
            browser = p.chromium.launch(
                channel="chrome", args=["--autoplay-policy=" + policy]
            )
            for url, embedded in ((args.standalone, False), (args.streamlit, True)):
                result.append(exercise(browser, url, embedded, phone))
            browser.close()
    assert {row["idle_music_start"] for row in result} == {"autoplay", "gesture"}
    if args.record:
        (
            Path(__file__).resolve().parents[1]
            / "reports/studio/interaction-check.json"
        ).write_text(json.dumps(result, indent=2) + "\n")
    print(result)
