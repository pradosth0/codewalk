"""Train a small rentals model on data/raw.csv and report how well it fits.

    python run.py [--data data/raw.csv] [--epochs 200] [--lr 0.1] [--plot predictions.png]
"""

from __future__ import annotations

import argparse

from demo.clean import clean
from demo.evaluate import plot_predictions, score
from demo.features import build_features
from demo.load import load_csv
from demo.train import LinearModel


def main(argv: list[str] | None = None) -> dict[str, float]:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", default="data/raw.csv")
    parser.add_argument("--epochs", type=int, default=200)
    parser.add_argument("--lr", type=float, default=0.1)
    parser.add_argument("--plot", default=None, help="write a predicted-vs-actual PNG here")
    args = parser.parse_args(argv)

    raw = load_csv(args.data)
    df, report = clean(raw)
    X, y, names = build_features(df)
    model = LinearModel(names).fit(X, y, epochs=args.epochs, lr=args.lr)
    metrics = score(model, X, y)

    print(f"rows: {len(raw)} raw -> {len(df)} clean ({report})")
    for name, value in metrics.items():
        print(f"{name}: {value:.3f}")
    if args.plot:
        plot_predictions(y, model.predict(X)).savefig(args.plot)
    return metrics


if __name__ == "__main__":
    main()
