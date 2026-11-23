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
let needsGesture = false;
let titleStarted = false;
try {
  enabled = localStorage.getItem("riskmatch-sound") !== "off";
} catch { /* Storage can be unavailable in an embedded studio. */ }

function draw() {
  button.setAttribute("aria-pressed", String(enabled));
  button.dataset.playback = !enabled ? "muted" : needsGesture ? "awaiting-interaction" : "enabled";
  button.title = enabled ? "Mute music and effects" : "Enable music and effects";
  button.innerHTML = '<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 9h4l5-4v14l-5-4H3z"/>' +
    (enabled ? '<path d="M16 8c2 2 2 6 0 8m3-11c4 4 4 10 0 14"/>' : '<path d="m16 9 5 6m0-6-5 6"/>') + '</svg>';
}
export function syncMusic() {
  if (!enabled) {
    jazz.pause();
    cues.pause();
    return;
  }
  if (!jazz.paused) return;
  jazz.play().then(() => {
    needsGesture = false;
    draw();
  }).catch(error => {
    if (error.name === "AbortError" || !enabled || !jazz.paused) return;
    needsGesture = true;
    draw();
  });
}
button.onclick = () => {
  enabled = !enabled;
  needsGesture = false;
  if (effectBus) effectBus.gain.value = enabled ? 1 : 0;
  try { localStorage.setItem("riskmatch-sound", enabled ? "on" : "off"); } catch {}
  draw();
  syncMusic();
};
// Retry within the user's normal gesture when the browser disallows audible autoplay.
function retryOnInteraction(event) {
  if (enabled && jazz.paused && event.isTrusted && !button.contains(event.target)) syncMusic();
}
for (const event of ["keydown", "pointerup", "touchend", "click"]) {
  document.addEventListener(event, retryOnInteraction, {capture: true, passive: true});
}
draw();
document.addEventListener("visibilitychange", () => { if (!document.hidden) syncMusic(); });
window.addEventListener("pageshow", syncMusic);

export function mountSoundControl(container) {
  container.append(button);
}
export function startSound(animate) {
  if (titleStarted) return;
  titleStarted = true;
  syncMusic();
  if (animate && enabled && !document.hidden) cues.play().catch(() => {});
}
export function endIntroSound() {
  cues.pause();
}

// Short original one-shots play on their own audio bus above the uninterrupted jazz.
let effectsContext;
let effectBus;
const voteClips = new Map();

function renderVote(context, like) {
  const rate = 44100;
  const clip = context.createBuffer(1, Math.ceil(rate * (like ? 0.32 : 0.13)), rate);
  const samples = clip.getChannelData(0);
  const tau = 2 * Math.PI;
  let previousNoise = 0;
  for (let i = 0; i < samples.length; i++) {
    const t = i / rate;
    if (like) {
      // Two bell strikes, E5 followed by G5, with a short sparkling overtone.
      for (const [onset, hz] of [[0, 659.25], [0.073, 783.99]]) {
        const age = t - onset;
        if (age < 0) continue;
        const phase = tau * hz * age;
        const envelope = Math.min(age / 0.005, 1) * Math.exp(-17 * age);
        samples[i] += 0.13 * envelope * (Math.sin(phase) + 0.22 * Math.sin(2.01 * phase));
      }
    } else {
      // A handclap has several closely spaced transients followed by a dry noise tail.
      const noise = 2 * Math.random() - 1;
      const snap = (noise - previousNoise) / 2;
      previousNoise = noise;
      const bursts = Math.exp(-230*t) + (t >= 0.009 ? 0.8*Math.exp(-200*(t-0.009)) : 0)
        + (t >= 0.019 ? 0.9*Math.exp(-100*(t-0.019)) : 0);
      samples[i] = 0.36 * snap * (bursts + 0.33*Math.exp(-42*t))
        + 0.13 * Math.sin(tau*190*t) * Math.exp(-60*t);
    }
    samples[i] *= Math.min(1, (samples.length - 1 - i) / (0.008 * rate));
  }
  return clip;
}

export function playSwipeSound(vote) {
  if (!enabled) return;
  const Audio = window.AudioContext || window.webkitAudioContext;
  if (!Audio) return;
  try {
    if (!effectsContext) {
      effectsContext = new Audio();
      effectBus = effectsContext.createGain();
      effectBus.connect(effectsContext.destination);
    }
    if (effectsContext.state !== "running") effectsContext.resume().catch(() => {});
    if (!voteClips.has(vote)) voteClips.set(vote, renderVote(effectsContext, vote === "yes"));
    const source = effectsContext.createBufferSource();
    source.buffer = voteClips.get(vote);
    source.connect(effectBus);
    source.onended = () => source.disconnect();
    source.start();
  } catch { /* Audio availability must never delay or reject a swipe. */ }
}
