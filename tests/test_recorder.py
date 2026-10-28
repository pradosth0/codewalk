from __future__ import annotations

import json
import math
import os
import sys

import pytest

from codewalk import Walkthrough
from codewalk.recorder import record
from conftest import MINIPROJ, line_of

STAGES = ["Load", "Transform", "Accumulate", "Score"]
STAGES_FILE = MINIPROJ / "mini" / "stages.py"
RUN_FILE = MINIPROJ / "run.py"


def wt(entry: str = "run.py --rows 5", **kwargs) -> Walkthrough:
    return Walkthrough("Mini", entry, STAGES, root=MINIPROJ, **kwargs)


def loc(snippet: str, file: str = "mini/stages.py", nth: int = 1) -> str:
    return f"{file}:{line_of(MINIPROJ / file, snippet, nth)}"


def displays(step: dict) -> dict:
    return {o["name"]: o["display"] for o in step["objects"]}


EXPECTED_TOTAL = sum(math.sqrt(i * 1.5) for i in range(5))


def test_before_semantics(backend):
    w = wt()
    w.step(id="pr", at=loc('print(f"loaded'), show={"data": "data", "n": "len(data)"})
    rec = record(w.spec, backend=backend)
    assert rec.backend == backend
    assert [s["id"] for s in rec.steps] == ["pr"]
    step = rec.steps[0]
    assert step["location"]["function"] == "load"
    assert step["location"]["mode"] == "before"
    assert step["location"]["file"] == "mini/stages.py"
    objs = displays(step)
    assert objs["n"] == {"kind": "json", "value": 5, "type": "int"}
    assert objs["data"]["value"] == [0.0, 1.5, 3.0, 4.5, 6.0]
    assert "loaded" not in step["console"]  # the print on that line has not run yet
    assert rec.warnings == []
    assert not rec.crashed


def test_after_semantics(backend):
    line = line_of(STAGES_FILE, "total = sum(out)")
    w = wt()
    w.step(id="t", after=f"mini/stages.py:{line}", show={"total": "total"})
    rec = record(w.spec, backend=backend)
    step = rec.steps[0]
    assert step["location"]["mode"] == "after"
    assert step["location"]["line"] == line
    assert step["location"]["paused_line"] == line + 1
    assert displays(step)["total"]["value"] == pytest.approx(EXPECTED_TOTAL)
    assert "loaded 5 rows" in step["console"]
    assert rec.warnings == []


def test_after_on_the_last_line_of_a_function_captures_at_its_return(backend):
    line = line_of(STAGES_FILE, "return out, total")
    w = wt()
    w.step(id="r", after=f"mini/stages.py:{line}", show={"total": "total"})
    rec = record(w.spec, backend=backend)
    assert [s["id"] for s in rec.steps] == ["r"]
    step = rec.steps[0]
    assert step["location"]["line"] == line
    assert displays(step)["total"]["value"] == pytest.approx(EXPECTED_TOTAL)
    assert rec.warnings == []


def test_function_entry(backend):
    w = wt()
    w.step(id="entry", at="mini/stages.py::load", show={"n": "n"})
    rec = record(w.spec, backend=backend)
    step = rec.steps[0]
    assert step["location"]["line"] == line_of(STAGES_FILE, "data = [i * 1.5")  # docstring skipped
    assert step["location"]["function"] == "load"
    assert displays(step)["n"]["value"] == 5


def test_function_return_exposes_return_value(backend):
    w = wt()
    w.step(id="ret", at="mini/stages.py::score", when="return", show={"r": "__return__", "mean": "mean"})
    rec = record(w.spec, backend=backend)
    step = rec.steps[0]
    assert step["location"]["mode"] == "return"
    assert step["location"]["line"] == line_of(STAGES_FILE, 'return {"mean"')
    objs = displays(step)
    assert objs["r"]["value"] == {"mean": pytest.approx(EXPECTED_TOTAL / 5), "n": 5}
    assert objs["mean"]["value"] == pytest.approx(EXPECTED_TOTAL / 5)


def test_method_breakpoint_with_hit_n(backend):
    w = wt()
    w.step(id="add3", at="mini/stages.py::Accumulator.add", hit=3, show={"count": "self.count", "x": "x"})
    rec = record(w.spec, backend=backend)
    assert len(rec.steps) == 1
    step = rec.steps[0]
    assert step["location"]["hit"] == 3
    assert displays(step)["count"]["value"] == 2
    assert displays(step)["x"]["value"] == pytest.approx(math.sqrt(3.0))


def test_hit_all_records_sub_steps_up_to_max_hits(backend):
    line = line_of(STAGES_FILE, "y = math.sqrt(x)")
    w = wt()
    w.step(id="sq", after=f"mini/stages.py:{line}", hit="all", max_hits=3, show={"y": "y"}, title="Square root")
    rec = record(w.spec, backend=backend)
    assert [s["id"] for s in rec.steps] == ["sq.1", "sq.2", "sq.3"]
    assert [s["label"] for s in rec.steps] == ["1.1", "1.2", "1.3"]
    assert [s["spec_id"] for s in rec.steps] == ["sq"] * 3
    assert [s["title"] for s in rec.steps] == [f"Square root (hit {i})" for i in (1, 2, 3)]
    ys = [displays(s)["y"]["value"] for s in rec.steps]
    assert ys == pytest.approx([0.0, math.sqrt(1.5), math.sqrt(3.0)])
    assert rec.warnings == []


def test_condition(backend):
    w = wt()
    w.step(id="big", at=loc("out.append(y)"), condition="x > 3", show={"x": "x", "y": "y"})
    rec = record(w.spec, backend=backend)
    assert len(rec.steps) == 1
    step = rec.steps[0]
    assert step["location"]["hit"] == 1
    assert displays(step)["x"]["value"] == 4.5


def test_failing_show_expression_is_recorded_not_fatal(backend):
    w = wt()
    w.step(id="load", at="mini/stages.py::load", show={"bad": "nope + 1", "ok": "n"})
    rec = record(w.spec, backend=backend)
    step = rec.steps[0]
    bad, ok = step["objects"]
    assert bad["display"]["kind"] == "error"
    assert "NameError" in bad["display"]["message"]
    assert "n" in bad["display"]["names"]
    assert ok["display"]["value"] == 5
    assert len(rec.warnings) == 1 and "show['bad']" in rec.warnings[0]


def test_unreached_step_warns(backend):
    w = wt()
    w.step(id="never", at=loc('raise ValueError("boom")', file="run.py"))
    rec = record(w.spec, backend=backend)
    assert rec.steps == []
    assert rec.warnings == [f"step 'never' at run.py:{line_of(RUN_FILE, 'raise ValueError')} was never reached"]


def test_hit_n_never_satisfied_warns(backend):
    w = wt()
    w.step(id="add99", at="mini/stages.py::Accumulator.add", hit=99)
    rec = record(w.spec, backend=backend)
    assert rec.steps == []
    assert len(rec.warnings) == 1
    assert "hit 5 time(s)" in rec.warnings[0] and "hit=99" in rec.warnings[0]


def test_order_mismatch_warns(backend):
    w = wt()
    w.step(id="t", at="mini/stages.py::transform")
    w.step(id="l", at="mini/stages.py::load")
    rec = record(w.spec, backend=backend)
    assert [s["id"] for s in rec.steps] == ["l", "t"]
    assert len(rec.warnings) == 1
    assert "different order" in rec.warnings[0] and "l -> t" in rec.warnings[0]


def test_crash_is_recorded_as_last_step(backend):
    w = wt(entry="run.py --rows 5 --fail")
    w.step(id="load", at="mini/stages.py::load", show={"n": "n"})
    rec = record(w.spec, backend=backend)
    assert rec.crashed
    assert [s["id"] for s in rec.steps] == ["load", "crash"]
    crash = rec.steps[-1]
    assert crash["kind"] == "crash"
    assert "ValueError: boom" in crash["traceback"]
    assert "bdb.py" not in crash["traceback"]
    assert crash["location"]["file"] == "run.py"
    assert crash["location"]["line"] == line_of(RUN_FILE, "raise ValueError")
    assert crash["code"]["current"] == crash["location"]["line"]
    assert "total" in crash["console"]


def test_console_is_split_between_steps(backend):
    w = wt()
    w.step(id="a", at="mini/stages.py::load")
    w.step(id="b", at="mini/stages.py::score")
    rec = record(w.spec, backend=backend)
    a, b = rec.steps
    assert a["console"] == ""
    assert "loaded 5 rows" in b["console"] and "total " in b["console"]


def test_default_code_range_is_the_enclosing_function(backend):
    line = line_of(STAGES_FILE, "total = sum(out)")
    w = wt()
    w.step(id="t", after=f"mini/stages.py:{line}")
    rec = record(w.spec, backend=backend)
    code = rec.steps[0]["code"]
    assert code["file"] == "mini/stages.py"
    assert code["start"] == line_of(STAGES_FILE, "def transform")
    assert code["end"] == line_of(STAGES_FILE, "return out, total")
    assert code["current"] == line
    assert code["source"].startswith("def transform(data):")
    assert code["focus"] == []


def test_explicit_code_range_and_focus(backend):
    w = wt()
    w.step(id="t", at="mini/stages.py::transform", code="mini/stages.py:1-3", focus="mini/stages.py:3")
    rec = record(w.spec, backend=backend)
    code = rec.steps[0]["code"]
    assert (code["start"], code["end"]) == (1, 3)
    assert code["source"] == "\n".join(STAGES_FILE.read_text().splitlines()[:3])
    assert code["current"] is None  # the pause line is outside the shown range
    assert code["focus"] == [[3, 3]]


def test_code_can_show_a_function_from_another_file(backend):
    w = wt()
    w.step(id="t", at="mini/stages.py::transform", code="run.py::main")
    rec = record(w.spec, backend=backend)
    code = rec.steps[0]["code"]
    assert code["file"] == "run.py"
    assert code["start"] == line_of(RUN_FILE, "def main")
    assert code["current"] is None


def test_placeholders_in_text(backend):
    w = wt()
    w.step(id="l", at="mini/stages.py::load", show={"n": "n"}, text="n is {{ n }}, {{missing}} stays")
    rec = record(w.spec, backend=backend)
    assert rec.steps[0]["text"] == "n is 5, {{missing}} stays"


def test_callable_entry(backend):
    w = wt(entry="mini.stages:demo")
    w.step(id="s", at="mini/stages.py::score", when="return", show={"r": "__return__"})
    rec = record(w.spec, backend=backend)
    assert displays(rec.steps[0])["r"]["value"]["n"] == 3


def test_argv_env_cwd_are_applied_then_restored(backend):
    before = (os.getcwd(), list(sys.argv), dict(os.environ))
    w = wt(entry="run.py --rows 7", env={"CODEWALK_TEST_VAR": "yes"})
    w.step(id="l", at="mini/stages.py::load", show={"n": "n", "var": "__import__('os').environ.get('CODEWALK_TEST_VAR')", "cwd": "__import__('os').getcwd()"})
    rec = record(w.spec, backend=backend)
    objs = displays(rec.steps[0])
    assert objs["n"]["value"] == 7
    assert objs["var"]["value"] == "yes"
    assert os.path.realpath(objs["cwd"]["value"]) == os.path.realpath(str(MINIPROJ))
    assert (os.getcwd(), list(sys.argv), dict(os.environ)) == before


def test_system_exit_zero_is_not_a_crash(backend):
    w = wt(entry="run.py --help")
    w.step(id="l", at="mini/stages.py::load")
    rec = record(w.spec, backend=backend)
    assert not rec.crashed
    assert rec.steps == []
    assert rec.warnings and "never reached" in rec.warnings[0]


def test_json_payload_shape(backend):
    w = wt()
    w.step(id="l", at="mini/stages.py::load", highlight="load", title="Load")
    w.step(id="s", at="mini/stages.py::score", highlight=["score"])
    rec = record(w.spec, backend=backend)
    data = json.loads(rec.to_json())
    assert data["version"] == 1
    assert data["title"] == "Mini"
    assert data["entry"] == "run.py --rows 5"
    assert data["schema"]["nodes"] == ["load", "transform", "accumulate", "score"]
    assert data["schema"]["source"].startswith("flowchart LR")
    assert [s["index"] for s in data["steps"]] == [1, 2]
    assert [s["label"] for s in data["steps"]] == ["1", "2"]
    assert data["steps"][0]["title"] == "Load"
    assert data["steps"][1]["title"].startswith("score (mini/stages.py:")
    assert data["steps"][0]["highlight"] == ["load"]
    elapsed = [s["location"]["elapsed"] for s in data["steps"]]
    assert elapsed == sorted(elapsed)
    assert data["duration"] >= elapsed[-1]
