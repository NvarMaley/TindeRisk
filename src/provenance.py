"""Observation-level provenance, kept separate from numerical model inputs."""

import hashlib
from pathlib import Path

import pandas as pd


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def observation_records(
    series: pd.Series,
    *,
    available_dates,
    source: str,
    downloaded_at_utc: str | None,
    availability_rule: str,
) -> pd.DataFrame:
    """Preserve observation/availability dates without fabricating retrievals.

    ``available_date`` is a documented modelling convention, not a claim that
    latest-vintage values were historically known on that date.
    """
    observations = pd.DatetimeIndex(series.index)
    availability = pd.DatetimeIndex(available_dates)
    if len(observations) != len(availability):
        raise ValueError("one availability date is required per observation")
    if observations.hasnans or availability.hasnans or (availability < observations).any():
        raise ValueError("availability must not precede observation dates")
    downloaded = pd.to_datetime(downloaded_at_utc, utc=True) if downloaded_at_utc else pd.NaT
    return pd.DataFrame({
        "series": str(series.name),
        "observation_date": observations,
        "available_date": availability,
        "value": series.to_numpy(),
        "source": source,
        "downloaded_at_utc": downloaded,
        "download_status": "recorded" if downloaded_at_utc else "unknown_original_download",
        "availability_rule": availability_rule,
        "availability_is_assumed": True,
    })
