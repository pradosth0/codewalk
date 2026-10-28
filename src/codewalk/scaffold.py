"""`codewalk init`: write a commented walkthrough.py that already passes `codewalk check`."""

from __future__ import annotations

import ast
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Union

from .errors import CodewalkError
from .pysource import find_function, parse_module

ENTRY_CANDIDATES = ("main.py", "run.py", "app.py", "cli.py", "train.py", "pipeline.py", "__main__.py")
SKIP_NAMES = {"walkthrough.py", "setup.py", "conftest.py", "noxfile.py", "tasks.py"}
SKIP_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__", "build", "dist", "out", "tests", "test", "docs"}

TEMPLATE = '''"""Walkthrough of %(project)s.

    codewalk check %(spec_name)s          # validate without running anything
    codewalk record %(spec_name)s -o out  # run once, write out/steps.json and out/index.html
    codewalk serve out --open            # read it; or codewalk screenshot out --all
"""

from codewalk import Walkthrough

walkthrough = Walkthrough(
    title="%(title)s",
    # What to run: "script.py --arg value" (run as __main__) or "package.module:function".
    entry="%(entry)s",
    # Paths in this file are relative to root, which defaults to this file's directory.
    # root="..",
    # The schema shown on top: Mermaid flowchart text, or a list of stage names such as
    # ["Load", "Clean", "Train"] (ids are then slugified: "Load CSV" -> load_csv).
    schema="""
    flowchart LR
      %(schema_body)s
    """,
    # Markdown shown before the first step: what the program does, what the reader will see.
    description="""
    %(description)s
    """,
)

# Each step pauses the program once and captures what you ask for. Exactly one location:
#   at="file.py:LINE"         pause before the line runs
#   after="file.py:LINE"      pause once the line has run (what it assigned is visible)
#   at="file.py::function"    pause on function entry; add when="return" to see `__return__`
# Loops: hit=N captures the Nth time the location is reached, hit="all" every time (max_hits=10),
# condition="i == 3" counts only hits where the expression is true. Keep show to 2-4 objects.
walkthrough.step(
    id="start",
    title="%(first_title)s",
    at="%(first_at)s",
    highlight="%(first_node)s",
    # code="%(entry_file)s::main",             # left pane; default: the enclosing function
    # focus="%(entry_file)s:10-14",             # lines to emphasise within the code pane
    # show={"df": "df.head()", "shape": "df.shape"},   # name -> expression evaluated in the paused frame
    # plot="plot_loss(history)",               # a matplotlib Figure/Axes, PIL image or image array
    # In text, {{name}} inserts the text form of the show= value called name.
    text="""
    What happens here and why it matters, and which tab in the objects pane to look at.
    """,
)
'''


@dataclass
class Scaffold:
    path: Path
    entry: str
    hints: list[str] = field(default_factory=list)


def _module_files(root: Path, limit: int = 12) -> list[str]:
    found: list[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS and not d.startswith("."))
        for name in sorted(filenames):
            if name.endswith(".py") and name not in SKIP_NAMES and name != "__init__.py":
                found.append(Path(dirpath, name).relative_to(root).as_posix())
                if len(found) >= limit:
                    return found
    return found


def _looks_like_entry(path: Path) -> bool:
    try:
        tree = parse_module(str(path))
    except (SyntaxError, OSError):
        return False
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and isinstance(node.left, ast.Name) and node.left.id == "__name__":
            return True
    return False


def detect_entry(root: Path) -> Optional[str]:
    """A top-level script that checks `__name__`, preferring conventional names."""
    for name in ENTRY_CANDIDATES:
        candidate = root / name
        if candidate.is_file() and _looks_like_entry(candidate):
            return name
    scripts = [p for p in sorted(root.glob("*.py")) if p.name not in SKIP_NAMES and _looks_like_entry(p)]
    if scripts:
        return scripts[0].name
    return None


def _first_location(root: Path, entry: str) -> tuple[str, str]:
    """`at=` for the first step and its title: `main` if the entry defines it, else the first statement."""
    script = entry.split()[0]
    path = root / script
    if not script.endswith(".py") or not path.is_file():
        return f"{script}:1", "Start"
    try:
        find_function(str(path), "main")
        return f"{script}::main", "Enter main()"
    except Exception:
        pass
    try:
        tree = parse_module(str(path))
    except (SyntaxError, OSError):
        return f"{script}:1", "Start"
    for node in tree.body:
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            continue  # module docstring
        return f"{script}:{node.lineno}", "Start"
    return f"{script}:1", "Start"


def write_scaffold(
    directory: Union[str, os.PathLike] = ".",
    *,
    entry: Optional[str] = None,
    out: Union[str, os.PathLike, None] = None,
    force: bool = False,
) -> Scaffold:
    root = Path(directory).resolve()
    if not root.is_dir():
        raise CodewalkError(f"{root} is not a directory")
    target = Path(out) if out is not None else root / "walkthrough.py"
    if target.exists() and not force:
        raise CodewalkError(f"{target} already exists; pass --force to overwrite it")

    hints: list[str] = []
    detected = detect_entry(root)
    if entry is None:
        if detected is None:
            entry = "main.py"
            hints.append("no entry script found: set entry= to the script or module:function to run")
        else:
            entry = detected
    elif not (root / entry.split()[0]).exists() and ":" not in entry:
        hints.append(f"entry {entry.split()[0]!r} does not exist under {root}")
    modules = _module_files(root)
    if modules:
        hints.append("modules found: " + ", ".join(modules))

    first_at, first_title = _first_location(root, entry)
    project = root.name or "the project"
    page = TEMPLATE % {
        "project": project,
        "spec_name": target.name if target.parent == root else target.as_posix(),
        "title": f"How {project} works",
        "entry": entry,
        "entry_file": entry.split()[0] if entry.split()[0].endswith(".py") else "main.py",
        "schema_body": "start[Start] --> work[Work] --> finish[Finish]",
        "description": f"What `{entry.split()[0]}` does, in one paragraph, and what this walkthrough shows.",
        "first_title": first_title,
        "first_at": first_at,
        "first_node": "start",
    }
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(page, encoding="utf-8")
    return Scaffold(path=target, entry=entry, hints=hints)
