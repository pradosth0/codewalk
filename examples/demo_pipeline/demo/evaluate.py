"""Stage 5: score a fitted model and draw its predictions against the truth."""

from __future__ import annotations

import numpy as np
from matplotlib.figure import Figure

from .train import LinearModel


def score(model: LinearModel, X: np.ndarray, y: np.ndarray) -> dict[str, float]:
    """Root mean squared error, mean absolute error and R squared on (X, y)."""
    pred = model.predict(X)
    residual = y - pred
    rmse = float(np.sqrt(np.mean(residual**2)))
    mae = float(np.mean(np.abs(residual)))
    r2 = float(1 - np.sum(residual**2) / np.sum((y - y.mean()) ** 2))
    return {"rmse": rmse, "mae": mae, "r2": r2}


def plot_predictions(y: np.ndarray, pred: np.ndarray) -> Figure:
    """Scatter of predicted against actual rentals, with the y = x line."""
    fig = Figure(figsize=(4, 4))
    ax = fig.subplots()
    ax.scatter(y, pred, s=12, alpha=0.7)
    lo, hi = min(y.min(), pred.min()), max(y.max(), pred.max())
    ax.plot([lo, hi], [lo, hi], "--", color="gray")
    ax.set_xlabel("actual rentals")
    ax.set_ylabel("predicted rentals")
    ax.set_title("Predicted vs actual")
    fig.tight_layout()
    return fig
