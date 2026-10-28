"""Render pages of a built walkthrough to PNG files with Playwright.

Playwright is an optional extra (`codewalk[screenshot]`); nothing here is imported by the
rest of the package, so a missing Playwright only affects the `screenshot` command.
"""

from __future__ import annotations

import json
import os
import re
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Optional, Union

from .errors import CodewalkError
from .serve import make_server, server_url

DATA_BLOCK = re.compile(r'<script id="codewalk-data" type="application/json">(.*?)</script>', re.S)
INSTALL_HINT = (
    "the screenshot command needs Playwright: add the extra with `uv add 'codewalk[screenshot]'` "
    "(or `pip install 'codewalk[screenshot]'`), then run `playwright install chromium`"
)
DEFAULT_WIDTH = 1440
DEFAULT_HEIGHT = 900


@dataclass(frozen=True)
class Target:
    """One page to capture: the intro (position 0) or a recorded step (position 1..n)."""

    position: int
    id: str
    label: str
    query: str  # value of the ?step= parameter
    filename: str


def resolve_page(path: Union[str, os.PathLike]) -> Path:
    """Accept index.html or the folder that holds it."""
    page = Path(path)
    if page.is_dir():
        page = page / "index.html"
    if not page.is_file():
        raise CodewalkError(f"{page} not found; run `codewalk record` (or `codewalk build`) first")
    return page


def read_recording(page: Path) -> dict[str, Any]:
    """The recording shown by `page`: steps.json next to it, else the embedded data block."""
    sibling = page.with_name("steps.json")
    if sibling.is_file():
        return json.loads(sibling.read_text(encoding="utf-8"))
    match = DATA_BLOCK.search(page.read_text(encoding="utf-8"))
    if not match:
        raise CodewalkError(f"{page} has no embedded recording and no steps.json next to it")
    return json.loads(match.group(1))


def _safe_name(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("._") or "step"


def all_targets(recording: dict[str, Any]) -> list[Target]:
    targets: list[Target] = []
    if str(recording.get("description", "")).strip():
        targets.append(Target(0, "intro", "intro", "0", "00-intro.png"))
    for i, step in enumerate(recording.get("steps", []), start=1):
        step_id = str(step["id"])
        targets.append(Target(i, step_id, str(step.get("label", i)), step_id, f"{i:02d}-{_safe_name(step_id)}.png"))
    return targets


def select_targets(recording: dict[str, Any], steps: Optional[Iterable[str]] = None, *, all_steps: bool = False) -> list[Target]:
    """Targets for `--all`, or for each requested step id, label or position."""
    available = all_targets(recording)
    if all_steps:
        return available
    chosen: list[Target] = []
    for name in steps or []:
        wanted = str(name).strip()
        match = next(
            (t for t in available if wanted in (t.id, t.label, str(t.position))),
            None,
        )
        if match is None:
            ids = ", ".join(t.id for t in available) or "(none)"
            raise CodewalkError(f"no step {wanted!r} in this recording; available: {ids}")
        if match not in chosen:
            chosen.append(match)
    if not chosen:
        raise CodewalkError("nothing to capture: pass --step ID (repeatable) or --all")
    return chosen


def _css_string(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def screenshot(
    page_path: Union[str, os.PathLike],
    *,
    steps: Optional[Iterable[str]] = None,
    all_steps: bool = False,
    out: Union[str, os.PathLike, None] = None,
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
    dark: bool = False,
    timeout: float = 30.0,
    log: Optional[Callable[[str], None]] = None,
) -> list[Path]:
    """Capture the requested steps of a built page; return the PNG paths written.

    `out` is a .png path when exactly one step is requested, otherwise a folder
    (default: `screenshots/` next to the page). Files are named `NN-<step id>.png`.
    """
    page_file = resolve_page(page_path)
    recording = read_recording(page_file)
    targets = select_targets(recording, steps, all_steps=all_steps)
    try:
        from playwright.sync_api import Error as PlaywrightError
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise CodewalkError(INSTALL_HINT) from None

    out_path = Path(out) if out is not None else page_file.parent / "screenshots"
    single_file = out_path.suffix.lower() == ".png"
    if single_file and len(targets) > 1:
        raise CodewalkError(f"{out_path} is a file but {len(targets)} steps were requested; pass a folder")
    if single_file:
        out_path.parent.mkdir(parents=True, exist_ok=True)
    else:
        out_path.mkdir(parents=True, exist_ok=True)

    # The page is served over HTTP (not file://) so that it behaves exactly as `codewalk serve` shows it.
    server = make_server(page_file.parent, port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    written: list[Path] = []
    page_errors: list[str] = []
    wait_ms = int(timeout * 1000)
    try:
        base = server_url(server) + page_file.name
        with sync_playwright() as playwright:
            try:
                browser = playwright.chromium.launch()
            except PlaywrightError as e:
                first_line = str(e).strip().splitlines()[0] if str(e).strip() else "unknown error"
                raise CodewalkError(f"could not launch Chromium ({first_line}); run `playwright install chromium`") from None
            try:
                context = browser.new_context(
                    viewport={"width": width, "height": height},
                    device_scale_factor=1,
                    color_scheme="dark" if dark else "light",
                )
                page = context.new_page()
                page.on("pageerror", lambda err: page_errors.append(str(err)))
                for target in targets:
                    page.goto(f"{base}?step={target.query}", wait_until="load", timeout=wait_ms)
                    # The viewer marks the root with the current step and each async pane with data-settled.
                    page.wait_for_selector(f".app[data-step={_css_string(target.id)}]", timeout=wait_ms)
                    page.wait_for_selector('.schema[data-settled="true"]', timeout=wait_ms)
                    page.wait_for_selector('.code[data-settled="true"]', timeout=wait_ms)
                    page.wait_for_function(
                        "() => document.fonts.status === 'loaded' && Array.from(document.images).every((i) => i.complete)",
                        timeout=wait_ms,
                    )
                    file = out_path if single_file else out_path / target.filename
                    page.screenshot(path=str(file))
                    written.append(file)
                    if log:
                        log(f"wrote {file}  (step {target.label}: {target.id})")
            finally:
                browser.close()
    finally:
        server.shutdown()
        server.server_close()
    if page_errors and log:
        for err in page_errors:
            log(f"warning: page error while rendering: {err}")
    return written
