"""Child-process entry point used by `codewalk record`: load, analyze, record, write steps.json."""

from __future__ import annotations

import argparse
import os
import sys

from .build import build_html, template_available
from .check import analyze
from .errors import CodewalkError, SpecError
from .recorder import record
from .spec import load_walkthrough


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m codewalk._run")
    parser.add_argument("spec")
    parser.add_argument("out")
    parser.add_argument("--backend", choices=["settrace", "monitoring"])
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--json-only", action="store_true")
    args = parser.parse_args(argv)

    def log(message: str) -> None:
        print(message, file=sys.stderr, flush=True)

    try:
        walkthrough = load_walkthrough(args.spec)
    except SpecError as e:
        log(f"error: {e}")
        return 1
    report = analyze(walkthrough.spec)
    for problem in report.errors:
        log(str(problem))
    if report.errors:
        return 1
    try:
        recording = record(walkthrough.spec, backend=args.backend, report=report)
    except CodewalkError as e:
        log(f"error: {e}")
        return 1

    os.makedirs(args.out, exist_ok=True)
    path = os.path.join(args.out, "steps.json")
    with open(path, "w", encoding="utf-8") as f:
        f.write(recording.to_json())
    log(
        f"recorded {len(recording.steps)} step(s) in {recording.duration:.2f}s "
        f"({recording.backend} backend) -> {path}"
    )
    if not args.json_only:
        if template_available():
            page = build_html(path)
            log(f"wrote {page}")
        else:
            log("warning: viewer template missing, index.html not written (build it with npm in viewer/)")
    for warning in recording.warnings:
        log(f"warning: {warning}")
    if recording.crashed:
        log("the program crashed; the traceback is recorded as the last step")
    if args.strict and (recording.warnings or recording.crashed):
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
