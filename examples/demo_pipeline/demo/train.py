"""Stage 4: linear regression fitted with plain gradient descent."""

from __future__ import annotations

import numpy as np
from matplotlib.figure import Figure


class LinearModel:
    """y ~ X @ w, with w found by gradient descent on the mean squared error."""

    def __init__(self, names: list[str]) -> None:
        self.names = list(names)
        self.w = np.zeros(len(self.names))
        self.history: list[float] = []

    def fit(self, X: np.ndarray, y: np.ndarray, *, epochs: int = 200, lr: float = 0.1) -> "LinearModel":
        n = len(y)
        for epoch in range(epochs):
            pred = X @ self.w
            error = pred - y
            loss = float(np.mean(error**2))
            self.history.append(loss)
            grad = 2 * X.T @ error / n
            self.w -= lr * grad
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        return X @ self.w

    def _repr_html_(self) -> str:
        rows = "".join(f"<tr><td>{n}</td><td align='right'>{w:,.1f}</td></tr>" for n, w in zip(self.names, self.w))
        return f"<table><thead><tr><th>feature</th><th>weight</th></tr></thead><tbody>{rows}</tbody></table>"


def plot_loss(history: list[float]) -> Figure:
    """Training loss per epoch on a log scale."""
    fig = Figure(figsize=(4.5, 3))
    ax = fig.subplots()
    ax.plot(history)
    ax.set_yscale("log")
    ax.set_xlabel("epoch")
    ax.set_ylabel("mean squared error")
    ax.set_title("Training loss")
    fig.tight_layout()
    return fig
