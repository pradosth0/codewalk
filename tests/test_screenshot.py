from __future__ import annotations

import json
import struct
from pathlib import Path

import pytest
from typer.testing import CliRunner

from codewalk.cli import app
from codewalk.errors import CodewalkError
from codewalk.screenshot import all_targets, read_recording, resolve_page, select_targets
from conftest import MINIPROJ

runner = CliRunner()

RECORDING = {
    "title": "T",
    "description": "intro text",
    "steps": [
        {"id": "load", "label": "1"},
        {"id": "loop.1", "label": "2.1"},
        {"id": "loop.2", "label": "2.2"},
        {"id": "weird id/with:chars", "label": "3"},
    ],
}


def png_size(path: Path) -> tuple[int, int]:
    head = path.read_bytes()[:24]
    assert head[:8] == b"\x89PNG\r\n\x1a\n"
    return struct.unpack(">II", head[16:24])


def test_targets_and_filenames():
    targets = all_targets(RECORDING)
    assert [t.filename for t in targets] == [
        "00-intro.png", "01-load.png", "02-loop.1.png", "03-loop.2.png", "04-weird_id_with_chars.png",
    ]
    assert targets[0].query == "0" and targets[1].query == "load"
    assert select_targets(RECORDING, all_steps=True) == targets
    chosen = select_targets(RECORDING, ["2.2", "load", "0", "load"])
    assert [t.id for t in chosen] == ["loop.2", "load", "intro"]
    assert all_targets({"title": "T", "description": "  ", "steps": []}) == []
    with pytest.raises(CodewalkError, match="no step 'nope'"):
        select_targets(RECORDING, ["nope"])
    with pytest.raises(CodewalkError, match="nothing to capture"):
        select_targets(RECORDING, [])


def test_read_recording_prefers_steps_json_then_embedded(tmp_path):
    page = tmp_path / "index.html"
    page.write_text('<html><script id="codewalk-data" type="application/json">{"title": "embedded", "steps": []}</script></html>')
    assert read_recording(page)["title"] == "embedded"
    (tmp_path / "steps.json").write_text(json.dumps({"title": "sibling", "steps": []}))
    assert read_recording(page)["title"] == "sibling"
    assert resolve_page(tmp_path) == page
    with pytest.raises(CodewalkError, match="not found"):
        resolve_page(tmp_path / "missing")
    bare = tmp_path / "bare"
    bare.mkdir()
    (bare / "index.html").write_text("<html></html>")
    with pytest.raises(CodewalkError, match="no embedded recording"):
        read_recording(bare / "index.html")


@pytest.fixture(scope="module")
def chromium():
    pytest.importorskip("playwright")
    from playwright.sync_api import Error, sync_playwright

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except Error as e:  # pragma: no cover - depends on the machine
            pytest.skip(f"Chromium is not installed for Playwright: {str(e).splitlines()[0]}")
        browser.close()
    return True


@pytest.fixture(scope="module")
def mini_page(tmp_path_factory, chromium):
    out = tmp_path_factory.mktemp("mini")
    result = runner.invoke(app, ["record", str(MINIPROJ / "walkthrough.py"), "-o", str(out)])
    assert result.exit_code == 0, result.output
    return out


def test_screenshot_all_steps(mini_page):
    result = runner.invoke(app, ["screenshot", str(mini_page), "--all", "--width", "1000", "--height", "700"])
    assert result.exit_code == 0, result.output
    files = sorted((mini_page / "screenshots").glob("*.png"))
    assert [f.name for f in files] == ["01-load.png", "02-total.png", "03-score.png"]
    assert all(png_size(f) == (1000, 700) for f in files)
    assert "3 screenshot(s)" in result.output
    assert "page error" not in result.output


def test_screenshot_single_step_to_file_and_dark(mini_page, tmp_path):
    target = tmp_path / "shots" / "total.png"
    result = runner.invoke(app, ["screenshot", str(mini_page / "index.html"), "--step", "total", "-o", str(target), "--dark"])
    assert result.exit_code == 0, result.output
    assert target.is_file() and png_size(target) == (1440, 900)
    bad = runner.invoke(app, ["screenshot", str(mini_page), "--step", "load", "--step", "total", "-o", str(target)])
    assert bad.exit_code == 1 and "pass a folder" in bad.output
    none = runner.invoke(app, ["screenshot", str(mini_page)])
    assert none.exit_code == 1 and "nothing to capture" in none.output
