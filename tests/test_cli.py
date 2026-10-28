from __future__ import annotations

import json
import textwrap

from typer.testing import CliRunner

from codewalk.cli import app
from conftest import BACKENDS, MINIPROJ

runner = CliRunner()


def test_check_ok():
    result = runner.invoke(app, ["check", str(MINIPROJ / "walkthrough.py")])
    assert result.exit_code == 0, result.output
    assert "ok: 3 step(s), 0 warning(s)" in result.output


def test_check_reports_errors(tmp_path):
    spec = tmp_path / "w.py"
    spec.write_text(
        textwrap.dedent(
            f"""
            from codewalk import Walkthrough
            w = Walkthrough("T", "run.py", ["Load"], root={str(MINIPROJ)!r})
            w.step(id="bad", at="mini/stages.py:9999", highlight="nope")
            """
        )
    )
    result = runner.invoke(app, ["check", str(spec)])
    assert result.exit_code == 1
    assert "error: step 'bad': mini/stages.py:9999 is past the end of the file" in result.output
    assert "highlight='nope'" in result.output
    assert "2 error(s), 0 warning(s) in 1 step(s)" in result.output


def test_record_writes_steps_json(tmp_path):
    out = tmp_path / "out"
    args = ["record", str(MINIPROJ / "walkthrough.py"), "-o", str(out), "--backend", BACKENDS[-1]]
    result = runner.invoke(app, args)
    assert result.exit_code == 0, result.output
    data = json.loads((out / "steps.json").read_text())
    assert data["backend"] == BACKENDS[-1]
    assert [s["id"] for s in data["steps"]] == ["load", "total", "score"]
    assert data["steps"][0]["text"] == "Load 5 rows."
    assert data["steps"][1]["text"].startswith("The total is 7.52")
    assert data["warnings"] == []


def test_record_strict_fails_on_warnings(tmp_path):
    spec = tmp_path / "w.py"
    spec.write_text(
        textwrap.dedent(
            f"""
            from codewalk import Walkthrough
            w = Walkthrough("T", "run.py", ["Load"], root={str(MINIPROJ)!r})
            w.step(id="never", at="run.py::main", hit=5)
            """
        )
    )
    out = tmp_path / "out"
    result = runner.invoke(app, ["record", str(spec), "-o", str(out), "--strict"])
    assert result.exit_code == 2, result.output
    data = json.loads((out / "steps.json").read_text())
    assert data["steps"] == []
    assert "hit=5 was never satisfied" in data["warnings"][0]


def test_record_timeout(tmp_path):
    (tmp_path / "loop.py").write_text("import time\nwhile True:\n    time.sleep(0.05)\n")
    spec = tmp_path / "w.py"
    spec.write_text(
        textwrap.dedent(
            """
            from codewalk import Walkthrough
            w = Walkthrough("T", "loop.py", ["Loop"], timeout=2)
            w.step(id="s", at="loop.py:3")
            """
        )
    )
    result = runner.invoke(app, ["record", str(spec), "-o", str(tmp_path / "out")])
    assert result.exit_code == 3
    assert "timed out after 2s" in result.output
