"""The summary-after rule that turns step levels into a hierarchy, and its parent= override."""

from __future__ import annotations

import json
import textwrap

from typer.testing import CliRunner

from codewalk.cli import app
from codewalk.outline import assign_parents, children_of, resolve_explicit, trailing_details
from conftest import MINIPROJ

runner = CliRunner()


def test_deeper_steps_belong_to_the_next_shallower_step():
    #         0  1  2  3  4  5  6  7
    levels = [1, 2, 2, 1, 2, 3, 3, 1]
    parents = assign_parents(levels)
    # the level-3 steps have no level-2 summary after them, so the level-1 step at 7 takes them
    assert parents == [None, 3, 3, None, 7, 7, 7, None]
    assert children_of(parents) == [[], [], [], [1, 2], [], [], [], [4, 5, 6]]


def test_trailing_and_leading_details():
    levels = [2, 2, 1, 2, 2]
    assert assign_parents(levels) == [2, 2, None, 2, 2]  # trailing details hang off the last summary
    assert trailing_details(levels) == [3, 4]
    assert assign_parents([2, 2]) == [None, None]  # a single level: everything is a root
    assert trailing_details([2, 2]) == []
    assert assign_parents([1, 3, 1]) == [None, 2, None]  # a level jump is fine
    assert assign_parents([]) == []


def test_explicit_parents_override_and_resolve_to_instances():
    levels = [1, 2, 2, 1]
    assert assign_parents(levels, [None, 0, None, None]) == [None, 0, 3, None]
    assert trailing_details([1, 2, 2], [None, 0, 0]) == []
    # parent="loop" with several recorded instances: first after, else last before
    ids = ["a", "loop", "d1", "loop", "d2"]
    assert resolve_explicit([None, None, "loop", None, "loop"], ids) == [None, None, 3, None, 3]
    assert resolve_explicit(["nope"], ["x"]) == [None]


def test_check_validates_parents_and_warns_about_structure(tmp_path):
    spec = tmp_path / "w.py"
    spec.write_text(
        textwrap.dedent(
            f"""
            from codewalk import Walkthrough
            w = Walkthrough("T", "run.py", ["Load"], root={str(MINIPROJ)!r}, levels=["Key"])
            w.step(id="entry", at="mini/stages.py::load", highlight="load", level=1)
            w.step(id="plain", at="mini/stages.py:9", level=2)
            w.step(id="detail", at="mini/stages.py:18", level=2, parent="missing")
            w.step(id="detail2", at="mini/stages.py:18", level=2, parent="entry")
            w.step(id="bad", at="mini/stages.py:18", level=2, parent="detail")
            w.step(id="deep", at="mini/stages.py::score", level=3)
            """
        )
    )
    result = runner.invoke(app, ["check", str(spec)])
    assert result.exit_code == 1, result.output
    assert "error: step 'detail': parent='missing' is not the id of any step" in result.output
    assert "error: step 'bad': parent='detail' is at level 2, which is not shallower than this step's level 2" in result.output
    assert "warning: step 'entry': level 1 step at the entry of load() is followed by deeper steps" in result.output
    assert "warning: steps 'plain', 'deep' are deeper than the steps around them but no shallower step follows them" in result.output
    assert "warning: levels= names 1 level(s) but steps go up to level 3" in result.output


def test_level_validation():
    import pytest

    from codewalk import SpecError, Walkthrough

    w = Walkthrough("T", "run.py", ["Load"], root=str(MINIPROJ))
    with pytest.raises(SpecError, match="level.*greater than or equal to 1"):
        w.step(id="x", at="run.py::main", level=0)
    with pytest.raises(SpecError, match="level"):
        w.step(id="y", at="run.py::main", level=True)
    with pytest.raises(SpecError, match="cannot be its own parent"):
        w.step(id="z", at="run.py::main", parent="z")
    with pytest.raises(SpecError, match="parent= must be a step id"):
        w.step(id="q", at="run.py::main", parent="not an id")
    step = w.step(id="ok", at="run.py::main", level=3, parent="z")
    assert step.level == 3 and step.parent == "z"
    assert w.step(id="default", at="run.py::main").level == 2


def test_record_writes_levels_and_parents(tmp_path):
    spec = tmp_path / "w.py"
    spec.write_text(
        textwrap.dedent(
            f"""
            from codewalk import Walkthrough
            w = Walkthrough("T", "run.py", ["Load", "Score"], root={str(MINIPROJ)!r}, levels=["Overview", "Walk"])
            w.step(id="load", at="mini/stages.py::load", when="return", highlight="load", level=1)
            w.step(id="acc", after="mini/stages.py:17", level=2, hit="all", max_hits=3)
            w.step(id="score", at="mini/stages.py::score", when="return", highlight="score", level=1)
            w.step(id="late", at="run.py::main", when="return", level=2, parent="load")
            """
        )
    )
    out = tmp_path / "out"
    result = runner.invoke(app, ["record", str(spec), "-o", str(out), "--json-only"])
    assert result.exit_code == 0, result.output
    data = json.loads((out / "steps.json").read_text())
    assert data["version"] == 2 and data["levels"] == ["Overview", "Walk"]
    got = [(s["id"], s["level"], s["parent"]) for s in data["steps"]]
    assert got == [
        ("load", 1, None),
        ("acc.1", 2, "score"),
        ("acc.2", 2, "score"),
        ("acc.3", 2, "score"),
        ("score", 1, None),
        ("late", 2, "load"),
    ]
