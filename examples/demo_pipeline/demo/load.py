"""Stage 1: read the raw CSV export."""

from __future__ import annotations

import pandas as pd


def load_csv(path: str) -> pd.DataFrame:
    """Read `path`, parse the date column and order the rows by date.

    The export is not sorted and the date comes in as text, so this is the only
    place that knows about the file format; everything downstream sees a frame.
    """
    df = pd.read_csv(path)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)
    return df
