"""The `codewalk` command line."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import List, Optional

import typer

from .build import build_html, template_available
from .check import analyze
from .errors import CodewalkError, SpecError
from .scaffold import write_scaffold
from .screenshot import DEFAULT_HEIGHT, DEFAULT_WIDTH
from .screenshot import screenshot as _screenshot
from .serve import serve as _serve
from .spec import Walkthrough, load_walkthrough

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="Agent-authored, debugger-style walkthroughs of Python code.",
)


@app.command()
def init(
    directory: Path = typer.Argument(Path("."), exists=True, file_okay=False, help="Project folder to describe"),
    entry: Optional[str] = typer.Option(None, "--entry", help='What to run, e.g. "run.py --rows 100" or "pkg.module:main"; detected if omitted'),
    out: Optional[Path] = typer.Option(None, "--out", "-o", help="Where to write the spec; default: DIRECTORY/walkthrough.py"),
    force: bool = typer.Option(False, "--force", help="Overwrite an existing file"),
) -> None:
    """Write a commented walkthrough.py template that already passes `codewalk check`."""
    try:
        result = write_scaffold(directory, entry=entry, out=out, force=force)
    except CodewalkError as e:
        typer.echo(f"error: {e}", err=True)
        raise typer.Exit(code=1)
    typer.echo(f"wrote {result.path} (entry: {result.entry})")
    for hint in result.hints:
        typer.echo(f"hint: {hint}")
    typer.echo(f"next: edit the steps, then `codewalk check {result.path}` and `codewalk record {result.path}`")


def _load(spec_path: Path) -> Walkthrough:
    try:
        return load_walkthrough(spec_path)
    except SpecError as e:
        typer.echo(f"error: {e}", err=True)
        raise typer.Exit(code=1)


@app.command()
def check(
    spec: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True, help="Path to walkthrough.py"),
) -> None:
    """Validate a walkthrough without running anything."""
    walkthrough = _load(spec)
    report = analyze(walkthrough.spec)
    for problem in report.problems():
        typer.echo(str(problem), err=True)
    n = len(walkthrough.spec.steps)
    if report.errors:
        typer.echo(
            f"{len(report.errors)} error(s), {len(report.warnings)} warning(s) in {n} step(s)",
            err=True,
        )
        raise typer.Exit(code=1)
    typer.echo(f"ok: {n} step(s), {len(report.warnings)} warning(s)")


@app.command()
def record(
    spec: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True, help="Path to walkthrough.py"),
    out: Path = typer.Option(Path("out"), "--out", "-o", help="Output directory for steps.json"),
    strict: bool = typer.Option(False, "--strict", help="Exit non-zero on warnings or a crash"),
    timeout: Optional[float] = typer.Option(None, help="Seconds; defaults to the walkthrough's timeout"),
    backend: Optional[str] = typer.Option(None, help="bdb backend: settrace or monitoring"),
    json_only: bool = typer.Option(False, "--json-only", help="Write steps.json but not index.html"),
) -> None:
    """Run the entry point under the recorder; write OUT/steps.json and OUT/index.html."""
    walkthrough = _load(spec)
    report = analyze(walkthrough.spec)
    if report.errors:
        for problem in report.problems():
            typer.echo(str(problem), err=True)
        raise typer.Exit(code=1)
    command = [sys.executable, "-m", "codewalk._run", str(spec), str(out)]
    if strict:
        command.append("--strict")
    if backend:
        command += ["--backend", backend]
    if json_only:
        command.append("--json-only")
    limit = timeout or walkthrough.spec.timeout
    try:
        completed = subprocess.run(command, timeout=limit)
    except subprocess.TimeoutExpired:
        typer.echo(
            f"error: recording timed out after {limit:g}s "
            "(raise timeout= in the walkthrough or pass --timeout)",
            err=True,
        )
        raise typer.Exit(code=3)
    if completed.returncode:
        raise typer.Exit(code=completed.returncode)


@app.command()
def build(
    steps: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True, help="A steps.json"),
    out: Optional[Path] = typer.Option(None, "--out", "-o", help="Output file; default: index.html next to steps.json"),
) -> None:
    """Build index.html from a steps.json, e.g. after upgrading the viewer."""
    if not template_available():
        typer.echo("error: the viewer template is missing; run `npm install && npm run build` in viewer/", err=True)
        raise typer.Exit(code=1)
    try:
        target = build_html(steps, out)
    except CodewalkError as e:
        typer.echo(f"error: {e}", err=True)
        raise typer.Exit(code=1)
    typer.echo(f"wrote {target}")


@app.command()
def serve(
    directory: Path = typer.Argument(Path("out"), exists=True, file_okay=False, help="Folder with index.html"),
    port: int = typer.Option(8731, help="Port; 0 picks a free one"),
    host: str = typer.Option("127.0.0.1", help="Interface to bind"),
    open_browser: bool = typer.Option(False, "--open", help="Open the page in a browser"),
) -> None:
    """Serve an output folder over HTTP (until Ctrl-C)."""
    if not (directory / "index.html").is_file():
        typer.echo(f"warning: {directory} has no index.html yet; run `codewalk build {directory}/steps.json`", err=True)
    _serve(directory, host=host, port=port, open_browser=open_browser)


@app.command()
def screenshot(
    page: Path = typer.Argument(Path("out"), exists=True, help="index.html, or the folder that holds it"),
    step: Optional[List[str]] = typer.Option(None, "--step", "-s", help="Step id, label or position; repeatable"),
    all_steps: bool = typer.Option(False, "--all", help="Every step (and the intro when there is one)"),
    out: Optional[Path] = typer.Option(None, "--out", "-o", help="A .png (single step) or a folder; default: screenshots/ next to the page"),
    width: int = typer.Option(DEFAULT_WIDTH, help="Viewport width in pixels"),
    height: int = typer.Option(DEFAULT_HEIGHT, help="Viewport height in pixels"),
    dark: bool = typer.Option(False, "--dark", help="Render with the dark colour scheme"),
    timeout: float = typer.Option(30.0, help="Seconds to wait for each page to settle"),
) -> None:
    """Render steps of a built walkthrough to PNG files (needs the `screenshot` extra)."""
    try:
        written = _screenshot(
            page,
            steps=step,
            all_steps=all_steps,
            out=out,
            width=width,
            height=height,
            dark=dark,
            timeout=timeout,
            log=lambda m: typer.echo(m, err=True),
        )
    except CodewalkError as e:
        typer.echo(f"error: {e}", err=True)
        raise typer.Exit(code=1)
    typer.echo(f"{len(written)} screenshot(s) in {written[0].parent}")
