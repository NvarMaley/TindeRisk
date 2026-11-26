const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");

const ctx = {window:{}};
vm.runInNewContext(fs.readFileSync(path.resolve(__dirname, "../../apps/web/paper-tracking.js"), "utf8"), ctx);
const {capture, update} = ctx.window.PaperTracking;
const trade = (price, as_of) => ({price, as_of});
const market = (a, b, at) => ({
  status:"ok", source:"Alpaca", feed:"iex",
  quotes:{SPY:trade(a,at), IEF:trade(b,at)},
});

test("tracking values the confirmed holdings, reports drift, and preserves the last complete valuation", () => {
  const start = new Date("2026-01-30T15:00:00Z");
  const state = capture({SPY:.6, IEF:.3, "USD cash":.1}, 1000, null, start);
  assert.equal(update(state,{status:"not_configured"},start).status,"not_configured");
  assert.equal(state.baselineAt,null);
  assert.ok(update(state,market(100,50,start.toISOString()),start).changed);
  assert.ok(Math.abs(state.quantities.SPY-6)<1e-10);
  assert.ok(Math.abs(state.quantities.IEF-6)<1e-10);
  assert.ok(Math.abs(state.quantities["USD cash"]-100)<1e-10);

  const later = new Date("2026-02-02T15:00:00Z");
  const quotes = market(110,50,later.toISOString());
  assert.ok(update(state,quotes,later).changed);
  assert.ok(Math.abs(state.latest.value-1060)<1e-10);
  assert.ok(Math.abs(state.latest.currentWeights.SPY-660/1060)<1e-10);
  assert.equal(update(state,quotes,later).changed,undefined);
  assert.equal(state.history.length,2);
  assert.equal(update(state,{status:"ok",quotes:{SPY:quotes.quotes.SPY}},later).status,"missing");
  assert.ok(Math.abs(state.latest.value-1060)<1e-10);
  assert.equal(update(state,market(100,50,start.toISOString()),later).status,"out_of_order");
  assert.equal(capture({SPY:.6,IEF:.3,"USD cash":.1},1000,state,later),state);
});

test("quarterly rebalancing waits for current quotes and records the simulated trades", () => {
  const start = new Date("2026-01-31T15:00:00Z");
  const state = capture({SPY:.6,IEF:.4},1000,null,start);
  state.policy = "quarterly";
  update(state,market(100,50,start.toISOString()),start);
  const now = new Date("2026-04-30T16:00:00Z");
  update(state,market(120,50,"2026-04-30T15:00:00Z"),now);
  assert.equal(state.journal.length,0);
  update(state,market(120,50,"2026-04-30T15:59:00Z"),now);
  assert.equal(state.latest.value,1120);
  assert.ok(Math.abs(state.latest.currentWeights.SPY-.6)<1e-10);
  assert.equal(state.journal.length,1);
  assert.equal(state.journal[0].trades.length,2);
  assert.ok(state.journal[0].trades.find(row=>row.symbol==="SPY").quantity<0);
});
