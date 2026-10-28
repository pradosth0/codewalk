"""Entry script of the mini project."""

import argparse

from mini.stages import Accumulator, load, score, transform


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", type=int, default=5)
    parser.add_argument("--fail", action="store_true")
    args = parser.parse_args(argv)
    data = load(args.rows)
    out, total = transform(data)
    acc = Accumulator()
    for x in out:
        acc.add(x)
        running = acc.total
    print("total", total)
    if args.fail:
        raise ValueError("boom")
    result = score(out)
    return result


if __name__ == "__main__":
    main()
