"""The authoring DSL (`Walkthrough`, `step()`) and the validated models behind it."""

from __future__ import annotations

import importlib.util
import os
import re
import shlex
import sys
import textwrap
from typing import Any, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from .errors import SpecError

__all__ = [
    "Walkthrough",
    "WalkthroughSpec",
    "StepSpec",
    "Location",
    "CodeRange",
    "Entry",
    "SchemaSpec",
    "load_walkthrough",
    "slugify",
    "PLACEHOLDER_RE",
    "MAX_SHOW",
]

MAX_SHOW = 6
PLACEHOLDER_RE = re.compile(r"\{\{\s*([A-Za-z_][A-Za-z0-9_]*)\s*\}\}")

_LOC_FUNC = re.compile(r"^(?P<file>.+?)::(?P<func>[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*)$")
_LOC_RANGE = re.compile(r"^(?P<file>.+):(?P<start>\d+)-(?P<end>\d+)$")
_LOC_LINE = re.compile(r"^(?P<file>.+):(?P<line>\d+)$")
_CALLABLE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*:[A-Za-z_][A-Za-z0-9_]*$")
_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s or "step"


def _format_validation_error(exc: ValidationError) -> str:
    parts = []
    for err in exc.errors():
        loc = ".".join(str(x) for x in err["loc"]) or "value"
        parts.append(f"{loc}: {err['msg']}")
    return "; ".join(parts)


# --------------------------------------------------------------------------- locations


class Location(BaseModel):
    """A parsed `file:LINE` or `file::function` reference (not yet checked against disk)."""

    model_config = ConfigDict(frozen=True)

    file: str
    line: Optional[int] = None
    function: Optional[str] = None

    @classmethod
    def parse(cls, text: str, *, field: str) -> "Location":
        text = text.strip()
        m = _LOC_FUNC.match(text)
        if m:
            return cls(file=m["file"], function=m["func"])
        m = _LOC_LINE.match(text)
        if m:
            line = int(m["line"])
            if line < 1:
                raise SpecError(f"{field}={text!r}: line numbers start at 1")
            return cls(file=m["file"], line=line)
        raise SpecError(
            f"{field}={text!r}: expected 'path/to/file.py:LINE' or 'path/to/file.py::function'"
        )

    def __str__(self) -> str:
        if self.function is not None:
            return f"{self.file}::{self.function}"
        return f"{self.file}:{self.line}"


class CodeRange(BaseModel):
    """A parsed `file:START-END`, `file:LINE` or `file::function` reference."""

    model_config = ConfigDict(frozen=True)

    file: str
    start: Optional[int] = None
    end: Optional[int] = None
    function: Optional[str] = None

    @classmethod
    def parse(cls, text: str, *, field: str) -> "CodeRange":
        text = text.strip()
        m = _LOC_FUNC.match(text)
        if m:
            return cls(file=m["file"], function=m["func"])
        m = _LOC_RANGE.match(text)
        if m:
            start, end = int(m["start"]), int(m["end"])
            if start < 1 or end < start:
                raise SpecError(f"{field}={text!r}: need 1 <= START <= END")
            return cls(file=m["file"], start=start, end=end)
        m = _LOC_LINE.match(text)
        if m:
            line = int(m["line"])
            if line < 1:
                raise SpecError(f"{field}={text!r}: line numbers start at 1")
            return cls(file=m["file"], start=line, end=line)
        raise SpecError(
            f"{field}={text!r}: expected 'file.py:START-END', 'file.py:LINE' or 'file.py::function'"
        )


# --------------------------------------------------------------------------- entry


class Entry(BaseModel):
    """What to run: a script with arguments, or an importable callable."""

    model_config = ConfigDict(frozen=True)

    kind: Literal["script", "callable"]
    target: str
    args: list[str] = []
    text: str

    @classmethod
    def parse(cls, text: str) -> "Entry":
        try:
            parts = shlex.split(text)
        except ValueError as e:
            raise SpecError(f"entry={text!r}: {e}") from None
        if not parts:
            raise SpecError("entry= must not be empty")
        first, args = parts[0], parts[1:]
        if _CALLABLE.match(first) and not first.endswith(".py"):
            return cls(kind="callable", target=first, args=args, text=text)
        if first.endswith(".py"):
            return cls(kind="script", target=first, args=args, text=text)
        raise SpecError(
            f"entry={text!r}: expected a .py script with optional arguments "
            "(e.g. 'run.py --rows 100') or 'package.module:function'"
        )

    @property
    def module(self) -> Optional[str]:
        return self.target.split(":")[0] if self.kind == "callable" else None

    @property
    def function(self) -> Optional[str]:
        return self.target.split(":")[1] if self.kind == "callable" else None


# --------------------------------------------------------------------------- schema

_MERMAID_HEADER = re.compile(r"^\s*(flowchart|graph)\b", re.I)
_MERMAID_SKIP_PREFIXES = ("classDef", "class ", "style ", "linkStyle", "click ", "%%", "direction ")
_MERMAID_LABELS = [
    re.compile(r'"[^"]*"'),
    re.compile(r"\(\([^)]*\)\)"),
    re.compile(r"\[\[[^\]]*\]\]"),
    re.compile(r"\[\([^\]]*\)\]"),
    re.compile(r"\(\[[^\]]*\]\)"),
    re.compile(r"\[/[^\]]*/\]"),
    re.compile(r"\[\\[^\]]*\\\]"),
    re.compile(r"\{\{[^}]*\}\}"),
    re.compile(r"(?<=[A-Za-z0-9_])>[^\]]*\]"),  # id>Label] (asymmetric shape), not the > of an arrow
    re.compile(r"\[[^\]]*\]"),
    re.compile(r"\([^)]*\)"),
    re.compile(r"\{[^}]*\}"),
    re.compile(r"\|[^|]*\|"),
]
_MERMAID_EDGE_TEXT = [
    re.compile(r"--\s[^-]*?\s-->"),
    re.compile(r"==\s[^=]*?\s==>"),
    re.compile(r"-\.\s[^.]*?\s\.->"),
]
_MERMAID_ARROW_END = re.compile(r"-{2,}[xo](?![A-Za-z0-9_])")
_MERMAID_TOKEN = re.compile(r"[A-Za-z0-9_]+")


def mermaid_node_ids(source: str) -> list[str]:
    """Best-effort extraction of node ids from a Mermaid flowchart. The viewer is the ground truth."""
    ids: list[str] = []
    seen: set[str] = set()

    def add(token: str) -> None:
        if token not in seen:
            seen.add(token)
            ids.append(token)

    for raw in source.splitlines():
        line = raw.strip()
        if not line or _MERMAID_HEADER.match(line) or line == "end":
            continue
        if any(line.startswith(p) for p in _MERMAID_SKIP_PREFIXES):
            continue
        if line.startswith("subgraph"):
            rest = line[len("subgraph"):].strip()
            m = _MERMAID_TOKEN.match(rest)
            if m:
                add(m.group(0))
            continue
        for pat in _MERMAID_EDGE_TEXT:
            line = pat.sub(" --> ", line)
        for pat in _MERMAID_LABELS:
            line = pat.sub(" ", line)
        line = _MERMAID_ARROW_END.sub(" ", line)
        line = re.sub(r":::[A-Za-z0-9_-]+", " ", line)
        line = re.sub(r"[-=.<>|&]+", " ", line)
        for token in _MERMAID_TOKEN.findall(line):
            add(token)
    return ids


def _stage_id(label: str, taken: set[str]) -> str:
    base = re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")
    if not base or not base[0].isalpha():
        base = "s_" + base
    candidate, n = base, 2
    while candidate in taken:
        candidate = f"{base}_{n}"
        n += 1
    return candidate


def stages_to_mermaid(stages: list[str]) -> tuple[str, list[str]]:
    ids: list[str] = []
    lines = ["flowchart LR"]
    for label in stages:
        node_id = _stage_id(str(label), set(ids))
        ids.append(node_id)
        safe_label = str(label).replace('"', "'")
        lines.append(f'  {node_id}["{safe_label}"]')
    if len(ids) > 1:
        lines.append("  " + " --> ".join(ids))
    return "\n".join(lines) + "\n", ids


class SchemaSpec(BaseModel):
    """The project schema shown on top of the viewer."""

    model_config = ConfigDict(frozen=True)

    kind: Literal["mermaid"] = "mermaid"
    source: str
    nodes: list[str]
    generated: bool = False  # True when built from a stage list, so node ids are exact

    @classmethod
    def from_input(cls, value: Any) -> "SchemaSpec":
        if isinstance(value, str):
            source = textwrap.dedent(value).strip()
            if not source:
                raise SpecError("schema= must not be empty")
            if not _MERMAID_HEADER.match(source):
                raise SpecError(
                    "schema= must be a Mermaid flowchart (start with 'flowchart LR' / 'graph TD') "
                    "or a list of stage names"
                )
            return cls(source=source + "\n", nodes=mermaid_node_ids(source))
        if isinstance(value, (list, tuple)):
            if not value:
                raise SpecError("schema= stage list must not be empty")
            source, ids = stages_to_mermaid([str(v) for v in value])
            return cls(source=source, nodes=ids, generated=True)
        raise SpecError("schema= must be Mermaid text or a list of stage names")


# --------------------------------------------------------------------------- steps


class StepSpec(BaseModel):
    """One breakpoint and what to show there. Built by `Walkthrough.step()`."""

    model_config = ConfigDict(extra="forbid")

    id: str
    index: int = Field(ge=1)
    title: Optional[str] = None
    at: Optional[str] = None
    after: Optional[str] = None
    when: Literal["line", "return"] = "line"
    hit: Union[int, Literal["all"]] = 1
    max_hits: int = Field(default=10, ge=1)
    condition: Optional[str] = None
    highlight: list[str] = []
    code: Optional[str] = None
    focus: Optional[str] = None
    show: dict[str, str] = {}
    text: str = ""

    @model_validator(mode="after")
    def _validate(self) -> "StepSpec":
        if (self.at is None) == (self.after is None):
            raise SpecError("give exactly one of at= or after=")
        loc = self.location
        if self.after is not None and loc.function is not None:
            raise SpecError(
                "after= needs 'file.py:LINE'; use at='file.py::function' to pause at a function's entry"
            )
        if self.when == "return" and loc.function is None:
            raise SpecError("when='return' needs at='file.py::function'")
        if isinstance(self.hit, bool) or (isinstance(self.hit, int) and self.hit < 1):
            raise SpecError("hit= must be an integer >= 1 or 'all'")
        if len(self.show) > MAX_SHOW:
            raise SpecError(
                f"show= has {len(self.show)} entries; keep it to {MAX_SHOW} or fewer so the objects pane stays readable"
            )
        for name, expr in self.show.items():
            if not _IDENT.match(name):
                raise SpecError(f"show= name {name!r} must be a plain identifier")
            if not isinstance(expr, str) or not expr.strip():
                raise SpecError(f"show[{name!r}] must be a non-empty expression string")
        if self.condition is not None and not self.condition.strip():
            raise SpecError("condition= must not be empty")
        if self.code is not None:
            CodeRange.parse(self.code, field="code")
        if self.focus is not None:
            CodeRange.parse(self.focus, field="focus")
        return self

    @property
    def location(self) -> Location:
        if self.at is not None:
            return Location.parse(self.at, field="at")
        return Location.parse(self.after or "", field="after")

    @property
    def mode(self) -> Literal["before", "after", "return"]:
        if self.after is not None:
            return "after"
        if self.when == "return":
            return "return"
        return "before"


class WalkthroughSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1)
    description: str = ""
    entry: Entry
    diagram: SchemaSpec
    root: str
    env: dict[str, str] = {}
    timeout: float = Field(default=600.0, gt=0)
    steps: list[StepSpec] = []

    def step_by_id(self, step_id: str) -> Optional[StepSpec]:
        for s in self.steps:
            if s.id == step_id:
                return s
        return None


# --------------------------------------------------------------------------- DSL


def _caller_dir(depth: int = 2) -> str:
    frame = sys._getframe(depth)
    filename = frame.f_code.co_filename
    if filename and not filename.startswith("<") and os.path.isfile(filename):
        return os.path.dirname(os.path.abspath(filename))
    return os.getcwd()


class Walkthrough:
    """Describe a walkthrough: what to run, the project schema, and the steps.

    Define exactly one module-level instance in your `walkthrough.py`.
    """

    def __init__(
        self,
        title: str,
        entry: str,
        schema: Union[str, list[str]],
        *,
        description: str = "",
        root: Union[str, os.PathLike, None] = None,
        env: Optional[dict[str, str]] = None,
        timeout: float = 600.0,
    ) -> None:
        entry_spec = Entry.parse(entry)
        schema_spec = SchemaSpec.from_input(schema)
        caller_dir = _caller_dir()
        # A relative root is taken from the walkthrough file's directory, not the current directory,
        # so `root=".."` means the same thing wherever `codewalk record` is run from.
        root_dir = os.path.abspath(os.path.join(caller_dir, os.fspath(root))) if root is not None else caller_dir
        try:
            self._spec = WalkthroughSpec(
                title=title,
                description=textwrap.dedent(description).strip(),
                entry=entry_spec,
                diagram=schema_spec,
                root=root_dir,
                env=dict(env or {}),
                timeout=timeout,
                steps=[],
            )
        except ValidationError as e:
            raise SpecError(_format_validation_error(e)) from None

    @property
    def spec(self) -> WalkthroughSpec:
        return self._spec

    @property
    def title(self) -> str:
        return self._spec.title

    @property
    def steps(self) -> list[StepSpec]:
        return self._spec.steps

    def step(
        self,
        *,
        at: Optional[str] = None,
        after: Optional[str] = None,
        when: Literal["line", "return"] = "line",
        hit: Union[int, Literal["all"]] = 1,
        max_hits: int = 10,
        condition: Optional[str] = None,
        highlight: Union[str, list[str], None] = None,
        code: Optional[str] = None,
        focus: Optional[str] = None,
        show: Optional[dict[str, str]] = None,
        plot: Optional[str] = None,
        text: str = "",
        title: Optional[str] = None,
        id: Optional[str] = None,
    ) -> StepSpec:
        """Add a step. Pause `at="file.py:LINE"` (before the line runs), `after="file.py:LINE"`
        (once it has run), or `at="file.py::function"` (on entry; `when="return"` for its return)."""
        index = len(self._spec.steps) + 1
        show_items: dict[str, str] = {}
        if plot is not None:
            show_items["plot"] = plot
        show_items.update(show or {})
        if highlight is None:
            highlight_list: list[str] = []
        elif isinstance(highlight, str):
            highlight_list = [highlight]
        else:
            highlight_list = [str(h) for h in highlight]
        if id is None:
            base = slugify(title) if title else f"step-{index}"
            id, n = base, 2
            existing = {s.id for s in self._spec.steps}
            while id in existing:
                id = f"{base}-{n}"
                n += 1
        label = f"step {index} ({id})"
        try:
            step = StepSpec(
                id=id,
                index=index,
                title=title,
                at=at,
                after=after,
                when=when,
                hit=hit,
                max_hits=max_hits,
                condition=condition,
                highlight=highlight_list,
                code=code,
                focus=focus,
                show=show_items,
                text=textwrap.dedent(text).strip(),
            )
        except ValidationError as e:
            raise SpecError(f"{label}: {_format_validation_error(e)}") from None
        except SpecError as e:
            raise SpecError(f"{label}: {e}") from None
        if any(s.id == step.id for s in self._spec.steps):
            raise SpecError(f"{label}: duplicate step id {step.id!r}")
        self._spec.steps.append(step)
        return step


def load_walkthrough(path: Union[str, os.PathLike]) -> Walkthrough:
    """Import a walkthrough file and return the `Walkthrough` instance it defines."""
    path = os.path.abspath(os.fspath(path))
    if not os.path.isfile(path):
        raise SpecError(f"walkthrough file not found: {path}")
    module_name = "codewalk_walkthrough_" + re.sub(r"[^A-Za-z0-9_]", "_", os.path.basename(path))
    module_spec = importlib.util.spec_from_file_location(module_name, path)
    if module_spec is None or module_spec.loader is None:
        raise SpecError(f"cannot import walkthrough file: {path}")
    module = importlib.util.module_from_spec(module_spec)
    spec_dir = os.path.dirname(path)
    inserted = spec_dir not in sys.path
    if inserted:
        sys.path.insert(0, spec_dir)
    try:
        module_spec.loader.exec_module(module)
    except SpecError:
        raise
    except Exception as e:
        raise SpecError(f"{os.path.basename(path)} failed to import: {type(e).__name__}: {e}") from e
    finally:
        if inserted and spec_dir in sys.path:
            sys.path.remove(spec_dir)
    instances: list[Walkthrough] = []
    for value in vars(module).values():
        if isinstance(value, Walkthrough) and all(value is not w for w in instances):
            instances.append(value)
    if not instances:
        raise SpecError(f"{os.path.basename(path)} defines no Walkthrough instance")
    if len(instances) > 1:
        named = getattr(module, "walkthrough", None)
        if isinstance(named, Walkthrough):
            return named
        raise SpecError(
            f"{os.path.basename(path)} defines {len(instances)} Walkthrough instances; "
            "keep one, or name the main one `walkthrough`"
        )
    return instances[0]
