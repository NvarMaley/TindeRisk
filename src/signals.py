"""Construct relative Black–Litterman views from approved sector signals."""

from collections.abc import Sequence

import numpy as np
import pandas as pd


def sentiment_view_matrix(
    assets: Sequence[str], sectors: Sequence[str], decision_date,
    *, scores: pd.Series | None = None, validated: bool = False,
    usable_from=None, usable_through=None, coverage_end=None,
) -> pd.DataFrame:
    """Return at most one spread from a single dated, validated score snapshot.

    Scores must already reflect the strongest-to-weakest signal convention.
    The caller supplies the snapshot validity window and the approved source cutoff.
    """
    columns = pd.Index(assets, name="asset")
    eligible = pd.Index(sectors)
    if columns.empty or columns.hasnans or columns.has_duplicates:
        raise ValueError("Assets must be nonempty and unique")
    if eligible.has_duplicates or not eligible.isin(columns).all():
        raise ValueError("Sectors must be a unique subset of the assets")

    empty = pd.DataFrame(index=pd.Index([], name="view"), columns=columns, dtype=float)
    if validated is not True or scores is None:
        return empty

    dates = pd.DatetimeIndex([decision_date, usable_from, usable_through, coverage_end])
    if dates.hasnans or dates.tz is not None or not dates.equals(dates.normalize()):
        raise ValueError("A validated view requires normalized decision, validity dates and coverage end")
    decision, start, end, cutoff = dates
    if start > end:
        raise ValueError("View validity starts after it ends")
    if not start <= decision <= min(end, cutoff):
        return empty

    if scores.index.has_duplicates:
        raise ValueError("Sector scores require unique asset labels")
    candidates = scores.reindex(eligible).astype(float)
    candidates = candidates[np.isfinite(candidates)]
    if len(candidates) < 2:
        return empty
    strongest = candidates[candidates.eq(candidates.max())]
    weakest = candidates[candidates.eq(candidates.min())]
    if len(strongest) != 1 or len(weakest) != 1:
        return empty

    view = pd.DataFrame(0.0, index=pd.Index(["stocktwits_sector_spread"], name="view"), columns=columns)
    view.loc[:, strongest.index[0]] = 1.0
    view.loc[:, weakest.index[0]] = -1.0
    return view
