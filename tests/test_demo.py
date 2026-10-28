"""The shipped example must check clean and record every step without warnings."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from codewalk.cli import app

DEMO = Path(__file__).resolve().parents[1] / "examples" / "demo_pipeline"
SPEC = DEMO / "walkthroughs" / "train.py"
runner = CliRunner()


def test_demo_walkthrough_checks_clean():
    result = runner.invoke(app, ["check", str(SPEC)])
    assert result.exit_code == 0, result.output
    assert "ok: 9 step(s), 0 warning(s)" in result.output


def test_demo_walkthrough_records_every_step(tmp_path):
    out = tmp_path / "demo"
    result = runner.invoke(app, ["record", str(SPEC), "-o", str(out), "--strict"])
    assert result.exit_code == 0, result.output
    data = json.loads((out / "steps.json").read_text(encoding="utf-8"))
    assert data["warnings"] == []
    ids = [s["id"] for s in data["steps"]]
    assert ids == [
        "load", "duplicates", "outliers", "missing", "features",
        "epoch.1", "epoch.2", "epoch.3", "epoch.4",
        "fitted", "score", "report",
    ]
    kinds = {o["display"]["kind"] for s in data["steps"] for o in s["objects"]}
    assert kinds == {"table", "json", "array", "image", "html"}, kinds
    by_id = {s["id"]: s for s in data["steps"]}
    assert "shape (183, 8)" in by_id["load"]["text"]
    flat = " ".join(by_id["duplicates"]["text"].split())
    assert "removed 3 of them (183 rows before, 180 after)" in flat
    assert by_id["epoch.1"]["text"].startswith("Epoch 0: the mean squared error is 6,")
    assert by_id["epoch.4"]["location"]["hit"] == 4  # hits that satisfied the condition
    assert by_id["epoch.4"]["text"].startswith("Epoch 119:")
    assert by_id["epoch.1"]["objects"][0]["name"] == "plot"
    assert by_id["report"]["code"]["focus"] == [[31, 35]]
    assert "rows: 183 raw -> 178 clean" in by_id["report"]["console"] and "r2: 0.895" in by_id["report"]["console"]
    assert by_id["report"]["location"]["line"] == 36
    assert (out / "index.html").is_file()
    # the walkthrough's relative root resolves against the spec file, wherever record runs from
    assert data["entry"] == "run.py --epochs 120"
