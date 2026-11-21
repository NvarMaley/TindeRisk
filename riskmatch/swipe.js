export default function ({ parentElement, data, setTriggerValue }) {
  const card = parentElement.querySelector(".card");
  const stamp = card.querySelector(".stamp");
  const pass = parentElement.querySelector(".skip");
  card.querySelector(".family").textContent = data.family;
  card.querySelector(".scenario").textContent = data.context;
  card.querySelector("h2").textContent = data.text;
  pass.textContent = data.passLabel;
  let start, locked = false;
  function reset() {
    start = null;
    card.classList.remove("dragging");
    card.style.transform = "";
    stamp.style.opacity = 0;
  }
  function feedback(dx) {
    stamp.textContent = dx > 0 ? "YES" : "NO";
    stamp.classList.toggle("positive", dx > 0);
    stamp.style.opacity = Math.min(Math.abs(dx) / 65, 1);
  }
  function submit(direction) {
    if (locked) return;
    locked = true;
    start = null;
    card.classList.remove("dragging");
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (direction !== "pass" && !reduced) {
      const sign = direction === "right" ? 1 : -1;
      feedback(100 * sign);
      card.style.transform = 'translateX(' + sign * 120 + '%) rotate(' + sign * 12 + 'deg)';
      card.style.opacity = 0;
    }
    setTimeout(() => setTriggerValue("picked", {id: data.id, nonce: data.nonce, direction}),
      direction === "pass" || reduced ? 0 : 150);
  }
  card.onpointerdown = e => {
    if (locked || !e.isPrimary || e.button !== 0) return;
    start = { id: e.pointerId, x: e.clientX, y: e.clientY };
    card.setPointerCapture(e.pointerId);
    card.classList.add("dragging");
  };
  card.onpointermove = e => {
    if (start?.id !== e.pointerId) return;
    const dx = e.clientX - start.x, dy = e.clientY - start.y;
    if (Math.abs(dy) > 14 && Math.abs(dy) > Math.abs(dx)) { reset(); return; }
    card.style.transform = 'translateX(' + dx + 'px) rotate(' + Math.max(-12, Math.min(12, dx / 14)) + 'deg)';
    feedback(dx);
  };
  card.onpointerup = e => {
    if (start?.id !== e.pointerId) return;
    const dx = e.clientX - start.x, dy = e.clientY - start.y;
    if (Math.abs(dx) >= 55 && Math.abs(dx) > Math.abs(dy) * 1.4) {
      submit(dx > 0 ? "right" : "left");
    } else reset();
  };
  card.onpointercancel = reset;
  card.onkeydown = e => {
    if (e.repeat || !["ArrowLeft", "ArrowRight"].includes(e.key)) return;
    e.preventDefault();
    submit(e.key === "ArrowRight" ? "right" : "left");
  };
  parentElement.querySelector(".no").onclick = () => submit("left");
  parentElement.querySelector(".yes").onclick = () => submit("right");
  pass.onclick = () => submit("pass");
  card.focus({preventScroll: true});
}
