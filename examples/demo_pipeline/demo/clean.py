"""Stage 2: make the raw frame fit for modelling."""

from __future__ import annotations

import pandas as pd

# No day ever had this many rentals: larger values are counter glitches.
MAX_RENTALS = 10_000

# Sensor columns that sometimes come back empty.
SENSORS = ("temp_c", "humidity")


def clean(raw: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    """Return a cleaned copy of `raw` and a report of what was changed."""
    report: dict[str, int] = {}

    df = raw.drop_duplicates()
    report["duplicates"] = len(raw) - len(df)

    outliers = df["rentals"] > MAX_RENTALS
    report["outliers"] = int(outliers.sum())
    df = df[~outliers].copy()

    for column in SENSORS:
        missing = df[column].isna()
        report[f"missing_{column}"] = int(missing.sum())
        df[column] = df[column].fillna(df[column].median())

    return df.reset_index(drop=True), report
