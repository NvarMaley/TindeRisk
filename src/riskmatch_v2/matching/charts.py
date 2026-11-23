"""Charts on the same dated portfolio measurements used by the matching desk."""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

PINK = "#ff82be"
BLUE = "#87dcff"
VIOLET = "#b59bff"
COLORS = [PINK, BLUE, VIOLET, "#9ad8b5", "#ffca91", "#e5c3ed", "#93b5cf"]


def style(fig, height=330):
    fig.update_layout(
        height=height,
        margin={"l": 10, "r": 12, "b": 15, "t": 15},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"family": "DM Sans, sans-serif", "color": "#f6edff", "size": 14},
        colorway=COLORS,
        legend={"orientation": "h", "yanchor": "top", "y": -0.20, "x": 0},
        hoverlabel={"bgcolor": "#28203b", "font_color": "#fff"},
    )
    fig.update_xaxes(gridcolor="#443750", zerolinecolor="#7e688c", automargin=True)
    fig.update_yaxes(gridcolor="#443750", zerolinecolor="#7e688c", automargin=True)
    return fig


def comparison_table(plans):
    return pd.DataFrame(
        [
            {
                "Option": name,
                "Model score / 100": p.get("score"),
                "Annual net (%)": 100 * p["net"],
                "Annual risk (%)": 100 * p["vol"],
                "Trading fees (CHF)": p["fee_chf"],
                "Eligible": bool(p["valid"]),
                "Decision": p.get("reason") or "Eligible",
            }
            for name, p in plans.items()
            if "vol" in p and "net" in p
        ]
    )


def frontier(plans, low, high):
    frame = comparison_table(plans)
    fig = go.Figure()
    if high is not None and high >= low:
        fig.add_vrect(
            x0=100 * low, x1=100 * high, fillcolor=BLUE, opacity=0.12, line_width=0
        )
        fig.add_vline(x=100 * high, line_width=1, line_dash="dash", line_color=BLUE)
    for i, row in frame.iterrows():
        benchmark = row["Option"] == "60/40 benchmark"
        shape = "diamond-open" if benchmark else "circle" if row["Eligible"] else "x"
        fig.add_scatter(
            x=[row["Annual risk (%)"]],
            y=[row["Annual net (%)"]],
            name=row["Option"],
            mode="markers",
            marker={"size": 15, "color": COLORS[i % len(COLORS)], "symbol": shape},
            hovertemplate="%{x:.2f}% annual risk<br>%{y:.2f}% annual net return<extra>%{fullData.name}</extra>",
        )
    fig.update_xaxes(title="Annual volatility (%)", rangemode="tozero")
    fig.update_yaxes(title="Estimated annual net return (%)", rangemode="tozero")
    return style(fig, 385)


def classes(plan):
    data = pd.Series(plan["classes"], dtype=float).sort_values(ascending=False)
    fig = go.Figure(
        go.Pie(
            labels=data.index,
            values=data,
            hole=0.66,
            sort=False,
            marker={"colors": COLORS},
            textinfo="percent",
            textposition="inside",
            hovertemplate="%{label}: %{percent}<extra></extra>",
        )
    )
    fig.add_annotation(
        text="CHF sleeve", x=0.5, y=0.5, showarrow=False, font={"size": 16}
    )
    return style(fig)


def concentration(plan):
    rows = {line["id"]: line["asset_class"] for line in plan["lines"]}
    result = {}
    for name, weight in plan["weights"].items():
        label = rows.get(
            name, "CHF cash" if name in {"CHF", "CHF cash"} else "Unclassified"
        )
        result[label] = result.get(label, 0.0) + weight**2
    return result


def bars(series, xlabel, percent=False):
    data = pd.Series(series, dtype=float).dropna().sort_values()
    if percent:
        data *= 100
    fig = go.Figure(
        go.Bar(
            y=data.index.tolist(),
            x=data.to_numpy(),
            orientation="h",
            marker_color=[PINK if v < 0 else BLUE for v in data],
            hovertemplate="%{y}: %{x:,.3f}<extra></extra>",
        )
    )
    fig.update_xaxes(title=xlabel)
    return style(fig, max(245, min(460, 70 + 45 * len(data))))


def heatmap(frame):
    trace = go.Heatmap(
        z=frame.values,
        x=frame.columns,
        y=frame.index,
        zmin=-1,
        zmax=1,
        colorscale=[[0, PINK], [0.5, "#302741"], [1, BLUE]],
        colorbar={"title": "ρ", "thickness": 12},
        hovertemplate="%{x} × %{y}: %{z:.2f}<extra></extra>",
    )
    return style(go.Figure(trace), 390)


def history_chart(history):
    frame = pd.DataFrame(history)
    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.12,
        row_heights=[0.59, 0.41],
    )
    for field, label, color, scale, row in [
        ("value", "Account value", BLUE, 1, 1),
        ("twr", "Flow-neutral return", PINK, 100, 2),
        ("drawdown", "Drawdown", VIOLET, 100, 2),
    ]:
        fig.add_trace(
            go.Scatter(
                x=frame.day,
                y=frame[field] * scale,
                name=label,
                mode="lines+markers",
                line={
                    "color": color,
                    "dash": "dot" if field == "drawdown" else "solid",
                },
                connectgaps=False,
            ),
            row=row,
            col=1,
        )
    fig.update_yaxes(title_text="CHF", row=1, col=1)
    fig.update_yaxes(title_text="Percent", row=2, col=1)
    fig.update_xaxes(type="date")
    return style(fig, 435)


def goal_comparison(plans):
    fig = go.Figure()
    for i, (name, p) in enumerate(plans.items()):
        if p.get("goal_value_chf") is None or not p.get("goal_range_chf"):
            continue
        low, high = p["goal_range_chf"]
        if low is None or high is None:
            continue
        fig.add_scatter(
            x=[low, high],
            y=[name, name],
            mode="lines+markers",
            name=name,
            line={"width": 5, "color": COLORS[i % len(COLORS)]},
            hovertemplate="%{y}: CHF %{x:,.0f}<extra></extra>",
        )
        fig.add_scatter(
            x=[p["goal_value_chf"]],
            y=[name],
            mode="markers",
            name=name + " central estimate",
            marker={"size": 12, "color": "white", "symbol": "diamond"},
            showlegend=False,
        )
    fig.update_layout(showlegend=False)
    fig.update_xaxes(title="Projected terminal value (CHF)")
    return style(fig, 225)
