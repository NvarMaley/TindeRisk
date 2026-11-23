"""Render the release coverage matrix from the checked public replay."""

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

directory = Path(__file__).resolve().parent
rows = json.loads((directory / "public-replay.json").read_text())["classes"]
columns = ("screened", "eligible", "blocked", "selected_union")
matrix = np.array([[row[key] for key in columns] for row in rows.values()])
fig, ax = plt.subplots(figsize=(8.2, 3.7), layout="constrained")
colors = ax.imshow(np.log1p(matrix), cmap="BuPu", aspect="auto", vmin=0)
ax.set_xticks(range(4), ["Screened", "Eligible", "Blocked", "Held by ≥1 source"])
ax.set_yticks(range(len(rows)), rows)
ax.xaxis.tick_top()
ax.tick_params(length=0, pad=7)
for (i, j), value in np.ndenumerate(matrix):
    ax.text(
        j,
        i,
        f"{value:,}",
        ha="center",
        va="center",
        fontweight="bold",
        color="white" if colors.norm(np.log1p(value)) > 0.62 else "#22132c",
    )
for spine in ax.spines.values():
    spine.set_visible(False)
ax.set_title("From the US research inventory to portfolio holdings", loc="left", pad=32)
ax.set_xlabel(
    "30 October 2026 · counts of instruments · colour uses log(1 + count)", labelpad=12
)
fig.savefig(directory / "asset-coverage.png", dpi=160)
plt.close(fig)
