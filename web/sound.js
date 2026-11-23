// Both recordings are original. The title cues follow the two landings at 1.36 and 1.78 s.
function track(asset, loop) {
  const audio = document.createElement("audio");
  audio.src = new URL("./assets/" + asset, import.meta.url).href;
  audio.preload = "auto";
  audio.loop = loop;
  audio.hidden = true;
  document.body.append(audio);
  return audio;
}

const jazz = track("lagoon-jazz.m4a", true);
const cues = track("lagoon-cues.m4a", false);
const button = document.createElement("button");
button.type = "button";
button.className = "sound-toggle";
button.setAttribute("aria-label", "Sound");
let enabled = true;
let started = false;
try {
  enabled = localStorage.getItem("riskmatch-sound") !== "off";
} catch { /* Storage can be unavailable in an embedded studio. */ }

function draw() {
  button.setAttribute("aria-pressed", String(enabled));
  button.title = enabled ? "Mute music and effects" : "Enable music and effects";
  button.innerHTML = '<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 9h4l5-4v14l-5-4H3z"/>' +
    (enabled ? '<path d="M16 8c2 2 2 6 0 8m3-11c4 4 4 10 0 14"/>' : '<path d="m16 9 5 6m0-6-5 6"/>') + '</svg>';
}
function syncMusic() {
  if (!started || !enabled || document.hidden) {
    jazz.pause();
    cues.pause();
    return;
  }
  jazz.play().catch(error => {
    if (error.name === "AbortError" || !enabled || document.hidden) return;
    enabled = false;
    cues.pause();
    draw();
  });
}
button.onclick = () => {
  enabled = !enabled;
  try { localStorage.setItem("riskmatch-sound", enabled ? "on" : "off"); } catch {}
  draw();
  syncMusic();
};
draw();
document.addEventListener("visibilitychange", syncMusic);
window.addEventListener("pagehide", () => { jazz.pause(); cues.pause(); });
window.addEventListener("pageshow", syncMusic);

export function mountSoundControl(container) {
  container.append(button);
}
export function startSound(animate) {
  if (started) return;
  started = true;
  syncMusic();
  if (animate && enabled && !document.hidden) cues.play().catch(() => {});
}
export function endIntroSound() {
  cues.pause();
}
