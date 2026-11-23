/** Full-screen, keyboard-accessible title sequence. The caller owns the next screen. */
import { mountSoundControl, startSound, endIntroSound } from './sound.js';

const introSheet = new URL('./intro.css', import.meta.url).href;
const artwork = name => new URL('./assets/' + name, import.meta.url).href;

function animateLagoon(scene, photo, canvas, preference) {
  let frame = 0;
  let previous = 0;
  let width = 0;
  let height = 0;
  const ctx = canvas.getContext('2d', { alpha: false });
  if (!ctx) return () => {};

  function resize() {
    const box = canvas.getBoundingClientRect();
    const ratio = Math.min(1, 1450 / Math.max(1, box.width));
    width = canvas.width = Math.max(1, Math.round(box.width * ratio));
    height = canvas.height = Math.max(1, Math.round(box.height * ratio));
  }

  function paint(time) {
    frame = requestAnimationFrame(paint);
    if (time - previous < 80 || !photo.naturalWidth || !width) return;
    previous = time;
    const scale = Math.max(width / photo.naturalWidth, height / photo.naturalHeight);
    const px = (photo.naturalWidth - width / scale) / 2;
    const py = (photo.naturalHeight - height / scale) / 2;
    const water = Math.floor(height * .48);
    const strip = Math.max(3, Math.round(height / 100));
    for (let y = water; y < height; y += strip) {
      const depth = (y - water) / Math.max(1, height - water);
      const shift = depth * (1.4 * Math.sin(y * .031 + time * .00095) + .8 * Math.sin(y * .074 - time * .0013));
      const swell = depth * .9 * Math.sin(y * .051 + time * .0013);
      ctx.drawImage(photo, px, py + (y + swell) / scale, width / scale, strip / scale,
        -3 + shift, y, width + 6, strip);
    }
  }

  function sync() {
    cancelAnimationFrame(frame);
    canvas.hidden = preference.matches || document.hidden || !photo.naturalWidth;
    if (!canvas.hidden && scene.isConnected) {
      resize();
      paint(performance.now());
    }
  }

  const observer = new ResizeObserver(sync);
  observer.observe(scene);
  photo.addEventListener('load', sync);
  preference.addEventListener('change', sync);
  document.addEventListener('visibilitychange', sync);
  sync();
  return () => {
    cancelAnimationFrame(frame);
    observer.disconnect();
    photo.removeEventListener('load', sync);
    preference.removeEventListener('change', sync);
    document.removeEventListener('visibilitychange', sync);
  };
}

export function showIntro(root, { prepare = () => undefined, onDone } = {}) {
  if (!document.querySelector('link[data-lagoon-intro]')) {
    const css = document.createElement('link');
    css.rel = 'stylesheet';
    css.href = introSheet;
    css.dataset.lagoonIntro = '';
    document.head.append(css);
  }
  const scene = document.createElement('section');
  scene.className = 'rm-intro';
  scene.dataset.phase = 'idle';
  scene.setAttribute('aria-label', 'RiskMatch opening scene');
  scene.innerHTML = `
    <div class="rm-intro__view" aria-hidden="true">
      <picture>
        <source media="(max-aspect-ratio: 4/5)" srcset="${artwork('lagoon-dusk-mobile.webp')}">
        <img class="rm-intro__photo" fetchpriority="high" src="${artwork('lagoon-dusk.webp')}" alt="">
      </picture>
      <canvas class="rm-intro__water" hidden></canvas>
    </div>
    <div class="rm-intro__shade" aria-hidden="true"></div>
    <div class="rm-intro__rings" aria-hidden="true"><i></i><i></i><i></i></div>
    <div class="rm-intro__reflection" aria-hidden="true"><img alt="" src="${artwork('cherry.png')}"></div>
    <div class="rm-intro__waterline" aria-hidden="true">
      <div class="rm-intro__emblem">
        <div class="rm-intro__word rm-intro__risk"><b data-word="Risk">Risk</b></div>
        <img class="rm-intro__cherries" src="${artwork('cherry.png')}" alt="" draggable="false">
        <div class="rm-intro__word rm-intro__match"><b data-word="Match">Match</b></div>
      </div>
    </div>
    <button class="rm-intro__start" type="button"><span>Press to start</span></button>
    <div class="rm-intro__loading" aria-live="polite" aria-atomic="true" hidden>
      <span class="rm-intro__status"></span>
      <div class="rm-intro__track" role="progressbar" aria-label="Opening your studio"><i></i></div>
      <button class="rm-intro__retry" type="button" hidden>Retry loading</button>
    </div>`;
  root.replaceChildren(scene);
  mountSoundControl(scene);
  const select = selector => scene.querySelector(selector);
  const start = select('.rm-intro__start');
  const loading = select('.rm-intro__loading');
  const retry = select('.rm-intro__retry');
  const status = select('.rm-intro__status');
  const motion = matchMedia('(prefers-reduced-motion: reduce)');
  const stopWater = animateLagoon(scene, select('.rm-intro__photo'), select('canvas'), motion);
  let disposed = false;
  let busy = false;
  let controller;

  function dispose() {
    if (disposed) return;
    disposed = true;
    controller?.abort();
    observer.disconnect();
    stopWater();
    endIntroSound();
    document.removeEventListener('keydown', startFromKeyboard);
  }
  const observer = new MutationObserver(() => {
    if (!scene.isConnected) dispose();
  });
  observer.observe(root, { childList: true });

  async function enter() {
    if (busy || disposed) return;
    busy = true;
    const replay = scene.dataset.phase === 'error';
    startSound(!motion.matches);
    scene.dataset.phase = 'rising';
    start.disabled = true;
    retry.hidden = true;
    loading.hidden = false;
    status.textContent = 'Opening your studio';
    let timeout;
    controller = new AbortController();
    try {
      // Allow the first painted frame to reach the screen before preparing the next view.
      await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
      const prepared = Promise.resolve().then(() => prepare(controller.signal));
      const deadline = new Promise((_, reject) => {
        timeout = setTimeout(() => { controller.abort(); reject(new Error('Preparation timed out')); }, 20000);
      });
      const hold = motion.matches ? 260 : replay ? 450 : 3350;
      const [result] = await Promise.all([
        Promise.race([prepared, deadline]),
        new Promise(resolve => setTimeout(resolve, hold)),
      ]);
      if (disposed || !scene.isConnected) return;
      scene.dataset.phase = 'ready';
      await new Promise(resolve => setTimeout(resolve, motion.matches ? 40 : 420));
      if (disposed || !scene.isConnected) return;
      await onDone?.(result);
      dispose();
    } catch {
      if (disposed || !scene.isConnected) return;
      scene.dataset.phase = 'error';
      status.textContent = 'Your studio could not open.';
      retry.hidden = false;
      retry.focus({ preventScroll: true });
      busy = false;
    } finally {
      clearTimeout(timeout);
    }
  }

  function startFromKeyboard(event) {
    if (scene.dataset.phase !== 'idle' || event.repeat || event.altKey || event.metaKey || event.ctrlKey) return;
    if (event.key !== 'Enter' && event.key !== ' ') return;
    if (event.target.closest?.('.sound-toggle')) return;
    if (event.target !== document.body && event.target !== document.documentElement && !scene.contains(event.target)) return;
    event.preventDefault();
    enter();
  }
  document.addEventListener('keydown', startFromKeyboard);
  start.addEventListener('click', enter);
  retry.addEventListener('click', enter);
  // The whole scene is the start button; touch, pointer, Space and Enter share one path.
  return dispose;
}
