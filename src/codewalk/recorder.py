"""Run the target program under bdb and capture a step at every breakpoint."""

from __future__ import annotations

import bdb
import datetime as _dt
import importlib
import inspect
import io
import json
import os
import platform
import runpy
import sys
import time
import traceback
from dataclasses import dataclass
from typing import Any, Optional

from .check import Report, ResolvedStep, ResolvedWalkthrough, _rel, analyze
from .errors import CodewalkError
from .pysource import read_lines
from . import display as _helpers
from .serialize import apply_step_budget, error_display, plain_text, to_display
from .spec import PLACEHOLDER_RE, WalkthroughSpec

PAYLOAD_VERSION = 1
SUPPORTS_MONITORING = "backend" in inspect.signature(bdb.Bdb.__init__).parameters
_PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
_MISSING = object()


def default_backend() -> str:
    """'monitoring' (sys.monitoring, Python 3.14+ bdb) when available, else 'settrace'."""
    return "monitoring" if SUPPORTS_MONITORING else "settrace"


class _Tee(io.TextIOBase):
    """Pass writes through to the real stream and keep a copy for the step's console field."""

    def __init__(self, original: Any, sink: list[str]) -> None:
        self._original = original
        self._sink = sink

    def write(self, s: str) -> int:
        self._original.write(s)
        self._sink.append(s)
        return len(s)

    def flush(self) -> None:
        self._original.flush()

    def writable(self) -> bool:
        return True

    def readable(self) -> bool:
        return False

    def isatty(self) -> bool:
        return False

    @property
    def encoding(self) -> str:  # type: ignore[override]
        return getattr(self._original, "encoding", None) or "utf-8"

    def fileno(self) -> int:
        return self._original.fileno()


@dataclass
class _State:
    step: ResolvedStep
    counter: int = 0  # how often the location was hit (condition permitting)
    done: bool = False  # no more captures wanted
    captured: int = 0
    first_seq: Optional[int] = None  # position of the first recorded step for this spec step


@dataclass
class Recording:
    spec: WalkthroughSpec
    backend: str
    steps: list[dict]
    warnings: list[str]
    recorded_at: str
    duration: float
    crashed: bool = False

    def to_dict(self) -> dict:
        diagram = self.spec.diagram
        return {
            "version": PAYLOAD_VERSION,
            "title": self.spec.title,
            "description": self.spec.description,
            "entry": self.spec.entry.text,
            "recorded_at": self.recorded_at,
            "python": platform.python_version(),
            "backend": self.backend,
            "duration": round(self.duration, 4),
            "schema": {"kind": diagram.kind, "source": diagram.source, "nodes": list(diagram.nodes)},
            "warnings": list(self.warnings),
            "steps": self.steps,
        }

    def to_json(self, indent: Optional[int] = 1) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False, allow_nan=False)


class Recorder(bdb.Bdb):
    """A bdb debugger that never stops for a user: it captures and continues."""

    def __init__(self, resolved: ResolvedWalkthrough, *, backend: Optional[str] = None) -> None:
        backend = backend or default_backend()
        if backend not in ("settrace", "monitoring"):
            raise CodewalkError(f"unknown backend {backend!r}; use 'settrace' or 'monitoring'")
        if backend == "monitoring" and not SUPPORTS_MONITORING:
            raise CodewalkError("the 'monitoring' backend needs Python 3.14 or newer; use 'settrace'")
        if SUPPORTS_MONITORING:
            super().__init__(backend=backend)
        else:
            super().__init__()
        self.backend_name = backend
        self.resolved = resolved
        self.warnings: list[str] = []
        self._states = [_State(step) for step in resolved.steps]
        self._by_loc: dict[tuple[str, int], list[_State]] = {}
        # frame -> [(mode, state, hit number)] waiting for that frame's next line or return
        self._pending: dict[Any, list[tuple[str, _State, int]]] = {}
        self._steps: list[dict] = []
        self._sink: list[str] = []
        self._t0 = 0.0
        self._busy = False
        self._script = ""
        self._compiled: dict[tuple[str, str], Any] = {}
        self._conditions: dict[str, Any] = {}
        for state in self._states:
            spec = state.step.spec
            for name, expr in spec.show.items():
                self._compiled[(spec.id, name)] = compile(expr.strip(), f"<show {spec.id}.{name}>", "eval")
            if spec.condition is not None:
                self._conditions[spec.id] = compile(spec.condition.strip(), f"<condition {spec.id}>", "eval")

    # ------------------------------------------------------------------ bdb plumbing

    def canonic(self, filename: str) -> str:
        # Like bdb's, but symlink-proof, so a module imported through another path still matches.
        if filename.startswith("<") and filename.endswith(">"):
            return filename
        cached = self.fncache.get(filename)
        if cached is None:
            cached = os.path.normcase(os.path.realpath(os.path.abspath(filename)))
            self.fncache[filename] = cached
        return cached

    def _install_breaks(self) -> None:
        for state in self._states:
            key = (self.canonic(state.step.path), state.step.break_line)
            if key not in self._by_loc:
                error = self.set_break(state.step.path, state.step.break_line)
                if error:
                    raise CodewalkError(error)
            self._by_loc.setdefault(key, []).append(state)

    def user_line(self, frame: Any) -> None:
        if self._busy:
            return
        pending = self._pending.get(frame)
        if pending:
            remaining = []
            for mode, state, hitno in pending:
                if mode == "after":
                    self._capture(state, frame, hitno)
                else:
                    remaining.append((mode, state, hitno))
            if remaining:
                self._pending[frame] = remaining
            else:
                del self._pending[frame]
        if self.break_here(frame):
            self._on_break(frame)
        self._resume()

    def user_return(self, frame: Any, return_value: Any) -> None:
        if self._busy:
            return
        pending = self._pending.pop(frame, None)
        if pending:
            for mode, state, hitno in pending:
                if mode == "after":
                    self._capture(state, frame, hitno)
                else:
                    self._capture(state, frame, hitno, return_value=return_value)
        self._resume()

    def _resume(self) -> None:
        """Continue, but keep bdb stepping for the most recently armed pending frame."""
        if not self._pending:
            self.set_continue()
            return
        frame, entries = next(reversed(self._pending.items()))
        if any(mode == "after" for mode, _, _ in entries):
            self.set_next(frame)  # next line in that frame, or its return
        else:
            self.set_return(frame)

    def _on_break(self, frame: Any) -> None:
        key = (self.canonic(frame.f_code.co_filename), frame.f_lineno)
        states = self._by_loc.get(key)
        if not states:
            return
        for state in states:
            if state.done:
                continue
            spec = state.step.spec
            condition = self._conditions.get(spec.id)
            if condition is not None:
                self._busy = True
                try:
                    ok = bool(eval(condition, frame.f_globals, dict(frame.f_locals)))
                except Exception as e:
                    ok = False
                    self._warn(
                        f"step '{spec.id}': condition {spec.condition!r} raised "
                        f"{type(e).__name__}: {e}; treated as false"
                    )
                finally:
                    self._busy = False
                if not ok:
                    continue
            state.counter += 1
            n = state.counter
            if spec.hit == "all":
                take = n <= spec.max_hits
                state.done = n >= spec.max_hits
            else:
                take = n == spec.hit
                state.done = n >= spec.hit
            if not take:
                continue
            if state.step.mode == "before":
                self._capture(state, frame, n)
            else:
                self._pending.setdefault(frame, []).append((state.step.mode, state, n))

    # ------------------------------------------------------------------ capture

    def _warn(self, message: str) -> None:
        self.warnings.append(message)

    def _drain(self) -> str:
        text = "".join(self._sink)
        self._sink.clear()
        return text

    def _code_block(self, step: ResolvedStep, current: int) -> dict:
        lines = read_lines(step.code_path)
        start = step.code_start
        end = min(step.code_end, len(lines))
        same_file = step.code_path == step.path
        return {
            "file": step.code_rel_file,
            "start": start,
            "end": end,
            "current": current if same_file and start <= current <= end else None,
            "focus": [[a, b] for a, b in step.focus],
            "source": "\n".join(lines[start - 1 : end]),
        }

    def _capture(self, state: _State, frame: Any, hitno: int, *, return_value: Any = _MISSING) -> None:
        self._busy = True
        try:
            step = state.step
            spec = step.spec
            elapsed = time.perf_counter() - self._t0
            namespace = dict(frame.f_locals)
            if return_value is not _MISSING:
                namespace["__return__"] = return_value
            # `cw` gives show= expressions the author helpers (cw.image(...)) unless the frame has its own
            globals_ns = frame.f_globals if "cw" in frame.f_globals else {**frame.f_globals, "cw": _helpers}
            objects: list[dict] = []
            values: dict[str, Any] = {}
            for name, expr in spec.show.items():
                try:
                    value = eval(self._compiled[(spec.id, name)], globals_ns, namespace)
                except Exception as e:
                    names = sorted(k for k in namespace if not k.startswith("__") or k == "__return__")
                    objects.append({"name": name, "expr": expr, "display": error_display(e, names)})
                    self._warn(
                        f"step '{spec.id}' (hit {hitno}): show[{name!r}] = {expr!r} raised "
                        f"{type(e).__name__}: {e}"
                    )
                    continue
                values[name] = value
                try:
                    display = to_display(value)
                except Exception as e:
                    display = error_display(e)
                    self._warn(
                        f"step '{spec.id}' (hit {hitno}): could not serialise {name!r}: "
                        f"{type(e).__name__}: {e}"
                    )
                objects.append({"name": name, "expr": expr, "display": display})
            apply_step_budget(objects)

            def fill(match: Any) -> str:
                name = match.group(1)
                return plain_text(values[name]) if name in values else match.group(0)

            text = PLACEHOLDER_RE.sub(fill, spec.text)
            current = step.break_line if step.mode == "after" else frame.f_lineno
            multi = spec.hit == "all"
            title = spec.title or f"{frame.f_code.co_name} ({step.rel_file}:{current})"
            if multi:
                title = f"{title} (hit {hitno})"
            entry = {
                "id": f"{spec.id}.{hitno}" if multi else spec.id,
                "spec_id": spec.id,
                "index": len(self._steps) + 1,
                "label": f"{step.index}.{hitno}" if multi else str(step.index),
                "kind": "step",
                "title": title,
                "location": {
                    "file": step.rel_file,
                    "line": current,
                    "paused_line": frame.f_lineno,
                    "function": frame.f_code.co_name,
                    "mode": step.mode,
                    "hit": hitno,
                    "elapsed": round(elapsed, 4),
                },
                "highlight": list(spec.highlight),
                "code": self._code_block(step, current),
                "objects": objects,
                "text": text,
                "console": self._drain(),
            }
            self._steps.append(entry)
            state.captured += 1
            if state.first_seq is None:
                state.first_seq = len(self._steps)
        finally:
            self._busy = False

    # ------------------------------------------------------------------ running

    def _execute(self) -> None:
        entry = self.resolved.spec.entry
        if entry.kind == "script":
            runpy.run_path(self._script, run_name="__main__")
            return
        module = importlib.import_module(entry.module or "")
        func = getattr(module, entry.function or "", None)
        if func is None or not callable(func):
            raise CodewalkError(f"entry {entry.target!r}: module {entry.module} has no callable {entry.function!r}")
        func()

    def run(self) -> Recording:
        spec = self.resolved.spec
        root = self.resolved.root
        entry = spec.entry
        saved_cwd = os.getcwd()
        saved_argv = list(sys.argv)
        saved_path = list(sys.path)
        saved_env = dict(os.environ)
        saved_streams = (sys.stdout, sys.stderr)
        saved_main = sys.modules.get("__main__")
        started = _dt.datetime.now(_dt.timezone.utc)
        crash: Optional[BaseException] = None
        duration = 0.0
        self._sink = []
        try:
            os.chdir(root)
            os.environ.update(spec.env)
            if entry.kind == "script":
                self._script = os.path.abspath(os.path.join(root, entry.target))
                sys.argv = [self._script, *entry.args]
                for p in (root, os.path.dirname(self._script)):
                    while p in sys.path:
                        sys.path.remove(p)
                    sys.path.insert(0, p)
            else:
                sys.argv = [entry.module or entry.target, *entry.args]
                while root in sys.path:
                    sys.path.remove(root)
                sys.path.insert(0, root)
            sys.stdout = _Tee(saved_streams[0], self._sink)
            sys.stderr = _Tee(saved_streams[1], self._sink)
            self._install_breaks()
            self._t0 = time.perf_counter()
            try:
                self.runcall(self._execute)
            except SystemExit as e:
                if e.code not in (None, 0):
                    crash = e
            except bdb.BdbQuit:
                pass
            except Exception as e:
                crash = e
            duration = time.perf_counter() - self._t0
        finally:
            self.clear_all_breaks()
            sys.stdout, sys.stderr = saved_streams
            os.chdir(saved_cwd)
            sys.argv = saved_argv
            sys.path[:] = saved_path
            os.environ.clear()
            os.environ.update(saved_env)
            if saved_main is not None:
                sys.modules["__main__"] = saved_main
        if crash is not None:
            self._steps.append(self._crash_step(crash))
        self._post_warnings()
        return Recording(
            spec=spec,
            backend=self.backend_name,
            steps=list(self._steps),
            warnings=list(self.warnings),
            recorded_at=started.isoformat(timespec="seconds"),
            duration=duration,
            crashed=crash is not None,
        )

    def _is_internal(self, filename: str) -> bool:
        if not filename or filename.startswith("<"):
            return True
        real = os.path.realpath(filename)
        return real.startswith(_PACKAGE_DIR + os.sep) or os.path.basename(real) in ("bdb.py", "runpy.py")

    def _crash_step(self, exc: BaseException) -> dict:
        frames = traceback.extract_tb(exc.__traceback__) if exc.__traceback__ else []
        user_frames = [f for f in frames if not self._is_internal(f.filename)]
        formatted = "".join(traceback.format_list(user_frames) + traceback.format_exception_only(type(exc), exc))
        if user_frames:
            formatted = "Traceback (most recent call last):\n" + formatted
        location = None
        code = None
        for f in reversed(user_frames):
            if f.lineno and os.path.isfile(f.filename):
                path = os.path.realpath(f.filename)
                lines = read_lines(path)
                start = max(1, f.lineno - 10)
                end = min(len(lines), f.lineno + 10)
                rel = _rel(self.resolved.root, os.path.abspath(f.filename))
                location = {
                    "file": rel,
                    "line": f.lineno,
                    "paused_line": f.lineno,
                    "function": f.name,
                    "mode": "crash",
                    "hit": 1,
                    "elapsed": round(time.perf_counter() - self._t0, 4),
                }
                code = {
                    "file": rel,
                    "start": start,
                    "end": end,
                    "current": f.lineno,
                    "focus": [],
                    "source": "\n".join(lines[start - 1 : end]),
                }
                break
        if isinstance(exc, SystemExit):
            message = f"SystemExit({exc.code!r})"
        else:
            message = f"{type(exc).__name__}: {exc}"
        return {
            "id": "crash",
            "spec_id": None,
            "index": len(self._steps) + 1,
            "label": "crash",
            "kind": "crash",
            "title": f"Uncaught {type(exc).__name__}",
            "location": location,
            "highlight": [],
            "code": code,
            "objects": [],
            "text": f"The program stopped with `{message}`.",
            "traceback": formatted,
            "console": self._drain(),
        }

    def _post_warnings(self) -> None:
        for state in self._states:
            if state.captured:
                continue
            spec = state.step.spec
            where = state.step.location_text
            if state.counter == 0:
                self._warn(f"step '{spec.id}' at {where} was never reached")
                continue
            satisfied = state.counter >= 1 if spec.hit == "all" else state.counter >= spec.hit
            if not satisfied:
                self._warn(
                    f"step '{spec.id}' at {where} was hit {state.counter} time(s), "
                    f"so hit={spec.hit!r} was never satisfied"
                )
            else:
                self._warn(
                    f"step '{spec.id}' at {where} was hit, but the program ended before the "
                    f"'{state.step.mode}' capture point was reached"
                )
        captured = [s for s in self._states if s.captured]
        executed = sorted(captured, key=lambda s: s.first_seq or 0)
        if [s.step.index for s in captured] != [s.step.index for s in executed]:
            order = " -> ".join(s.step.spec.id for s in executed)
            self._warn(
                f"steps were reached in a different order than declared: {order}. "
                "Reorder them in the walkthrough so the explanation follows the program."
            )


def record(
    spec: WalkthroughSpec,
    *,
    backend: Optional[str] = None,
    report: Optional[Report] = None,
) -> Recording:
    """Analyze (unless a report is given), then run and record in this process."""
    if report is None:
        report = analyze(spec)
    if report.errors or report.resolved is None:
        raise CodewalkError("the walkthrough has errors:\n" + "\n".join(str(p) for p in report.errors))
    recorder = Recorder(report.resolved, backend=backend)
    recorder.warnings.extend(
        f"step '{p.step_id}': {p.message}" if p.step_id else p.message for p in report.warnings
    )
    return recorder.run()
