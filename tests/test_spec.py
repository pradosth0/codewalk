from __future__ import annotations

import textwrap

import pytest

from codewalk import SpecError, Walkthrough, load_walkthrough
from codewalk.spec import CodeRange, Entry, Location, SchemaSpec, mermaid_node_ids, stages_to_mermaid
from conftest import MINIPROJ

STAGES = ["Load", "Transform"]


def wt(**kwargs) -> Walkthrough:
    return Walkthrough("T", "run.py", STAGES, root=MINIPROJ, **kwargs)


# ---------------------------------------------------------------- parsing helpers


def test_location_parse():
    assert Location.parse("a/b.py:12", field="at") == Location(file="a/b.py", line=12)
    assert Location.parse("a/b.py::f", field="at") == Location(file="a/b.py", function="f")
    assert Location.parse("a/b.py::Cls.method", field="at").function == "Cls.method"
    with pytest.raises(SpecError, match="expected"):
        Location.parse("a/b.py", field="at")
    with pytest.raises(SpecError, match="start at 1"):
        Location.parse("a/b.py:0", field="at")


def test_code_range_parse():
    assert CodeRange.parse("x.py:3-9", field="code") == CodeRange(file="x.py", start=3, end=9)
    assert CodeRange.parse("x.py:4", field="code") == CodeRange(file="x.py", start=4, end=4)
    assert CodeRange.parse("x.py::f", field="code").function == "f"
    with pytest.raises(SpecError):
        CodeRange.parse("x.py:9-3", field="code")


def test_entry_parse():
    e = Entry.parse("scripts/run.py --rows 5 'two words'")
    assert e.kind == "script" and e.target == "scripts/run.py" and e.args == ["--rows", "5", "two words"]
    c = Entry.parse("pkg.mod:main")
    assert c.kind == "callable" and c.module == "pkg.mod" and c.function == "main"
    with pytest.raises(SpecError):
        Entry.parse("scripts/run")
    with pytest.raises(SpecError):
        Entry.parse("")


def test_stages_to_mermaid():
    source, ids = stages_to_mermaid(["Load CSV", "Clean", "Clean", 'Say "hi"'])
    assert ids == ["load_csv", "clean", "clean_2", "say_hi"]
    assert source.startswith("flowchart LR\n")
    assert '  load_csv["Load CSV"]' in source
    assert "load_csv --> clean --> clean_2 --> say_hi" in source
    assert '"hi"' not in source  # quotes inside labels are replaced


def test_mermaid_node_ids_best_effort():
    src = textwrap.dedent(
        """
        flowchart TD
          %% a comment
          load[Load data] --> clean(Clean) --> feats{Features?}
          feats -->|yes| train[[Train]]
          train -- evaluate --> eval[(Evaluate)]
          subgraph infra [Infrastructure]
            db[(DB)] --x cache
          end
          api:::hot --> db
          classDef hot fill:#f00
          class api hot
          a1[One] --> b1[Two] --> c1>Flag] --> d1[Four]
        """
    )
    assert mermaid_node_ids(src) == [
        "load", "clean", "feats", "train", "eval", "infra", "db", "cache", "api", "a1", "b1", "c1", "d1",
    ]


def test_schema_from_input():
    s = SchemaSpec.from_input(["A", "B"])
    assert s.generated and s.nodes == ["a", "b"]
    m = SchemaSpec.from_input("graph LR\n a --> b")
    assert not m.generated and m.nodes == ["a", "b"]
    with pytest.raises(SpecError, match="Mermaid"):
        SchemaSpec.from_input("a --> b")
    with pytest.raises(SpecError):
        SchemaSpec.from_input([])


# ---------------------------------------------------------------- DSL


def test_step_defaults_and_ids():
    w = wt()
    s1 = w.step(at="run.py:5")
    s2 = w.step(at="run.py:6", title="Read the CSV")
    s3 = w.step(at="run.py:7", title="Read the CSV")
    assert [s.id for s in (s1, s2, s3)] == ["step-1", "read-the-csv", "read-the-csv-2"]
    assert [s.index for s in (s1, s2, s3)] == [1, 2, 3]
    assert s1.mode == "before" and s1.location.line == 5


def test_step_plot_highlight_and_text_normalisation():
    w = wt()
    s = w.step(
        at="run.py:5",
        plot="fig",
        show={"a": "a"},
        highlight="load",
        text="""
            Hello
              world
        """,
    )
    assert list(s.show) == ["plot", "a"]
    assert s.highlight == ["load"]
    assert s.text == "Hello\n  world"
    assert w.step(at="run.py:6", highlight=["a", "b"]).highlight == ["a", "b"]


def test_step_modes():
    w = wt()
    assert w.step(after="run.py:5").mode == "after"
    assert w.step(at="run.py::main", when="return").mode == "return"
    assert w.step(at="run.py::main").mode == "before"


@pytest.mark.parametrize(
    "kwargs, match",
    [
        ({}, "exactly one of at= or after="),
        ({"at": "run.py:1", "after": "run.py:2"}, "exactly one"),
        ({"after": "run.py::main"}, "after= needs"),
        ({"at": "run.py:3", "when": "return"}, "when='return' needs"),
        ({"at": "run.py:3", "hit": 0}, "hit= must be"),
        ({"at": "run.py:3", "hit": "some"}, "hit"),
        ({"at": "run.py:3", "show": {f"v{i}": "1" for i in range(7)}}, "6 or fewer"),
        ({"at": "run.py:3", "show": {"not an identifier": "1"}}, "identifier"),
        ({"at": "run.py:3", "show": {"x": ""}}, "non-empty"),
        ({"at": "run.py:3", "code": "run.py:9-1"}, "code="),
        ({"at": "run.py", "show": {}}, "expected"),
    ],
)
def test_step_validation_errors(kwargs, match):
    w = wt()
    with pytest.raises(SpecError, match=match) as info:
        w.step(**kwargs)
    assert str(info.value).startswith("step 1 (")


def test_unknown_kwarg_is_a_type_error():
    with pytest.raises(TypeError):
        wt().step(at="run.py:3", hilight="x")


def test_duplicate_step_id():
    w = wt()
    w.step(id="a", at="run.py:3")
    with pytest.raises(SpecError, match="duplicate"):
        w.step(id="a", at="run.py:4")


def test_walkthrough_validation():
    with pytest.raises(SpecError, match="title"):
        Walkthrough("", "run.py", STAGES, root=MINIPROJ)
    with pytest.raises(SpecError, match="timeout"):
        Walkthrough("T", "run.py", STAGES, root=MINIPROJ, timeout=0)
    w = Walkthrough("T", "run.py", STAGES, root=MINIPROJ, description="""
        Intro
    """)
    assert w.spec.description == "Intro"


# ---------------------------------------------------------------- loading files


def test_load_walkthrough_fixture():
    w = load_walkthrough(MINIPROJ / "walkthrough.py")
    assert w.title == "Mini project"
    assert w.spec.root == str(MINIPROJ)  # default root is the walkthrough's directory
    assert [s.id for s in w.steps] == ["load", "total", "score"]


def test_load_walkthrough_errors(tmp_path):
    empty = tmp_path / "w.py"
    empty.write_text("x = 1\n")
    with pytest.raises(SpecError, match="no Walkthrough"):
        load_walkthrough(empty)
    broken = tmp_path / "b.py"
    broken.write_text("import nonexistent_module_xyz\n")
    with pytest.raises(SpecError, match="failed to import"):
        load_walkthrough(broken)
    bad = tmp_path / "bad.py"
    bad.write_text("from codewalk import Walkthrough\nw = Walkthrough('T', 'run.py', ['A'])\nw.step()\n")
    with pytest.raises(SpecError, match="exactly one of"):
        load_walkthrough(bad)
    with pytest.raises(SpecError, match="not found"):
        load_walkthrough(tmp_path / "missing.py")


def test_load_walkthrough_picks_the_one_named_walkthrough(tmp_path):
    f = tmp_path / "two.py"
    f.write_text(
        "from codewalk import Walkthrough\n"
        "other = Walkthrough('Other', 'run.py', ['A'])\n"
        "walkthrough = Walkthrough('Main', 'run.py', ['A'])\n"
    )
    assert load_walkthrough(f).title == "Main"
    g = tmp_path / "three.py"
    g.write_text(
        "from codewalk import Walkthrough\n"
        "a = Walkthrough('A', 'run.py', ['A'])\n"
        "b = Walkthrough('B', 'run.py', ['A'])\n"
    )
    with pytest.raises(SpecError, match="2 Walkthrough instances"):
        load_walkthrough(g)
