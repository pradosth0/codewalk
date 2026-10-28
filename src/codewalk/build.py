"""Embed a recording into the prebuilt viewer template to produce one self-contained HTML file."""

from __future__ import annotations

import html
import json
import os
from pathlib import Path
from typing import Any, Optional, Union

from .errors import CodewalkError

TEMPLATE = Path(__file__).parent / "viewer" / "index.html"
DATA_PLACEHOLDER = "__CODEWALK_DATA__"
TITLE_PLACEHOLDER = "__CODEWALK_TITLE__"


def template_available() -> bool:
    return TEMPLATE.is_file()


def embed(recording: dict[str, Any], *, template_path: Optional[Path] = None) -> str:
    """Return the viewer page with the recording embedded as a JSON data block."""
    path = template_path or TEMPLATE
    if not path.is_file():
        raise CodewalkError(
            f"the viewer template is missing ({path}); build it with `npm install && npm run build` in viewer/"
        )
    template = path.read_text(encoding="utf-8")
    if DATA_PLACEHOLDER not in template:
        raise CodewalkError(f"the viewer template {path} has no {DATA_PLACEHOLDER} placeholder")
    payload = json.dumps(recording, ensure_ascii=False, allow_nan=False)
    # Inside a <script> block only "</" can end the element; "<\/" is the same string to JSON.
    payload = payload.replace("</", "<\\/")
    title = html.escape(str(recording.get("title") or "codewalk"))
    page = template.replace(TITLE_PLACEHOLDER, title)
    return page.replace(DATA_PLACEHOLDER, payload, 1)


def build_html(steps_json: Union[str, os.PathLike], out: Union[str, os.PathLike, None] = None) -> Path:
    """Read a steps.json and write index.html next to it (or at `out`)."""
    source = Path(steps_json)
    if not source.is_file():
        raise CodewalkError(f"{source} not found")
    try:
        recording = json.loads(source.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise CodewalkError(f"{source} is not valid JSON: {e}") from None
    target = Path(out) if out is not None else source.with_name("index.html")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(embed(recording), encoding="utf-8")
    return target
