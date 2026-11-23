import { mountSoundControl } from "./sound.js";

export const root = document.getElementById("studio");
export const state = {
  token: "",
  version: 0,
  profile: null,
  facts: {},
  answers: {},
  cards: [],
  funded: false,
  plans: [],
  kept: [],
  index: 0,
  revision: 0,
  day: "",
  preview: null,
  draft: null,
};
export const esc = (value) =>
  String(value ?? "").replace(
    /[&<>"']/g,
    (ch) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        ch
      ],
  );
export const fmt = (v) =>
  Number.isFinite(v)
    ? new Intl.NumberFormat("en-CH", { maximumFractionDigits: 0 }).format(v)
    : "—";
export const chf = (v) =>
  Number.isFinite(v)
    ? "CHF " +
      new Intl.NumberFormat("en-CH", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      }).format(v)
    : "—";
export const pct = (v) =>
  Number.isFinite(v) ? (100 * v).toFixed(1) + "%" : "—";
export function toast(message) {
  const el = document.getElementById("notice");
  el.textContent = message;
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => (el.textContent = ""), 6500);
}
const embedded =
  window.parent !== window &&
  new URLSearchParams(location.search).has("streamlit");
const isComponent = embedded || location.pathname.includes("/component/");
let ready,
  pending = null;
const handshake = new Promise((resolve) => (ready = resolve));
const parentOrigin = document.referrer
  ? new URL(document.referrer).origin
  : location.origin;
function send(type, args = {}) {
  parent.postMessage(
    { isStreamlitMessage: true, type: "streamlit:" + type, ...args },
    parentOrigin,
  );
}
if (isComponent) {
  addEventListener("message", (e) => {
    if (
      e.source !== parent ||
      e.origin !== parentOrigin ||
      e.data?.type !== "streamlit:render"
    )
      return;
    ready();
    const reply = e.data.args?.reply;
    if (pending && reply?.id === pending.id) {
      pending.resolve(reply);
      pending = null;
    }
  });
  send("componentReady", { apiVersion: 1 });
  send("setFrameHeight", { height: window.innerHeight || 800 });
}
let queue = Promise.resolve();
async function invoke(action, payload) {
  const data = { ...payload };
  if (state.token) data.token = state.token;
  if (state.version) data.version = state.version;
  let reply;
  if (isComponent) {
    await handshake;
    const id = crypto.randomUUID();
    reply = await new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        if (pending?.id === id) pending = null;
        reject(Error("The studio timed out. Please retry."));
      }, 90000);
      pending = {
        id,
        resolve: (x) => {
          clearTimeout(timeout);
          resolve(x);
        },
      };
      send("setComponentValue", {
        dataType: "json",
        value: { id, action, data },
      });
    });
  } else {
    const response = await fetch("./api/studio", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action, data }),
    });
    if (!response.headers.get("content-type")?.includes("application/json"))
      throw Error(
        "Open the running RiskMatch studio to start your simulation.",
      );
    reply = await response.json();
  }
  if (!reply.ok)
    throw Error(reply.error || "The studio could not complete this action.");
  return reply.result;
}
export function api(action, data = {}) {
  const job = queue.then(() => invoke(action, data));
  queue = job.catch(() => {});
  return job;
}
export const nav = {};
export function shell(page, body) {
  const links = state.profile
    ? [
        ["Profile", "profile"],
        ["Library", "library"],
        ["Matches", "matches"],
        ...(state.funded ? [["Portfolio", "tracking"]] : []),
      ]
    : [];
  root.innerHTML =
    '<div class="studio-shell"><header class="mast"><button class="word" data-go="' +
    (state.profile ? "profile" : "intake") +
    '" aria-label="RiskMatch home"><img src="./assets/cherry.png" alt=""><span>Risk<i>Match</i></span></button><nav class="nav" aria-label="Studio">' +
    links
      .map(
        ([label, id]) =>
          '<button data-go="' +
          id +
          '" ' +
          (id === page ? 'aria-current="page"' : "") +
          ">" +
          label +
          "</button>",
      )
      .join("") +
    '</nav></header><section class="stage" id="stage">' +
    body +
    "</section></div>";
  mountSoundControl(root.querySelector(".nav"));
  root.scrollTop = 0;
  root.focus({ preventScroll: true });
  root
    .querySelectorAll("[data-go]")
    .forEach((b) => (b.onclick = () => run(b, () => nav[b.dataset.go]())));
}
export async function run(button, fn) {
  if (button?.disabled) return;
  if (button) {
    button.disabled = true;
    button.setAttribute("aria-busy", "true");
  }
  try {
    await fn();
  } catch (e) {
    toast(e.message || "Please retry.");
    const error = root.querySelector(".error");
    if (error) error.textContent = e.message;
  } finally {
    if (button?.isConnected) {
      button.disabled = false;
      button.removeAttribute("aria-busy");
    }
  }
}
export function bind(query, fn) {
  const el = root.querySelector(query);
  if (el) el.onclick = () => run(el, fn);
}
export function swipes(card, fn) {
  const badge = card.querySelector(".swipe-mark");
  let start = null,
    flight = false;
  const paint = (delta, alpha) => {
    card.style.setProperty("--dx", delta + "px");
    card.style.setProperty("--tilt", delta / 17 + "deg");
    card.style.setProperty("--mark", alpha);
    if (badge) {
      badge.textContent = delta < 0 ? "×" : "♥";
      badge.style.color = delta < 0 ? "#90e5ff" : "#ffa7cf";
    }
  };
  const reset = () => {
    start = null;
    card.classList.remove("drag");
    paint(0, 0);
  };
  async function choose(value) {
    if (flight) return;
    flight = true;
    paint(value === "yes" ? 100 : -100, 1);
    card.classList.add(value === "yes" ? "fly-yes" : "fly-no");
    await new Promise((r) =>
      setTimeout(
        r,
        matchMedia("(prefers-reduced-motion: reduce)").matches ? 10 : 225,
      ),
    );
    try {
      await fn(value);
    } catch (e) {
      toast(e.message);
    } finally {
      if (card.isConnected) {
        card.classList.remove("fly-yes", "fly-no");
        flight = false;
        reset();
      }
    }
  }
  card.onpointerdown = (e) => {
    if (
      flight ||
      !e.isPrimary ||
      e.button !== 0 ||
      e.target.closest("button,a,details,input")
    )
      return;
    start = { x: e.clientX, y: e.clientY };
    card.setPointerCapture(e.pointerId);
    card.classList.add("drag");
  };
  card.onpointermove = (e) => {
    if (!start) return;
    const dx = e.clientX - start.x,
      dy = e.clientY - start.y;
    if (Math.abs(dy) > Math.abs(dx) + 18) {
      reset();
      return;
    }
    paint(dx, Math.min(1, Math.abs(dx) / 75));
  };
  card.onpointercancel = reset;
  card.onpointerup = (e) => {
    if (!start) return;
    const dx = e.clientX - start.x,
      dy = e.clientY - start.y;
    reset();
    if (Math.abs(dx) > 50 && Math.abs(dx) > Math.abs(dy) * 1.25)
      choose(dx > 0 ? "yes" : "no");
  };
  card.onkeydown = (e) => {
    if (!e.repeat && ["ArrowLeft", "ArrowRight"].includes(e.key)) {
      e.preventDefault();
      choose(e.key === "ArrowRight" ? "yes" : "no");
    }
  };
  root
    .querySelectorAll("[data-vote]")
    .forEach((b) => (b.onclick = () => choose(b.dataset.vote)));
  return choose;
}
export function tiles(values) {
  return (
    '<div class="tiles">' +
    values
      .map(
        ([label, value]) =>
          '<div class="tile"><small>' +
          esc(label) +
          '</small><strong class="num">' +
          esc(value) +
          "</strong></div>",
      )
      .join("") +
    "</div>"
  );
}
export function tileBar(weights) {
  const palette = [
    "#ff8cb8",
    "#7ed5ee",
    "#dfb3fb",
    "#ffbf87",
    "#a5a9ff",
    "#bed8a1",
  ];
  let cumulative = 0;
  const stops = Object.values(weights).map((v, i) => {
    const start = cumulative;
    cumulative += Math.max(0, 100 * v);
    return palette[i % palette.length] + " " + start + "% " + cumulative + "%";
  });
  const ring = stops.length
    ? '<div class="allocation-ring" aria-hidden="true" style="background:conic-gradient(' +
      stops.join(",") +
      ')"><i></i></div>'
    : "";
  return (
    ring +
    '<div class="hbar" aria-hidden="true">' +
    Object.entries(weights)
      .map(
        ([_, v], i) =>
          '<span style="width:' +
          Math.max(0, 100 * v) +
          "%;background:" +
          palette[i % palette.length] +
          '"></span>',
      )
      .join("") +
    '</div><div class="chips">' +
    Object.entries(weights)
      .map(
        ([k, v], i) =>
          '<span class="pill"><b style="color:' +
          palette[i % palette.length] +
          '">●</b>' +
          esc(k) +
          " " +
          pct(v) +
          "</span>",
      )
      .join("") +
    "</div>"
  );
}
