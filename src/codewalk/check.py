"""Static validation of a walkthrough: resolve files, lines, functions, expressions, schema ids."""

from __future__ import annotations

import ast
import os
from dataclasses import dataclass, field
from typing import Literal, Optional

from .errors import SpecError
from .pysource import (
    enclosing_function,
    executable_lines,
    find_function,
    function_entry_line,
    function_range,
    is_blank_or_comment,
    read_lines,
)
from .spec import PLACEHOLDER_RE, CodeRange, StepSpec, WalkthroughSpec

CONTEXT_LINES = 15


@dataclass
class Problem:
    level: Literal["error", "warning"]
    message: str
    step_id: Optional[str] = None

    def __str__(self) -> str:
        where = f" step '{self.step_id}':" if self.step_id else ""
        return f"{self.level}:{where} {self.message}"


@dataclass
class ResolvedStep:
    spec: StepSpec
    index: int
    path: str  # real absolute path of the file with the breakpoint
    rel_file: str  # display path, relative to root when inside it
    break_line: int
    mode: Literal["before", "after", "return"]
    function: Optional[str]
    code_path: str
    code_rel_file: str
    code_start: int
    code_end: int
    focus: list[tuple[int, int]] = field(default_factory=list)

    @property
    def location_text(self) -> str:
        return f"{self.rel_file}:{self.break_line}"


@dataclass
class ResolvedWalkthrough:
    spec: WalkthroughSpec
    root: str
    steps: list[ResolvedStep]


@dataclass
class Report:
    errors: list[Problem]
    warnings: list[Problem]
    resolved: Optional[ResolvedWalkthrough]

    @property
    def ok(self) -> bool:
        return not self.errors

    def problems(self) -> list[Problem]:
        return [*self.errors, *self.warnings]


def _abs(root: str, file: str) -> str:
    return os.path.abspath(os.path.join(root, file))


def _rel(root: str, path: str) -> str:
    root_abs = os.path.abspath(root)
    if path == root_abs or path.startswith(root_abs + os.sep):
        return os.path.relpath(path, root_abs).replace(os.sep, "/")
    return path.replace(os.sep, "/")


def _check_expression(expr: str, what: str) -> Optional[str]:
    try:
        ast.parse(expr.strip(), mode="eval")
    except SyntaxError as e:
        return f"{what} = {expr!r} is not a valid expression: {e.msg}"
    return None


def _resolve_range(root: str, cr: CodeRange, field_name: str) -> tuple[str, int, int]:
    path = _abs(root, cr.file)
    if not os.path.isfile(path):
        raise SpecError(f"{field_name}: file not found: {cr.file}")
    n_lines = len(read_lines(path))
    if cr.function is not None:
        _qual, node = find_function(path, cr.function)
        start, end = function_range(node)
        return path, start, end
    start, end = cr.start or 1, cr.end or 1
    if end > n_lines:
        raise SpecError(f"{field_name}: {cr.file}:{start}-{end} goes past the end of the file ({n_lines} lines)")
    return path, start, end


def _resolve_step(
    spec: WalkthroughSpec,
    step: StepSpec,
    errors: list[Problem],
    warnings: list[Problem],
) -> Optional[ResolvedStep]:
    root = spec.root
    nodes = spec.diagram.nodes
    ok = True

    def err(msg: str) -> None:
        nonlocal ok
        ok = False
        errors.append(Problem("error", msg, step.id))

    def warn(msg: str) -> None:
        warnings.append(Problem("warning", msg, step.id))

    # breakpoint location
    loc = step.location
    path = _abs(root, loc.file)
    break_line: Optional[int] = None
    function: Optional[str] = None
    if not os.path.isfile(path):
        err(f"file not found: {loc.file} (looked under {root})")
    else:
        lines = read_lines(path)
        if loc.function is not None:
            try:
                function, node = find_function(path, loc.function)
                break_line = function_entry_line(node)
            except SpecError as e:
                err(str(e))
            except SyntaxError as e:
                err(f"{loc.file} does not parse: {e}")
        else:
            line = loc.line or 0
            if line > len(lines):
                err(f"{loc.file}:{line} is past the end of the file ({len(lines)} lines)")
            elif is_blank_or_comment(lines[line - 1]):
                err(f"{loc.file}:{line} is blank or a comment; a breakpoint there never fires")
            else:
                break_line = line
                try:
                    if line not in executable_lines(path):
                        warn(
                            f"{loc.file}:{line} carries no bytecode (part of a multi-line statement, "
                            "an 'else:' line, ...); the breakpoint will probably never fire"
                        )
                except SyntaxError as e:
                    err(f"{loc.file} does not parse: {e}")
            if break_line is not None:
                enclosing = enclosing_function(path, break_line)
                function = enclosing[0] if enclosing else None

    # code pane range
    code_path, code_start, code_end = path, 1, 1
    if step.code is not None:
        try:
            cr = CodeRange.parse(step.code, field="code")
            code_path, code_start, code_end = _resolve_range(root, cr, "code")
        except SpecError as e:
            err(str(e))
    elif break_line is not None and os.path.isfile(path):
        enclosing = enclosing_function(path, break_line)
        if enclosing:
            code_start, code_end = function_range(enclosing[1])
        else:
            n_lines = len(read_lines(path))
            code_start = max(1, break_line - CONTEXT_LINES)
            code_end = min(n_lines, break_line + CONTEXT_LINES)

    focus: list[tuple[int, int]] = []
    if step.focus is not None:
        try:
            fr = CodeRange.parse(step.focus, field="focus")
            f_path, f_start, f_end = _resolve_range(root, fr, "focus")
            if os.path.realpath(f_path) != os.path.realpath(code_path):
                warn(f"focus= points at {fr.file} but the code pane shows {_rel(root, code_path)}; focus ignored")
            else:
                focus.append((f_start, f_end))
        except SpecError as e:
            err(str(e))

    # expressions
    for name, expr in step.show.items():
        problem = _check_expression(expr, f"show[{name!r}]")
        if problem:
            err(problem)
    if step.condition is not None:
        problem = _check_expression(step.condition, "condition")
        if problem:
            err(problem)

    # schema ids
    for node_id in step.highlight:
        if nodes and node_id not in nodes:
            msg = f"highlight={node_id!r} is not a node of the schema (known: {', '.join(nodes)})"
            if spec.diagram.generated:
                err(msg)
            else:
                warn(msg + "; node ids are extracted heuristically, check the viewer")

    # placeholders
    for name in PLACEHOLDER_RE.findall(step.text):
        if name not in step.show:
            warn(f"text mentions {{{{{name}}}}} but show= has no entry named {name!r}; it will be left as is")

    if not ok or break_line is None:
        return None
    return ResolvedStep(
        spec=step,
        index=step.index,
        path=os.path.realpath(path),
        rel_file=_rel(root, path),
        break_line=break_line,
        mode=step.mode,
        function=function,
        code_path=os.path.realpath(code_path),
        code_rel_file=_rel(root, code_path),
        code_start=code_start,
        code_end=code_end,
        focus=focus,
    )


def analyze(spec: WalkthroughSpec) -> Report:
    """Resolve every step against the filesystem and report errors and warnings."""
    errors: list[Problem] = []
    warnings: list[Problem] = []
    root = spec.root
    if not os.path.isdir(root):
        errors.append(Problem("error", f"root {root!r} is not a directory"))
        return Report(errors, warnings, None)

    entry = spec.entry
    if entry.kind == "script":
        script = _abs(root, entry.target)
        if not os.path.isfile(script):
            errors.append(Problem("error", f"entry script {entry.target!r} not found under {root}"))
    else:
        module_rel = (entry.module or "").replace(".", os.sep)
        if not (
            os.path.isfile(os.path.join(root, module_rel + ".py"))
            or os.path.isfile(os.path.join(root, module_rel, "__init__.py"))
        ):
            warnings.append(
                Problem(
                    "warning",
                    f"entry module {entry.module!r} was not found under {root}; "
                    "it must be importable in the recording environment",
                )
            )

    if not spec.diagram.nodes:
        warnings.append(Problem("warning", "no node ids were found in the schema; highlight= cannot be checked"))
    if not spec.steps:
        warnings.append(Problem("warning", "the walkthrough has no steps"))

    resolved_steps: list[ResolvedStep] = []
    for step in spec.steps:
        rs = _resolve_step(spec, step, errors, warnings)
        if rs is not None:
            resolved_steps.append(rs)

    resolved = ResolvedWalkthrough(spec=spec, root=root, steps=resolved_steps) if not errors else None
    return Report(errors=errors, warnings=warnings, resolved=resolved)
