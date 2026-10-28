"""Stage 3: turn the cleaned frame into a numeric design matrix."""

from __future__ import annotations

import numpy as np
import pandas as pd

NUMERIC = ["temp_c", "humidity", "windspeed"]
# "clear" is the baseline, so it gets no column of its own.
WEATHER = ["cloudy", "rain"]


def build_features(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Return (X, y, names).

    X has one row per day: a bias column, the standardised numeric columns,
    one-hot weather indicators and the holiday flag. y is the rental count.
    """
    numeric = df[NUMERIC].to_numpy(dtype=float)
    scaled = (numeric - numeric.mean(axis=0)) / numeric.std(axis=0)

    weather = np.stack([(df["weather"] == w).to_numpy(dtype=float) for w in WEATHER], axis=1)
    holiday = df[["holiday"]].to_numpy(dtype=float)
    bias = np.ones((len(df), 1))

    X = np.hstack([bias, scaled, weather, holiday])
    y = df["rentals"].to_numpy(dtype=float)
    names = ["bias", *NUMERIC, *(f"weather={w}" for w in WEATHER), "holiday"]
    return X, y, names
