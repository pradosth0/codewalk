"""Stages of the mini pipeline used by the tests."""

import math


def load(n):
    """Make n floats."""
    data = [i * 1.5 for i in range(n)]
    print(f"loaded {len(data)} rows")
    return data


def transform(data):
    out = []
    for x in data:
        y = math.sqrt(x)
        out.append(y)
    total = sum(out)
    return out, total


class Accumulator:
    def __init__(self):
        self.total = 0.0
        self.count = 0

    def add(self, x):
        self.total += x
        self.count += 1
        return self.total


def score(out):
    mean = sum(out) / len(out)
    return {"mean": mean, "n": len(out)}


def demo():
    out, total = transform(load(3))
    return score(out)
