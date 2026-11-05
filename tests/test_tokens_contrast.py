"""The viewer's colour tokens keep WCAG AA contrast for text in both themes.

Reads viewer/src/styles/tokens.css, so a retuned palette fails here before it ships.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

TOKENS = Path(__file__).resolve().parents[1] / "viewer" / "src" / "styles" / "tokens.css"

# (text token, background token, where it is used, minimum ratio)
TEXT_PAIRS = [
    ("fg", "bg-0", "body text", 4.5),
    ("fg", "bg-1", "bars", 4.5),
    ("fg", "bg-2", "chips, visited stages", 4.5),
    ("fg-muted", "bg-0", "pane meta, step line", 4.5),
    ("fg-muted", "bg-1", "pane headers", 4.5),
    ("fg-muted", "bg-2", "chips", 4.5),
    ("fg-faint", "bg-0", "line numbers, hints", 4.5),
    ("fg-faint", "bg-1", "outline stages, legends", 4.5),
    ("accent", "bg-0", "links, level label, current line number", 4.5),
    ("accent", "bg-1", "links on bars", 4.5),
    ("accent", "accent-soft", "active chips, current outline row, object chips", 4.5),
    ("accent-fg", "accent-fill", "Next button, current stage", 4.5),
    ("warn", "bg-1", "warnings badge", 4.5),
    ("error", "bg-0", "errors", 4.5),
    ("ok", "bg-0", "copied", 3.0),
    ("accent-fill", "bg-0", "current stage against the page", 3.0),
    ("fg-faint", "bg-2", "visited badge on a stage", 3.0),
]


def luminance(hex_colour: str) -> float:
    h = hex_colour.lstrip("#")
    channels = [int(h[i : i + 2], 16) / 255 for i in (0, 2, 4)]
    linear = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast(a: str, b: str) -> float:
    la, lb = luminance(a), luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def tokens(css: str, selector: str) -> dict[str, str]:
    block = re.search(re.escape(selector) + r"\s*\{(.*?)\}", css, re.S)
    assert block, f"no {selector} block in tokens.css"
    return dict(re.findall(r"--([a-z0-9-]+):\s*(#[0-9a-fA-F]{6})", block.group(1)))


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_text_contrast(theme):
    css = TOKENS.read_text()
    t = tokens(css, ":root" if theme == "light" else ":root[data-theme='dark']")
    failures = []
    for fg, bg, where, need in TEXT_PAIRS:
        ratio = contrast(t[fg], t[bg])
        if ratio < need:
            failures.append(f"{fg} on {bg} ({where}): {ratio:.2f} < {need}")
    assert not failures, "\n".join(failures)
