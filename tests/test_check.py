from __future__ import annotations

import textwrap

import pytest

from codewalk import Walkthrough, load_walkthrough
from codewalk.check import analyze
from conftest import MINIPROJ, line_of

STAGES = ["Load", "Transform", "Accumulate", "Score"]
STAGES_FILE = MINIPROJ / "mini" / "stages.py"


def wt(entry="run.py --rows 5", schema=STAGES, root=MINIPROJ) -> Walkthrough:
    return Walkthrough("T", entry, schema, root=root)


def messages(problems):
    return [str(p) for p in problems]


def test_fixture_walkthrough_is_clean():
    report = analyze(load_walkthrough(MINIPROJ / "walkthrough.py").spec)
    assert report.ok and report.warnings == []
    steps = {s.spec.id: s for s in report.resolved.steps}
    assert steps["load"].break_line == line_of(STAGES_FILE, "data = [i * 1.5")
    assert steps["load"].function == "load"
    assert steps["total"].mode == "after" and steps["total"].break_line == line_of(STAGES_FILE, "total = sum(out)")
    assert steps["total"].function == "transform"
    assert steps["score"].mode == "return"
    assert steps["load"].rel_file == "mini/stages.py"
    assert (steps["load"].code_start, steps["load"].code_end) == (
        line_of(STAGES_FILE, "def load"),
        line_of(STAGES_FILE, "return data"),
    )


def test_missing_file_and_bad_lines():
    w = wt()
    w.step(id="nofile", at="mini/nothing.py:3")
    w.step(id="eof", at="mini/stages.py:9999")
    w.step(id="blank", at=f"mini/stages.py:{line_of(STAGES_FILE, 'import math') + 1}")
    w.step(id="nofunc", at="mini/stages.py::nothing")
    w.step(id="fine", at="mini/stages.py::load")
    report = analyze(w.spec)
    msgs = messages(report.errors)
    assert len(msgs) == 4
    assert msgs[0].startswith("error: step 'nofile': file not found: mini/nothing.py")
    assert "past the end of the file" in msgs[1]
    assert "blank or a comment" in msgs[2]
    assert "no function 'nothing'" in msgs[3] and "available: load, transform" in msgs[3]
    assert report.resolved is None


def test_non_executable_line_warns(tmp_path):
    (tmp_path / "m.py").write_text(
        textwrap.dedent(
            """
            def f(a):
                if a:
                    return 1
                else:
                    return 2
            """
        ).lstrip()
    )
    w = Walkthrough("T", "m.py", ["A"], root=tmp_path)
    w.step(id="else", at="m.py:4")
    report = analyze(w.spec)
    assert report.ok
    assert len(report.warnings) == 1 and "carries no bytecode" in str(report.warnings[0])


def test_expression_and_condition_syntax():
    w = wt()
    w.step(id="s", at="mini/stages.py::load", show={"x": "df.head("}, condition="n >")
    report = analyze(w.spec)
    msgs = messages(report.errors)
    assert len(msgs) == 2
    assert "show['x'] = 'df.head(' is not a valid expression" in msgs[0]
    assert "condition = 'n >' is not a valid expression" in msgs[1]


def test_highlight_checks_depend_on_schema_origin():
    w = wt()
    w.step(id="s", at="mini/stages.py::load", highlight="nope")
    report = analyze(w.spec)
    assert not report.ok
    assert "highlight='nope' is not a node of the schema (known: load, transform, accumulate, score)" in str(report.errors[0])

    m = wt(schema="flowchart LR\n load --> clean")
    m.step(id="s", at="mini/stages.py::load", highlight="nope")
    report = analyze(m.spec)
    assert report.ok
    assert "heuristically" in str(report.warnings[0])


def test_placeholder_and_focus_warnings():
    w = wt()
    w.step(id="s", at="mini/stages.py::load", show={"n": "n"}, text="{{n}} and {{m}}", focus="run.py:1-2")
    report = analyze(w.spec)
    assert report.ok
    msgs = messages(report.warnings)
    assert any("focus= points at run.py" in m for m in msgs)
    assert any("{{m}}" in m for m in msgs)
    assert report.resolved.steps[0].focus == []


def test_entry_checks():
    missing = wt(entry="nothing.py")
    assert "entry script 'nothing.py' not found" in str(analyze(missing.spec).errors[0])
    callable_missing = wt(entry="nothing.here:main")
    report = analyze(callable_missing.spec)
    assert report.ok and "entry module 'nothing.here' was not found" in str(report.warnings[0])
    callable_ok = wt(entry="mini.stages:demo")
    assert not any("entry module" in str(w) for w in analyze(callable_ok.spec).warnings)


def test_bad_root():
    report = analyze(wt(root=MINIPROJ / "does-not-exist").spec)
    assert not report.ok and "is not a directory" in str(report.errors[0])


def test_code_range_errors():
    w = wt()
    w.step(id="a", at="mini/stages.py::load", code="mini/stages.py:1-9999")
    w.step(id="b", at="mini/stages.py::load", code="nothing.py::f")
    msgs = messages(analyze(w.spec).errors)
    assert "goes past the end of the file" in msgs[0]
    assert "code: file not found: nothing.py" in msgs[1]
