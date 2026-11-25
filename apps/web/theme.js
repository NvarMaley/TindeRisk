/* Presentation only: original V2 jazz starts on the user's opening gesture. */
(() => {
  const toggle = document.getElementById("sound-toggle");
  const introToggle = document.getElementById("intro-sound-toggle");
  const saveToggle = document.getElementById("save-sound-toggle");
  const waves = document.getElementById("sound-waves");
  const jazz = new Audio("./assets/lagoon-jazz.m4a");
  jazz.loop = true;
  jazz.preload = "none";
  jazz.volume = 0.5;

  function update() {
    const playing = !jazz.paused;
    const label = window.RM.t(playing ? "musicOff" : "musicOn");
    [toggle,introToggle,saveToggle].forEach(button=>{
      button.setAttribute("aria-pressed", String(playing));
      button.setAttribute("aria-label", label);
      button.title = label;
    });
    waves.setAttribute("d", playing ? "M16 8c2 2 2 6 0 8m3-11c4 4 4 10 0 14" : "m16 9 5 6m0-6-5 6");
  }
  [toggle,introToggle,saveToggle].forEach(button=>button.addEventListener("click", async () => {
    if (!jazz.paused) jazz.pause();
    else {
      try { await jazz.play(); }
      catch { /* Audio remains muted if the browser blocks or cannot decode it. */ }
    }
    update();
  }));
  document.addEventListener("riskmatch:intro-start",()=>{
    // Invoke play synchronously within the click/Enter gesture for browser autoplay rules.
    if(jazz.paused)jazz.play().then(update).catch(update);
    const cue=new Audio("./assets/lagoon-cues.m4a");
    cue.volume=.35;
    cue.play().catch(()=>{});
  });
  jazz.addEventListener("play", update);
  jazz.addEventListener("pause", update);
  jazz.addEventListener("error", update);
  window.addEventListener("pagehide", () => jazz.pause());
  document.addEventListener("riskmatch:language", update);
  update();
})();
