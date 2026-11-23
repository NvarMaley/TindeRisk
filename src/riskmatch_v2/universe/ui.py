"""Mixed-universe results for the Streamlit options page."""

import json

import pandas as pd
from riskmatch_v2.archive_labels import read_snapshot
import streamlit as st


def render(root):
    report = root / "reports/univers-complet"
    r = json.loads((report / "resultats.json").read_text())
    path = root / "data/local/univers" / r["snapshot"]
    st.subheader("Actions, ETF et Treasuries directs")
    st.caption(
        "Study in CHF on 30 October 2026 · investment sleeve of 35,000 CHF · reserve of 15,000 CHF"
    )
    st.dataframe(
        pd.DataFrame(r["annual"][-1]["classes"]).T.rename(
            columns={"size": "Screened", "sum": "Submitted"}
        )
    )
    st.caption(
        "WTI and rates serve as factors. GLD represents gold. Bond orders and prices are simulated."
    )
    if (report / "couverture.png").is_file():
        st.image(str(report / "couverture.png"))
    cards = r["cards"]
    lookup = {}
    model = None
    weights = None
    low = 0.0
    high = 0.12
    if (path / "models.npz").is_file():
        from riskmatch_v2.universe.desk import customize, load_model, mix

        @st.cache_resource(show_spinner=False)
        def inputs(version):
            return load_model(path)

        model, shock, prices, fx = inputs(r["snapshot"])
        inv = read_snapshot(
            path / "membership.parquet", filters=[("day", "=", r["date"])]
        )
        lookup = inv.set_index("id").symbol.to_dict()
        with st.expander("Change the band or exclude securities"):
            with st.form("mixed_request"):
                low_in = st.number_input("Lower Borne (%)", 0.0, 150.0, 0.0, 1.0)
                high_in = st.number_input("Ceiling (%)", 0.0, 150.0, 12.0, 1.0)
                exc = st.multiselect(
                    "Exclusions",
                    model[0].names,
                    format_func=lambda k: f"{lookup.get(k, k)} · {k}",
                )
                if st.form_submit_button("Recalculate options"):
                    st.session_state["mixed_req"] = (
                        low_in / 100,
                        high_in / 100,
                        tuple(exc),
                    )
        low, high, exc = st.session_state.get("mixed_req", (0.0, 0.12, ()))
        if low > high:
            st.error("The low bound exceeds the ceiling.")
            return
        if low or high != 0.12 or exc:
            from riskmatch_v2.universe.model import risk_metrics

            with st.spinner("Recalculation on all titles of the mandate..."):
                model, weights, status = customize(model, shock, low, high, exc)
            st.caption(status)
            if not weights:
                return
            cards = {}
            for n, w in weights.items():
                card = risk_metrics(model, shock, w)
                card["valid"] = model[0].evaluate(w, low, high)["valid"]
                card["top"] = [
                    {"id": k, "symbol": lookup.get(k, k), "weight": v}
                    for k, v in sorted(card["weights"].items(), key=lambda a: -a[1])[
                        :10
                    ]
                ]
                cards[n] = card
        else:
            frame = read_snapshot(
                path / "weights.parquet", filters=[("day", "=", r["date"])]
            )
            weights = {
                n: group.set_index("id")
                .weight.reindex(model[0].names, fill_value=0)
                .to_numpy()
                for n, group in frame.groupby("option")
            }
    st.dataframe(
        pd.DataFrame(
            [
                dict(
                    Option=n,
                    **{
                        "Net estimate (%)": c["net"] * 100,
                        "Volatility (%)": c["vol"] * 100,
                        "Loss of scenario (%)": c["loss"] * 100,
                        "Positions": c["n"],
                        "In the mandate": c["valid"],
                    },
                )
                for n, c in cards.items()
            ]
        ).round(2),
        hide_index=True,
    )
    st.caption(
        "Estimates are highly dependent on past averages. It does not constitute a validated forecast. The 2008 shock uses the observed return when available and a factor projection for other securities."
    )
    name = st.selectbox("See the composition", list(cards))
    top = pd.DataFrame(cards[name]["top"])
    if len(top):
        st.dataframe(top, hide_index=True)
    if "by_class" in cards[name]:
        st.bar_chart(pd.Series(cards[name]["by_class"], name="Weight (%)") * 100)
    if cards is r["cards"]:
        st.subheader("Background and adequacy")
        evidence_file = report / "replay-evidence.json"
        evidence = json.loads(evidence_file.read_text()) if evidence_file.exists() else {}
        common = r["common"]
        if evidence.get("snapshot") == r["snapshot"]:
            common = {label: {key: variants["central"][key] for key in ("end", "sessions", "cumulative")}
                      for label, variants in evidence["scenarios"].items()}
        df = pd.DataFrame(common).T
        st.dataframe(
            df.rename(
                columns={
                    "sessions": "Comparable sessions",
                    "end": "Last common date",
                    "cumulative": "Accumulated return (decimal)",
                }
            )
        )
        p = st.radio("Mandate priority", list(r["profiles"]), horizontal=True)
        score = r["profiles"][p]
        if name in score["rows"]:
            st.write(f"Replay score · {score['rows'][name]['total']:.1f}/100")
        elif name in score["excluded"]:
            st.caption("Replay score not available · " + score["excluded"][name])
        if name in r["backcast"][p]["rows"]:
            st.caption(
                f"Retrospective 12-month calculation using October weights · {r['backcast'][p]['rows'][name]['total']:.1f}/100 · holdings known at the end of the period."
            )
        with st.expander("View replay coverage limits"):
            c = r["runs"][name]["central"]
            st.write(
                {
                    "First unverified observation in original archive": c["first_problem"],
                    "Securities requiring verification": len(c["unresolved"]),
                    "Indicative cumulative costs in CHF": round(c["fees"], 2),
                }
            )
    st.subheader("Combine Options")
    if weights is None:
        label = st.selectbox("Calculated comparisons", list(r["mixes"]))
        st.json(r["mixes"][label], expanded=False)
        return
    allowed = [n for n in cards if cards[n]["valid"] and n != "60/40 benchmark"]
    selected = st.multiselect("Options to combine", allowed, default=allowed[:2])
    if not selected:
        return
    with st.form("mixed_parts"):
        mode = st.selectbox(
            "Criterion", ["Manual", "Sharpe", "Minimum risk", "Return"]
        )
        parts = [
            st.number_input(
                "Share (%) · " + n,
                min_value=0.0,
                max_value=100.0,
                value=100.0 / len(selected),
            )
            / 100
            for n in selected
        ]
        minimum = (
            st.number_input("Minimum (%) per optimisation option", 0.0, 100.0, 0.0)
            / 100
        )
        submit = st.form_submit_button("Assess the combination")
    if submit:
        try:
            c = mix(
                model,
                shock,
                prices,
                fx,
                [weights[n] for n in selected],
                parts,
                mode,
                minimum,
                low,
                high,
            )
        except ValueError as err:
            st.error(str(err))
            return
        st.write(c["status"])
        if "parts" in c:
            st.write(dict(zip(selected, map(float, c["parts"]))))
            st.write(
                f"Estimated volatility {c['vol']:.2%} · estimated return {c['net']:.2%} · {c['rounding']}"
            )
