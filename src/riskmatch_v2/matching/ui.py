"""Comparison, explicit simulated selection, close monitoring and client-led review."""

import json
import math
from pathlib import Path
from uuid import uuid4

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from . import charts
from .engine import REVIEW_POLICY, Market

ROOT = Path(__file__).resolve().parents[3]
DESCRIPTIONS = {
    "Return": "Highest estimated net return",
    "Robust": "Return across model variants",
    "Diversification": "Lower concentration",
    "Hedge": "Lower modeled stress loss",
    "60/40 benchmark": "60/40 equity–Treasury reference scaled to the risk limit",
    "CHF cash": "Minimum modeled volatility",
}


@st.cache_resource(show_spinner=False)
def market():
    return Market()


def money(value):
    return "Unavailable" if pd.isna(value) else f"CHF {value:,.2f}"


def pct(value):
    return "Unavailable" if pd.isna(value) else f"{100 * value:.2f}%"


def _caption(m, day):
    source = m.source if day == m.day else "Synthetic follow-up close"
    st.caption(
        f"Simulated CHF account · valuation {day} · risk model {m.day} · {source}"
    )


def _plot(fig, key):
    st.plotly_chart(
        fig,
        use_container_width=True,
        key="rm13_" + key,
        config={"displayModeBar": False, "scrollZoom": False, "responsive": True},
        theme=None,
    )


def _table(data):
    st.dataframe(pd.DataFrame(data), hide_index=True, width="stretch")


def _weights():
    st.caption("Answers → confirmed risk limits → eligible allocations → your choice")


def _asset_rows(p):
    frame = pd.DataFrame(p["lines"]).rename(
        columns={
            "id": "Instrument",
            "symbol": "Symbol",
            "asset_class": "Class",
            "units": "Units",
            "weight": "Weight (%)",
            "chf": "Value (CHF)",
            "risk_contribution": "Annual risk contribution (pp)",
        }
    )
    if not frame.empty:
        frame["Weight (%)"] *= 100
        frame["Annual risk contribution (pp)"] *= 100
    cash_weight = sum(p["weights"].get(k, 0.0) for k in ("CHF", "CHF cash"))
    if frame.empty or not frame["Class"].isin(["CHF cash"]).any():
        frame = pd.concat(
            [
                frame,
                pd.DataFrame(
                    [
                        {
                            "Instrument": "CHF",
                            "Symbol": "CHF",
                            "Class": "CHF cash",
                            "Units": None,
                            "Weight (%)": 100 * cash_weight,
                            "Value (CHF)": p["cash_chf"],
                            "Annual risk contribution (pp)": 0.0,
                        }
                    ]
                ),
            ],
            ignore_index=True,
        )
    return frame


def _details(label, p, key):
    option = st.selectbox(
        "Explore this composition",
        [
            "Asset weights",
            "Risk and concentration",
            "Correlations",
            "Stress scenarios",
            "Score components",
        ],
        key="rm13_metrics_" + key,
    )
    if option == "Asset weights":
        st.markdown("**Capital by asset class**")
        _plot(charts.classes(p), key + "_ring")
        st.caption(
            f"Weights sum to {sum(p['classes'].values()):.2%} of the marked investment sleeve after trading fees, including cash."
        )
        with st.expander("Asset classes and individual positions"):
            _table(
                [{"Class": k, "Weight (%)": 100 * v} for k, v in p["classes"].items()]
            )
            _table(_asset_rows(p))
    elif option == "Risk and concentration":
        _plot(
            charts.bars(
                p["euler"],
                "Contribution to annual volatility (percentage points)",
                True,
            ),
            key + "_euler",
        )
        concentrated = charts.concentration(p)
        _plot(
            charts.bars(
                concentrated,
                "Contribution to instrument concentration (sum of squared weights)",
            ),
            key + "_hhi",
        )
        st.caption(
            f"Volatility contributions sum to {sum(p['euler'].values()):.2%}. Concentration contributions sum to {sum(concentrated.values()):.4f}, including CHF cash."
        )
        _table(
            pd.DataFrame(
                {
                    "Risk contribution (pp)": pd.Series(p["euler"]) * 100,
                    "Concentration contribution": pd.Series(concentrated),
                }
            )
            .rename_axis("Class")
            .reset_index()
        )
    elif option == "Correlations":
        corr = pd.DataFrame(p["correlations"])
        if corr.empty:
            st.info("Correlation needs at least two measured risky positions.")
        else:
            st.caption(
                "Model correlations among the displayed holdings, from −1 to +1."
            )
            _plot(charts.heatmap(corr), key + "_corr")
            _table(corr.rename_axis("Instrument").reset_index().round(3))
    elif option == "Stress scenarios":
        _plot(
            charts.bars(p["scenarios"], "Conditional change in sleeve value (CHF)"),
            key + "_shock",
        )
        _table(
            [
                {"Conditional shock": k, "Change (CHF)": v}
                for k, v in p["scenarios"].items()
            ]
        )
        st.caption(
            "Market, macro, quantitative, geopolitical and sentiment inputs currently have zero recommendation weight. Scenario amounts describe a specified shock."
        )
    else:
        st.caption(
            "The model-only score uses comparable goal, stress, diversification and cost components. The historical and forecast components remain unscored."
        )
        _table([{"Component": k, "Score / 100": v} for k, v in p["subscores"].items()])
        st.write(
            f"Model-only comparison score · {p['score']:.1f}/100"
            if p.get("score") is not None
            else "Insufficient information for a model score."
        )


def _cards(plans, mandate, ledger, day):
    st.html("""<style>
[class*="st-key-rm13_tile_"] {background: linear-gradient(125deg,#31213b 0%,#20192e 60%,#202039 100%); border-top: 2px solid #d981ab !important; border-radius: 15px !important;}
.st-key-rm13_tile_1,.st-key-rm13_tile_3 {background:linear-gradient(125deg,#262b42,#1d1b32 74%);border-top-color:#83c7eb !important;}
[class*="st-key-rm13_tile_"] h3{letter-spacing:-.045em}
</style>""")
    names = list(plans)
    for start in range(0, len(names), 2):
        cols = st.columns(2)
        for col, name in zip(cols, names[start : start + 2]):
            p = plans[name]
            with col.container(border=True, key=f"rm13_tile_{names.index(name)}"):
                st.caption(DESCRIPTIONS.get(name, name))
                st.subheader(name)
                if p.get("score") is not None:
                    st.markdown(f"**{p['score']:.1f} / 100** · model-only score")
                if "net" in p:
                    st.write(
                        f"Annual net {pct(p['net'])}  ·  Annual risk {pct(p['vol'])}"
                    )
                    st.caption(f"Trading fees {money(p['fee_chf'])}")
                if name == "Robust":
                    st.caption("Near-duplicate of Return in the frozen research model.")
                if not p["valid"]:
                    st.caption(p.get("reason") or "Outside the confirmed mandate")
                if st.button(
                    "Choose this portfolio",
                    key=f"rm13_choose_{name}",
                    disabled=not p["valid"],
                    width="stretch",
                ):
                    _save_draft(ledger, day, p, "match", mandate)


def _save_draft(ledger, day, p, kind, mandate):
    try:
        if not p["valid"] or mandate.get("blocked_reason"):
            raise ValueError(
                p.get("reason")
                or mandate.get("blocked_reason")
                or "Outside the confirmed mandate."
            )
        meta = {
            k: p.get(k)
            for k in (
                "vol",
                "net",
                "cash_chf",
                "fee_chf",
                "goal_gap_chf",
                "scenarios",
                "score",
            )
        }
        meta.update(
            {
                "kind": kind,
                "model": market().model_id,
                "policy": "Hold rounded units; review drift",
                "source": market().source,
            }
        )
        ident = ledger.propose(
            day,
            p["targets"],
            p["parts"],
            metadata=meta,
            expected_revision=p["ledger_revision"],
            expected_mandate=mandate["version"],
        )
    except ValueError as exc:
        st.error(str(exc))
        return
    st.session_state.rm13_draft = ident
    st.rerun()


def _receipt(navigate):
    receipt = st.session_state.get("rm13_receipt")
    if not receipt:
        return False
    version = receipt["version"]
    fresh = st.session_state.get("rm13_celebrated") != receipt["id"]
    st.session_state.rm13_celebrated = receipt["id"]
    motion = " rm13-pop" if fresh else ""
    st.html(f"""<style>.rm13-success{{padding:1.35rem 1.5rem;border-radius:18px;background:linear-gradient(115deg,#42233f,#24263c);border:1px solid #ab648e;display:flex;gap:1rem;align-items:center;margin-bottom:1rem}}
.rm13-heart{{font-size:2.8rem;color:#ff91c0}} .rm13-pop{{animation:rm13-love .65s ease-out both}}
@keyframes rm13-love{{0%{{transform:scale(.55)}}60%{{transform:scale(1.24)}}100%{{transform:scale(1)}}}}
@media(prefers-reduced-motion:reduce){{.rm13-pop{{animation:none}}}}</style>
<div class="rm13-success" role="status"><span class="rm13-heart{motion}" aria-hidden="true">♥</span><div>
<strong>Confirmed match</strong><br>Simulated portfolio version {int(version)} is recorded.</div></div>""")
    if st.button("See my portfolio", type="primary", key="rm13_receipt_open"):
        st.session_state.pop("rm13_receipt", None)
        navigate("Portfolio")
    return True


def _pending(ledger, account, day, mandate, navigate):
    ident = st.session_state.get("rm13_draft")
    if not ident:
        return False
    try:
        proposal = ledger.proposal(ident)
    except ValueError:
        st.session_state.pop("rm13_draft", None)
        return False
    if proposal["status"] != "draft":
        st.info(
            f"This proposal is {proposal['status']}. Current positions remain visible in Portfolio."
        )
        st.session_state.pop("rm13_draft", None)
        return False
    st.subheader("Review your draft")
    st.caption(
        f"Close {proposal['day']} · mandate version {proposal['mandate']} · simulation"
    )
    _table(
        [
            {"Source option": k, "Share (%)": 100 * v}
            for k, v in proposal["parts"].items()
        ]
    )
    meta = proposal["metadata"]
    st.write(
        f"Estimated annual net {pct(meta.get('net'))} · annual risk {pct(meta.get('vol'))} · fees {money(meta.get('fee_chf'))}"
    )
    with st.expander("Inspect whole-unit changes"):
        assets = sorted(set(proposal["targets"]) | set(account["holdings"]))
        changes = [
            {
                "Instrument": s,
                "Held units": account["holdings"].get(s, 0),
                "Target units": proposal["targets"].get(s, 0),
            }
            for s in assets
            if proposal["targets"].get(s, 0) != account["holdings"].get(s, 0)
        ]
        _table(changes)
    if st.button(
        "Confirm simulated match"
        if meta["kind"] == "match"
        else "Confirm simulated revision",
        type="primary",
        key="rm13_confirm_" + ident,
        disabled=bool(mandate.get("blocked_reason")),
    ):
        try:
            version = ledger.confirm(ident, day)
        except ValueError as exc:
            st.error(str(exc))
        else:
            st.session_state.rm13_receipt = {"version": version, "id": ident}
            st.session_state.pop("rm13_draft", None)
            st.rerun()
    if st.button("Cancel draft", key="rm13_cancel_" + ident):
        ledger.cancel(ident)
        st.session_state.pop("rm13_draft", None)
        st.rerun()
    return True


def _rebalance(prefix, selected, change, source):
    """Preserve 100 whole percentage points and the relative mix of the other options."""
    state = st.session_state
    revised = int(state[f"{prefix}_{source}_{change}"])
    others = [n for n in selected if n != change]
    total = sum(state[f"{prefix}_slider_{n}"] for n in others)
    exact = [
        (100 - revised)
        * (state[f"{prefix}_slider_{n}"] / total if total else 1 / len(others))
        for n in others
    ]
    values = [math.floor(v) for v in exact]
    for i in sorted(
        range(len(others)), key=lambda i: exact[i] - values[i], reverse=True
    )[: 100 - revised - sum(values)]:
        values[i] += 1
    weights = dict(zip(others, values))
    weights[change] = revised
    for n, v in weights.items():
        for field in ["slider", "number"]:
            state[f"{prefix}_{field}_{n}"] = v


def _blend(m, ledger, account, mandate, day, plans):
    eligible = [n for n, p in plans.items() if p["valid"]]
    if len(eligible) < 2:
        st.info(
            "This mandate needs at least two eligible source options to compose a blend."
        )
        return
    selected = st.multiselect(
        "Source portfolios",
        eligible,
        default=(
            [eligible[0], "Diversification"]
            if eligible[0] != "Diversification" and "Diversification" in eligible
            else eligible[:2]
        ),
        key="rm13_sources",
    )
    if len(selected) < 2:
        return
    mode = st.radio(
        "Allocation method",
        ["Manual", "Sharpe", "Return", "Minimum risk"],
        horizontal=True,
        key="rm13_mix_mode",
    )
    if mode == "Manual":
        prefix = "rm13_mix_" + "|".join(selected)
        for i, n in enumerate(selected):
            initial = 100 // len(selected) + int(i < 100 % len(selected))
            for field in ["slider", "number"]:
                st.session_state.setdefault(f"{prefix}_{field}_{n}", initial)
            slider, number = st.columns([3, 1])
            slider.slider(
                f"{n} share (%)",
                0,
                100,
                key=f"{prefix}_slider_{n}",
                on_change=_rebalance,
                args=(prefix, selected, n, "slider"),
            )
            number.number_input(
                f"{n} (%)",
                min_value=0,
                max_value=100,
                step=1,
                key=f"{prefix}_number_{n}",
                on_change=_rebalance,
                args=(prefix, selected, n, "number"),
            )
        parts = {n: st.session_state[f"{prefix}_number_{n}"] / 100 for n in selected}
    else:
        try:
            parts = m.suggest(selected, mode, mandate, account)
        except ValueError as exc:
            st.info(str(exc))
            return
        if not parts:
            st.info("No feasible blend for this selection.")
            return
        _table(
            [
                {"Source option": n, "Suggested share (%)": 100 * p}
                for n, p in parts.items()
            ]
        )
        st.caption(
            "Suggested shares are calculated from the available options and checked again after lot rounding."
        )
    try:
        p = m.plan(parts, mandate, account)
    except ValueError as exc:
        st.info(str(exc))
        return
    st.write(
        f"Annual net {pct(p.get('net'))} · risk {pct(p.get('vol'))} · fees {money(p.get('fee_chf'))}"
    )
    if p.get("lines"):
        _details("Blended allocation", p, "blend")
    if not p["valid"]:
        st.info(p["reason"])
    if st.button(
        "Choose this blend",
        type="primary",
        key="rm13_choose_blend",
        disabled=not p["valid"],
    ):
        _save_draft(ledger, day, p, "match", mandate)


def _history_research():
    with st.expander("Observed-market replay of the source strategies"):
        prior = json.loads(
            (ROOT / "reports/univers-complet/resultats.json").read_text()
        )["monthly"]
        evidence = json.loads(
            (ROOT / "reports/univers-complet/replay-evidence.json").read_text()
        )["scenarios"]
        end = min(v["central"]["end"] for v in evidence.values())
        frame = pd.DataFrame(prior).sort_index().loc[:end].dropna()
        if frame.empty:
            return
        base = frame.div(frame.iloc[0]) * 100
        draw = (frame / frame.cummax() - 1) * 100
        measure = st.radio(
            "Historical measure",
            ["Indexed value", "Drawdown"],
            horizontal=True,
            key="rm13_obs",
        )
        selected = base if measure == "Indexed value" else draw
        fig = go.Figure()
        for name in selected:
            fig.add_scatter(
                x=selected.index, y=selected[name], name=name, mode="lines+markers"
            )
        fig.update_yaxes(
            title="Indexed value (start = 100)"
            if measure == "Indexed value"
            else "Month-end drawdown (%)"
        )
        _plot(charts.style(fig, 360), "observed")
        st.caption(
            f"Historical CHF strategy replay at common month-ends through {selected.index[-1]}. Coverage ends at the first shared data gap. Your own account starts at the simulated match."
        )
        _table(selected.rename_axis("Month-end").reset_index().round(2))


def render_compare(ledger, account, mandate, navigate):
    if _receipt(navigate):
        return
    _weights()
    if not mandate or mandate.get("blocked_reason"):
        st.info(
            (mandate or {}).get("blocked_reason")
            or "Confirm your mandate to compare options."
        )
        if st.button("Open mandate", key="rm13_cmp_mandate"):
            navigate("Mandate")
        return
    m = market()
    day = st.session_state.get("match_day", m.day)
    account = account | {"day": day}
    _caption(m, day)
    if _pending(ledger, account, day, mandate, navigate):
        return
    names = ["CHF cash"] if mandate["mode"] == "minimum" else m.names
    try:
        plans = {n: m.plan({n: 1.0}, mandate, account) for n in names}
    except ValueError as exc:
        st.info(str(exc))
        return
    mode = st.radio(
        "Selection",
        ["Browse portfolios", "Compose an allocation"],
        horizontal=True,
        key="rm13_compare_mode",
    )
    if mode == "Compose an allocation":
        _blend(m, ledger, account, mandate, day, plans)
        return
    st.caption(
        "Compare estimated net return, volatility and trading fees after whole-unit rounding."
    )
    _cards(plans, mandate, ledger, day)
    if account["portfolio_version"]:
        held = m.held(mandate, account)
        with st.expander("Compare options with the positions I hold", expanded=True):
            _table(
                [
                    {
                        "Candidate": name,
                        "Eligible": plan["valid"],
                        "Annual net change (pp)": 100 * (plan["net"] - held["net"]),
                        "Annual risk change (pp)": 100 * (plan["vol"] - held["vol"]),
                        "Trading fee (CHF)": plan["fee_chf"],
                        "Terminal goal gap change (CHF)": plan["goal_gap_chf"]
                        - held["goal_gap_chf"],
                    }
                    for name, plan in plans.items()
                ]
            )
            st.caption(
                "Differences use the same confirmed goal, dates, savings and current holdings. A negative goal-gap change narrows the projected shortfall."
            )
    with st.expander("Compare score components"):
        _table(
            [
                {"Option": name, **p["subscores"], "Model score / 100": p.get("score")}
                for name, p in plans.items()
            ]
        )
        st.caption(
            "Model-only comparison uses 75% of the original grid, renormalized across the four available components."
        )
    table = charts.comparison_table(plans)
    if table.empty:
        return
    st.subheader("Return and risk")
    _plot(
        charts.frontier(plans, mandate.get("low", 0.0) or 0.0, mandate.get("high")),
        "frontier",
    )
    st.caption(
        "The shaded interval is the confirmed volatility band. A diamond indicates the fixed benchmark. An × indicates an ineligible allocation."
    )
    _table(table.round(2))
    chosen = st.selectbox(
        "Inspect an option",
        [n for n in names if plans[n].get("weights")],
        key="rm13_inspect",
    )
    if chosen:
        _details(chosen, plans[chosen], "single")
    _history_research()


def _monitor_controls(ledger, day, m):
    i = m.days.index(day)
    next_day = m.days[i + 1] if i + 1 < len(m.days) else None
    if next_day:
        if st.button(
            f"Advance to simulated close · {next_day}", key="rm13_mark_" + day
        ):
            ledger.mark(next_day, m.quotes(next_day))
            st.session_state.match_day = next_day
            st.rerun()
    else:
        st.caption("End of the five-close simulation.")
    with st.expander("Record a simulated cash flow"):
        ident = st.session_state.setdefault("rm13_flow_id", uuid4().hex)
        with st.form("rm13_flow_" + ident):
            side = st.radio("Cash flow", ["Deposit", "Withdrawal"], horizontal=True)
            amount = st.number_input(
                "Amount (CHF)", min_value=0.01, value=500.0, step=100.0
            )
            if st.form_submit_button("Record cash flow"):
                try:
                    ledger.flow(day, amount if side == "Deposit" else -amount, ident)
                except ValueError as exc:
                    st.error(str(exc))
                else:
                    st.session_state.rm13_flow_id = uuid4().hex
                    st.rerun()


def _flows(history, mandate):
    st.markdown("**Cash-flow timeline**")
    frame = pd.DataFrame(history)
    flows = frame[frame.flow_chf.ne(0)]
    fig = go.Figure()
    if not flows.empty:
        fig.add_bar(
            x=flows.day,
            y=flows.flow_chf,
            name="Booked external flow",
            marker_color=charts.BLUE,
        )
    scheduled = []
    for flow in (mandate or {}).get("flows", []):
        if not flow.get("date") or flow.get("currency") != "CHF":
            continue
        direction = 1 if flow["direction"] == "contribution" else -1
        lower, upper = sorted((direction * flow["low"], direction * flow["high"]))
        scheduled.append(
            {
                "Date": flow["date"],
                "Type": "Planned " + flow["direction"],
                "Lower amount (CHF)": lower,
                "Upper amount (CHF)": upper,
            }
        )
    # Keep long-horizon planned household amounts distinct from simulated sleeve cash movements.
    if not flows.empty:
        fig.update_xaxes(type="category")
        fig.update_yaxes(title="Booked flow (CHF)")
        _plot(charts.style(fig, 240), "flow_timeline")
    _table(
        [
            {
                "Date": r.day,
                "Type": "Booked deposit" if r.flow_chf > 0 else "Booked withdrawal",
                "Amount (CHF)": r.flow_chf,
            }
            for r in flows.itertuples()
        ]
    )
    if scheduled:
        st.caption("Planned household flows from the mandate")
        _table(scheduled)


def render_tracking(ledger, account, mandate, navigate):
    st.session_state.pop("rm13_receipt", None)
    m = market()
    day = st.session_state.get("match_day", m.day)
    _caption(m, day)
    if not account.get("portfolio_version"):
        st.info("Choose and confirm a portfolio to start tracking it.")
        if st.button("Compare portfolios", type="primary", key="rm13_empty_compare"):
            navigate("Compare")
        return
    doc = ledger.export()
    picks = doc["portfolios"]
    current = next(p for p in picks if p["version"] == account["portfolio_version"])
    history = [v for v in ledger.history() if v["day"] <= day]
    last = history[-1]
    a, b, c = st.columns(3)
    a.metric("Account value", money(account["value"]))
    b.metric("Flow-neutral return", pct(last["twr"]))
    c.metric("Maximum drawdown", pct(min(r["drawdown"] for r in history)))
    st.caption(
        f"Portfolio v{current['version']} · matched {current['day']} · booked mandate v{current['mandate']} · settled cash {money(account['settled_cash'])}"
    )
    with st.expander("Price and FX freshness"):
        st.write("Closing simulation · live portfolio pricing is unavailable")
        marks = [account["quotes"].get(asset, {}) for asset in account["holdings"]]
        for label, key in (("Security price", "price_at"), ("USD/CHF", "fx_at")):
            times = [row.get(key) for row in marks]
            if times:
                st.caption(f"{label} · oldest held simulation mark: {min(times) if all(times) else 'missing'}")
        sample = json.loads((ROOT / "reports/14-delivery/intraday.json").read_text())["compact"]
        if "latest_bar_stamp" in sample:
            st.caption(
                f"Intraday source check · IBM historical sample stamped {sample['latest_bar_stamp']} · "
                f"received {sample['received_utc']} · age at receipt {sample['seconds_since_sample_stamp']/3600:.1f} hours. "
                "Account values use the closing simulation."
            )
    if account["stale_symbols"]:
        st.warning(
            "Stale closing marks: "
            + ", ".join(account["stale_symbols"])
            + ". Refresh affected prices and FX before confirming a change."
        )
    _plot(charts.history_chart(history), "history")
    with st.expander("Daily values, flows and drawdowns"):
        _table(
            [
                {
                    "Date": v["day"],
                    "Account value (CHF)": v["value"],
                    "External flow (CHF)": v["flow_chf"],
                    "Cash (CHF)": v["cash"],
                    "Flow-neutral return (%)": 100 * v["twr"],
                    "Drawdown (%)": 100 * v["drawdown"],
                }
                for v in history
            ]
        )
    _monitor_controls(ledger, day, m)
    with st.expander("Original blend and portfolio versions"):
        _table(
            [
                {
                    "Version": p["version"],
                    "Match date": p["day"],
                    "Mandate version": p["mandate"],
                    "Source option": n,
                    "Original share (%)": v * 100,
                }
                for p in reversed(picks)
                for n, v in p["parts"].items()
            ]
        )
        st.caption(
            "The simulator holds the rounded units. Original strategy shares are retained as the selection record while position weights drift."
        )
    st.markdown("**Current positions**")
    st.caption(
        f"Largest absolute weight change since the last match · {pct(account['drift_max'])}"
    )
    position_rows = []
    for symbol, quantity in account["holdings"].items():
        quote = account["quotes"][symbol]
        close, fxday = quote["price_at"], quote["fx_at"]
        position_rows.append(
            {
                "Instrument": symbol,
                "Units": quantity,
                "Value (CHF)": quantity * account["prices_chf"][symbol],
                "Weight (%)": 100 * account["weights"][symbol],
                "Change (pp)": 100 * account["drift_by_asset"].get(symbol, 0),
                "USD close": quote["price"],
                "CHF / USD": quote["fx"],
                "Price timestamp": close,
                "FX timestamp": fxday,
            }
        )
    position_rows.append(
        {
            "Instrument": "CHF cash",
            "Value (CHF)": account["cash"],
            "Weight (%)": 100 * account["weights"].get("CHF", 0),
            "Change (pp)": 100 * account["drift_by_asset"].get("CHF", 0),
        }
    )
    _table(position_rows)
    _flows(history, mandate)
    if mandate:
        try:
            held = m.held(mandate, account | {"day": day})
            warnings = m.triggers(
                mandate,
                account | {"day": day},
                held,
                drift=account["drift_max"],
                drawdown=last["drawdown"],
                mandate_changed=account["mandate_version"] != current["mandate"],
            )
        except ValueError as exc:
            st.info(str(exc))
        else:
            st.caption(
                f"Held model risk {pct(held['vol'])} · joint conditional change {money(held['scenarios']['Joint'])}"
            )
            if warnings:
                st.info("Review notice · " + " · ".join(warnings))
    if st.button("Request a review", type="primary", key="rm13_track_review"):
        navigate("Review")


def _review_table(plans):
    return pd.DataFrame(
        [
            {
                "Choice": name,
                "Annual net (%)": 100 * p["net"],
                "Annual risk (%)": 100 * p["vol"],
                "Trading fee (CHF)": p["fee_chf"],
                "Turnover (CHF)": p["turnover_chf"],
                "Goal gap (CHF)": p["goal_gap_chf"],
                "Oil impact magnitude (CHF)": p["oil_abs_chf"],
            }
            for name, p in plans.items()
        ]
    )


def render_review(ledger, account, mandate, navigate):
    if _receipt(navigate):
        return
    m = market()
    day = st.session_state.get("match_day", m.day)
    account = account | {"day": day}
    _caption(m, day)
    if not account["portfolio_version"]:
        st.info("Confirm a first match before requesting a revision.")
        if st.button("Compare portfolios", type="primary", key="rm13_no_review"):
            navigate("Compare")
        return
    if not mandate or mandate.get("blocked_reason"):
        st.info(
            (mandate or {}).get("blocked_reason")
            or "Resolve the mandate before requesting a revision."
        )
        if st.button("Open mandate", key="rm13_review_mandate"):
            navigate("Mandate")
        return
    if _pending(ledger, account, day, mandate, navigate):
        return
    latest = ledger.export()["portfolios"][-1]
    latest_history = ledger.history()[-1]
    try:
        held = m.held(mandate, account)
    except ValueError as exc:
        st.warning(str(exc))
        return
    action = st.radio(
        "Reason for review",
        ["Oil exposure", "Goal, savings or risk limits"],
        horizontal=True,
        key="rm13_reason",
    )
    reported = action == "Oil exposure" and st.checkbox(
        "Flag oil exposure as a concern", key="rm13_oil_concern"
    )
    notice = m.triggers(
        mandate,
        account,
        held,
        drift=account["drift_max"],
        drawdown=latest_history["drawdown"],
        reported=reported,
        mandate_changed=latest["mandate"] != account["mandate_version"],
    )
    with st.expander("Review thresholds"):
        st.caption(
            f"Policy {REVIEW_POLICY['version']} · drift of {REVIEW_POLICY['weight_drift']:.0%} from the booked weight, drawdown of {REVIEW_POLICY['drawdown']:.0%}, or a goal or scheduled withdrawal within {REVIEW_POLICY['days_to_goal']} days. A changed mandate, a breached risk limit or a client-reported concern can also open a review."
        )
    if notice:
        st.info("Review notice · " + " · ".join(notice))
    if action == "Goal, savings or risk limits":
        st.write(
            "Confirm the revised goal, date, cash flows or risk band in your mandate. New options use the current ledger positions and show the resulting trading fee."
        )
        if st.button("Review my mandate", type="primary", key="rm13_review_edit"):
            navigate("Mandate")
        if st.button("Compare revised options", key="rm13_review_recalc"):
            navigate("Compare")
        return
    st.subheader("Oil exposure review")
    st.caption(
        "Compare holding the actual units with an allocation chosen to reduce exposure to a USD 10 move in WTI."
    )
    replay = m.review(mandate, account)
    alt = replay["alternative"]
    plans = {"Keep current holdings": held}
    if alt is not None:
        plans["Proposed oil revision"] = alt
    _table(_review_table(plans).round(2))
    if alt is not None:
        st.write(
            f"Oil-impact reduction {money(replay['oil_improvement_chf'])} · after the one-way trading fee {money(replay['after_fee_improvement_chf'])}."
        )
        _table(
            [
                {"Source option": n, "Revision share (%)": 100 * v}
                for n, v in alt["parts"].items()
            ]
        )
    else:
        st.info(replay["reason"])
    shocks = pd.DataFrame({name: p["scenarios"] for name, p in plans.items()})
    fig = go.Figure()
    for name in shocks:
        fig.add_bar(x=shocks.index, y=shocks[name], name=name)
    fig.update_layout(barmode="group")
    fig.update_yaxes(title="Conditional change (CHF)")
    _plot(charts.style(fig, 365), "oil_review")
    with st.expander("Conditional shock amounts"):
        _table(shocks.rename_axis("Scenario").reset_index().round(2))
    st.markdown("**Terminal goal scenarios**")
    f = charts.goal_comparison(plans)
    if mandate.get("goal_chf"):
        f.add_vline(x=mandate["goal_chf"], line_dash="dot", line_color=charts.BLUE)
    _plot(f, "goal_range")
    st.caption(
        f"Modeled terminal value at {mandate.get('goal_date')} against a {money(mandate.get('goal_chf'))} goal. The range spans three model estimates. No event probability has been validated."
    )
    _table(
        [
            {
                "Choice": n,
                "Low scenario (CHF)": p["goal_range_chf"][0],
                "Central scenario (CHF)": p["goal_value_chf"],
                "High scenario (CHF)": p["goal_range_chf"][1],
            }
            for n, p in plans.items()
        ]
    )
    st.caption(
        "The section 12 signals contribute zero to this notice. The oil exposure uses the documented conditional scenario."
    )
    with st.expander("Signal contributions to the review"):
        r = pd.DataFrame(
            json.loads((ROOT / "reports/12-forecasts/registry.json").read_text())
        )
        evidence = (
            r[r.name.str.startswith("increment_")]
            .groupby("family")
            .agg(tested=("name", "size"), recommendation_weight=("weight", "sum"))
            .reset_index()
        )
        _table(
            evidence.rename(
                columns={
                    "family": "Family",
                    "tested": "SPY specifications",
                    "recommendation_weight": "Effective weight",
                }
            )
        )
    if alt is not None and st.button(
        "Choose oil revision", type="primary", key="rm13_choose_oil"
    ):
        _save_draft(ledger, day, alt, "revision", mandate)
    if held["valid"]:
        if st.button("Keep current holdings", key="rm13_keep"):
            navigate("Portfolio")
    else:
        st.warning(
            "Current composition is outside the latest mandate. It remains on the ledger until an eligible revision is confirmed."
        )
