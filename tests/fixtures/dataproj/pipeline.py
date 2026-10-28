"""A tiny data pipeline that produces pandas, numpy, matplotlib, PIL and html objects."""

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PIL import Image


class TinyModel:
    def __init__(self, w):
        self.w = w

    def _repr_html_(self):
        return f"<table class='tiny'><tr><th>w</th><td>{self.w:.3f}</td></tr></table>"


def load(n):
    rng = np.random.default_rng(0)
    df = pd.DataFrame(
        {
            "x": np.arange(n, dtype=float),
            "y": rng.normal(size=n),
            "label": [f"row {i}" for i in range(n)],
            "when": pd.date_range("2024-01-01", periods=n, freq="D"),
        }
    )
    df.loc[2, "y"] = np.nan
    return df


def features(df):
    x = df["x"].to_numpy()
    X = np.stack([x, x**2], axis=1)
    return X


def fit(X, y):
    w = float(np.nanmean(y))
    model = TinyModel(w)
    return model


def plot(df):
    fig, ax = plt.subplots(figsize=(4, 3))
    ax.plot(df["x"], df["y"].fillna(0))
    ax.set_title("y over x")
    return fig


def thumbnail(fig):
    fig.canvas.draw()
    rgba = np.asarray(fig.canvas.buffer_rgba())
    img = Image.fromarray(rgba).convert("RGB").resize((40, 30))
    return img


def main():
    df = load(30)
    X = features(df)
    model = fit(X, df["y"].to_numpy())
    fig = plot(df)
    img = thumbnail(fig)
    cube = np.arange(2 * 3 * 4, dtype=np.int32).reshape(2, 3, 4)
    print("done")
    return df, X, model, fig, img, cube


if __name__ == "__main__":
    main()
