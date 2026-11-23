const $ = id => document.getElementById(id);
const parentOrigin = document.referrer ? new URL(document.referrer).origin : location.origin;
function send(type, data = {}) {
  parent.postMessage({isStreamlitMessage: true, type: "streamlit:" + type, ...data}, parentOrigin);
}
function height() { send("setFrameHeight", {height: $("card").offsetHeight + 6}); }
new ResizeObserver(height).observe($("card"));
let current, token, locked = false, start, lastSubmit = -Infinity;
function submit(value) {
  if (locked || performance.now() - lastSubmit < 380) return;
  locked = true; lastSubmit = performance.now();
  send("setComponentValue", {dataType: "json", value: {token, value}});
}
function button(label, action, cls = "") {
  const el = document.createElement("button");
  el.type = "button"; el.textContent = label; el.className = cls; el.onclick = action;
  return el;
}
function addRow(value = {}) {
  const group = document.createElement("fieldset");
  for (const spec of current.fields) {
    const label = document.createElement("label");
    label.append(spec.label);
    const el = document.createElement(spec.type === "select" ? "select" : "input");
    el.name = spec.id; el.required = spec.type !== "optional_date";
    if (spec.type === "select") {
      el.append(new Option("Choose…", ""), ...spec.options.map(s => new Option(s, s)));
    } else if (["number","signed"].includes(spec.type)) {
      el.type = "number"; el.step = "any"; if (spec.type === "number") el.min = "0";
    } else el.type = spec.type.includes("date") ? "date" : "text";
    el.value = value[spec.id] ?? ""; label.append(el); group.append(label);
  }
  if (current.kind === "rows") group.append(button("Remove row", () => group.remove(), "remove"));
  $("fields").append(group);
}
function saveForm() {
  if (!$("fields").reportValidity()) return;
  const rows = [...$("fields").querySelectorAll("fieldset")].map(group =>
    Object.fromEntries([...group.querySelectorAll("[name]")].map(el => [el.name, el.type === "number" ? el.valueAsNumber : el.value])));
  if (rows.some(r => r.low > r.high)) { $("error").textContent = "The maximum must be at least the minimum."; return; }
  submit(current.kind === "rows" ? rows : rows[0]);
}
function render(args) {
  if (args.token === token) return;
  current = args.card; token = args.token; locked = false; start = undefined;
  $("family").textContent = current.family; $("question").textContent = current.text;
  $("error").textContent = ""; $("fields").replaceChildren(); $("actions").replaceChildren();
  const binary = current.kind === "binary";
  $("hint").textContent = binary ? "Swipe the card or use the arrow keys." :
    current.kind === "rows" ? "Add one row per item. Confirm an empty list for “none”, or skip if you are unsure." :
    "For an exact amount, enter the same value for both bounds.";
  if (binary) {
    $("actions").append(button("← " + current.options.no, () => submit("no")),
      button(current.options.yes + " →", () => submit("yes"), "primary"));
  } else {
    const value = args.previous === "skip" ? null : args.previous;
    if (current.kind === "rows") {
      for (const row of value || []) addRow(row);
      $("actions").append(button("Add row", () => addRow()));
    } else addRow(value || {});
    $("actions").append(button("Confirm", saveForm, "primary"));
  }
  $("actions").append(button("Unsure / skip", () => submit("skip")));
  if (binary) $("card").focus({preventScroll: true});
  height();
}
$("fields").onsubmit = e => { e.preventDefault(); saveForm(); };
$("card").onpointerdown = e => {
  if (current?.kind !== "binary" || !e.isPrimary || e.button !== 0 || e.target.closest("button")) return;
  start = {x:e.clientX,y:e.clientY,id:e.pointerId}; $("card").setPointerCapture(e.pointerId);
};
$("card").onpointercancel = () => {start = undefined;};
$("card").onpointerup = e => {
  if (!start || start.id !== e.pointerId) return;
  const dx=e.clientX-start.x, dy=e.clientY-start.y; start=undefined;
  if (Math.abs(dx)>=52 && Math.abs(dx)>Math.abs(dy)*1.3) submit(dx>0?"yes":"no");
};
document.addEventListener("keydown", e => {
  if (current?.kind !== "binary" || e.altKey || e.ctrlKey || e.metaKey || e.repeat) return;
  if (["ArrowLeft","ArrowRight"].includes(e.key)) {e.preventDefault();submit(e.key==="ArrowRight"?"yes":"no");}
});
window.addEventListener("message", e => {
  if (e.source===parent && e.origin===parentOrigin && e.data.type==="streamlit:render") render(e.data.args);
});
send("componentReady",{apiVersion:1});
