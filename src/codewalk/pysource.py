"""Helpers for looking at Python source files: functions, ranges, executable lines."""

from __future__ import annotations

import ast
import functools
import types
from typing import Optional, Union

from .errors import SpecError

FunctionNode = Union[ast.FunctionDef, ast.AsyncFunctionDef]


@functools.lru_cache(maxsize=256)
def read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def read_lines(path: str) -> list[str]:
    return read_text(path).splitlines()


@functools.lru_cache(maxsize=256)
def parse_module(path: str) -> ast.Module:
    return ast.parse(read_text(path), filename=path)


def clear_caches() -> None:
    read_text.cache_clear()
    parse_module.cache_clear()
    executable_lines.cache_clear()


def _definitions(tree: ast.AST) -> list[tuple[str, FunctionNode]]:
    """All function definitions in a module with their qualified names (Class.method, outer.inner)."""
    out: list[tuple[str, FunctionNode]] = []

    def visit(node: ast.AST, prefix: str) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                qual = f"{prefix}.{child.name}" if prefix else child.name
                if not isinstance(child, ast.ClassDef):
                    out.append((qual, child))
                visit(child, qual)
            else:
                visit(child, prefix)

    visit(tree, "")
    return out


def find_function(path: str, name: str) -> tuple[str, FunctionNode]:
    """Find a function by name or dotted qualified name. Returns (qualified name, node)."""
    defs = _definitions(parse_module(path))
    exact = [d for d in defs if d[0] == name]
    if exact:
        return exact[-1]  # a redefinition wins at runtime, mirror that
    suffix = [d for d in defs if d[0].endswith("." + name)]
    if len(suffix) == 1:
        return suffix[0]
    if len(suffix) > 1:
        names = ", ".join(d[0] for d in suffix)
        raise SpecError(f"{name!r} is ambiguous in {path}; use one of: {names}")
    available = ", ".join(d[0] for d in defs) or "none"
    raise SpecError(f"no function {name!r} in {path}; available: {available}")


def function_entry_line(node: FunctionNode) -> int:
    """First executable line of a function body (skips a docstring)."""
    body = node.body
    first = body[0]
    if (
        isinstance(first, ast.Expr)
        and isinstance(first.value, ast.Constant)
        and isinstance(first.value.value, str)
        and len(body) > 1
    ):
        first = body[1]
    return first.lineno


def function_range(node: FunctionNode) -> tuple[int, int]:
    start = node.lineno
    if node.decorator_list:
        start = min(start, min(d.lineno for d in node.decorator_list))
    return start, node.end_lineno or node.lineno


def enclosing_function(path: str, line: int) -> Optional[tuple[str, FunctionNode]]:
    """Innermost function whose source range contains `line`."""
    best: Optional[tuple[str, FunctionNode]] = None
    best_size = None
    for qual, node in _definitions(parse_module(path)):
        start, end = function_range(node)
        if start <= line <= end:
            size = end - start
            if best_size is None or size < best_size:
                best, best_size = (qual, node), size
    return best


@functools.lru_cache(maxsize=256)
def executable_lines(path: str) -> frozenset[int]:
    """Line numbers that carry bytecode, i.e. where a line breakpoint can fire."""
    code = compile(read_text(path), path, "exec")
    out: set[int] = set()
    stack = [code]
    while stack:
        c = stack.pop()
        for _start, _end, lineno in c.co_lines():
            if lineno is not None:
                out.add(lineno)
        for const in c.co_consts:
            if isinstance(const, types.CodeType):
                stack.append(const)
    return frozenset(out)


def is_blank_or_comment(line_text: str) -> bool:
    stripped = line_text.strip()
    return not stripped or stripped.startswith("#")
