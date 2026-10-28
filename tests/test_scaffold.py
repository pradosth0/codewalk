from __future__ import annotations

import textwrap

from typer.testing import CliRunner

from codewalk.cli import app
from codewalk.scaffold import detect_entry, write_scaffold

runner = CliRunner()


def make_project(tmp_path, entry_name="main.py", with_main=True):
    body = "def main():\n    x = 1\n    print(x)\n\n\nif __name__ == '__main__':\n    main()\n" if with_main else "import sys\nprint(sys.argv)\n"
    (tmp_path / entry_name).write_text(body)
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "__init__.py").write_text("")
    (tmp_path / "pkg" / "work.py").write_text("def work():\n    return 1\n")
    return tmp_path


def test_init_detects_entry_and_passes_check(tmp_path):
    make_project(tmp_path, "run.py")
    (tmp_path / "helper.py").write_text("x = 1\n")  # no __main__ check: not an entry
    assert detect_entry(tmp_path) == "run.py"
    result = runner.invoke(app, ["init", str(tmp_path)])
    assert result.exit_code == 0, result.output
    spec = tmp_path / "walkthrough.py"
    assert spec.is_file()
    assert "wrote" in result.output and "(entry: run.py)" in result.output
    assert "modules found: helper.py, run.py, pkg/work.py" in result.output
    text = spec.read_text()
    assert 'entry="run.py"' in text and 'at="run.py::main"' in text
    check = runner.invoke(app, ["check", str(spec)])
    assert check.exit_code == 0, check.output
    assert "ok: 1 step(s), 0 warning(s)" in check.output


def test_init_without_main_uses_first_statement(tmp_path):
    make_project(tmp_path, "script.py", with_main=False)
    (tmp_path / "script.py").write_text('"""doc"""\n\nimport sys\n\nif __name__ == "__main__":\n    print(sys.argv)\n')
    result = write_scaffold(tmp_path)
    assert result.entry == "script.py"
    assert 'at="script.py:3"' in result.path.read_text()
    check = runner.invoke(app, ["check", str(result.path)])
    assert check.exit_code == 0, check.output


def test_init_explicit_entry_refuses_overwrite_unless_forced(tmp_path):
    make_project(tmp_path)
    result = runner.invoke(app, ["init", str(tmp_path), "--entry", "pkg.work:work", "-o", str(tmp_path / "walks" / "w.py")])
    assert result.exit_code == 0, result.output
    spec = tmp_path / "walks" / "w.py"
    assert 'entry="pkg.work:work"' in spec.read_text()
    again = runner.invoke(app, ["init", str(tmp_path), "-o", str(spec)])
    assert again.exit_code == 1 and "already exists" in again.output
    forced = runner.invoke(app, ["init", str(tmp_path), "-o", str(spec), "--force"])
    assert forced.exit_code == 0, forced.output
    assert 'entry="main.py"' in spec.read_text()


def test_init_with_nothing_to_run_still_writes_a_hint(tmp_path):
    (tmp_path / "lib.py").write_text("def f():\n    return 1\n")
    result = runner.invoke(app, ["init", str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert "hint: no entry script found" in result.output
    assert 'entry="main.py"' in (tmp_path / "walkthrough.py").read_text()
