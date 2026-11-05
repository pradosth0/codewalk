---
name: codewalk
description: Explain a Python codebase visually by recording one run of it with codewalk. Write a walkthrough.py (breakpoints, objects to show, Markdown explanations), record, check the screenshots, hand over a self-contained HTML page where the reader steps through the program with the project schema, the paused code, the live objects and your explanation. Use when asked to explain, document, onboard someone to, or visually walk through how a Python program, pipeline, service or library works.
---

# codewalk: explain a codebase by running it

You write a small `walkthrough.py`. `codewalk record` runs the program once under a
debugger, pauses at your breakpoints, captures the objects you asked for and writes
`out/index.html`: a page where the reader presses Next through the run. Each step shows

- the project schema on top with the current stage highlighted,
- the code paused at the breakpoint on the left,
- the objects you chose on the right (tables, arrays, plots, HTML, JSON),
- your explanation underneath.

The target codebase is never modified. The reference walkthrough is
`examples/demo_pipeline/walkthroughs/train.py` in the codewalk repository: read it
once before writing your first one.

## Workflow

1. **Set up.** In the target project's environment: `uv add --dev codewalk[screenshot]`
   (or `pip install 'codewalk[screenshot]'`) and `playwright install chromium`
   once. If codewalk is a checkout rather than a package, use
   `uv add --dev --editable /path/to/codewalk[screenshot]`. Without the extra
   everything works except `codewalk screenshot`.
2. **Read the code.** Find the entry point and the cheapest invocation that still
   goes through every stage: small data, few epochs, a fixture, a `--limit` flag.
   The run must finish in well under a minute; it is executed once, in full.
3. **Draw the schema.** 4 to 9 nodes: stages for a pipeline, components for a
   service, the call graph for an algorithm. Use Mermaid `flowchart LR` text, or a
   plain list of stage names. Every step highlights one of these nodes.
4. **Choose the breakpoints in three levels** (see *Levels of detail*): one key step
   per schema node at level 1, 6 to 15 steps of the normal walk at level 2, and
   line-by-line steps at level 3 only where the implementation is not obvious.
   All in execution order, one idea each.
5. **Scaffold and write.** `codewalk init` writes a commented `walkthrough.py` that
   already passes `check`; fill in the steps.
6. **Validate and record.** `codewalk check walkthrough.py` (static, instant), fix,
   then `codewalk record walkthrough.py -o out`. Read every warning.
7. **Look at the result.** `codewalk screenshot out --all`, then open each PNG.
   Judge it as a reader: is the right object open, does the text explain this
   moment, is the code window the right size?
8. **Deliver** `out/index.html` (self-contained, open from disk or `codewalk serve out`).

## The DSL

```python
from codewalk import Walkthrough

walkthrough = Walkthrough(
    title="How train.py fits the model",
    entry="run.py --epochs 20",            # script + args (run as __main__), or "pkg.module:function"
    root="..",                             # relative to THIS file; default: this file's directory
    schema=["Load", "Clean", "Train"],     # or Mermaid text: "flowchart LR\n  load[Load] --> train[Train]"
    description="Markdown shown before step 1.",
    env={"MPLBACKEND": "Agg"},             # optional extra environment for the run
    timeout=120,                           # seconds, default 600
    levels=["Overview", "Walkthrough", "Line by line"],   # optional names for the levels of detail
)

walkthrough.step(
    id="clean",                            # stable id: ?step=clean deep links, screenshot --step clean
    title="Drop bad rows",
    level=2,                               # 1 = key step, 2 = default walk, 3 = line by line (any int >= 1)
    at="demo/clean.py:23",                 # pause BEFORE line 23 runs
    highlight="clean",                     # node id (or list) in the schema; "Clean" in a list schema -> "clean"
    code="demo/clean.py::clean",           # left pane; default: the enclosing function (or 15 lines around)
    focus="demo/clean.py:21-23",           # lines to emphasise within the code pane
    show={"bad": "df[outliers]", "n": "int(outliers.sum())"},   # name -> expression, evaluated in the paused frame
    plot="plot_loss(history)",             # a matplotlib Figure/Axes, PIL image or image array; shown first
    text="Removed {{n}} rows. ...",        # Markdown; {{name}} inserts the text form of a `show` value
)
```

Locations, exactly one per step:

| Form | Pauses | Use it for |
|---|---|---|
| `at="file.py:LINE"` | before LINE runs | the state going into a line |
| `after="file.py:LINE"` | once LINE has run | what the line assigned or produced |
| `at="file.py::func"` | on entry (first body line); `Class.method` works | a stage's inputs |
| `at="file.py::func", when="return"` | when it returns, with `__return__` | a stage's output |

Loops: `hit=3` captures the third time the location is reached; `hit="all"`
captures every time (up to `max_hits`, default 10) as sub-steps `k.1, k.2, ...`;
`condition="epoch % 10 == 0"` counts only hits where the expression is true.

`show` values are serialised by type: pandas DataFrame/Series as tables (first 20
rows), numpy arrays and torch tensors as shape, dtype, stats and a corner preview,
matplotlib figures and PIL images as pictures, objects with `_repr_html_` as HTML,
dicts and dataclasses as JSON, anything else as `repr`. `cw.image(arr)` turns an
HxW, HxWx3, HxWx4 or CxHxW array (or PNG bytes) into a picture. Expressions may
call functions but must not mutate state: they run inside the real program.

Paths are relative to `root`. Line numbers refer to the files as they are when you
record.

## Levels of detail

Readers start with the key steps and go deeper only where they need to, without asking
you again. Every step has a `level` (default 2); the viewer walks one level at a time:
**Next/Prev** skip deeper steps, **Down** (↓) enters the details of the current step,
**Up** (↑) returns to the step that summarises them, and the outline drawer (`o`) has a
selector for the level to walk at. Unless the person asks for something else, produce three:

| Level | For whom | What it holds |
|---|---|---|
| 1 | a project manager | one key step per schema node, showing the stage's result; 4 to 9 steps that read as a complete story on their own |
| 2 | a teammate who must understand and vouch for the output | the normal walk: inputs, what key lines produced, a loop at a few iterations |
| 3 | yourself, debugging or learning the implementation | line by line, only inside the parts that are not obvious; every non-obvious step explained |

How steps are nested is derived from the recorded order, with one rule: **a key step
summarises the deeper steps recorded before it**, back to the previous step at its
level. So put a level-1 step where the stage's result is visible, at the stage
function's return (`when="return"`) or in the caller right after the call (`after=`),
and let its details come before it. Do not put a key step at a function's entry with
its details after it; `check` warns about that. Deeper steps at the very end attach to
the previous key step. For a different nesting, set `parent="step-id"` on the deeper
step. Declaration order must still follow first execution: a `hit="all"` loop step is
declared before the level-3 steps inside one of its iterations, and its hit after
those lines summarises them.

`codewalk screenshot out --all --level 1` renders only the overview; read those pages
first and ask whether they tell the whole story on their own.

## Choosing breakpoints

- One idea per step. If the text needs "also", split the step.
- Prefer `when="return"` on a function for its result and `after=` on a line for
  what it assigned. `at=` on a line is for showing what goes in.
- In a loop, show 3 or 4 iterations with `hit="all"` plus a `condition`, not 100.
- Show 2 to 4 objects per step (6 is the maximum). Put the one the text talks about
  first: it is the open tab. One plot where a picture explains more than numbers.
- `code=` defaults to the enclosing function, which is usually right. Set it when the
  function is long (`file.py:40-70`) and use `focus=` for the lines that matter.
- Highlight the schema node of the stage the reader is in, not the one being called.
- Capture the last step somewhere the printed output is visible (a final `return`),
  because console output is attached to the step after it was printed.

## Writing the text

Two or three short paragraphs of Markdown per step. Say what this moment is, why the
code does it this way, and what to look at in the objects pane (name the tab). Use
`{{name}}` for numbers that come from the run so that the text stays true when the
data changes. Do not restate the code line by line. The `description` is the
introduction: what the program does and what the walkthrough will show.

## Reading `check` and `record` output

| Message | Meaning | Fix |
|---|---|---|
| `error: step 'x': file:LINE is blank or a comment` | breakpoint would never fire | move it to a statement |
| `warning: ... is not an executable line` | likely a `def`, decorator or continuation line | pick the first line of the statement |
| `error: ... highlight='foo' is not a node of the schema` | id mismatch | use the ids from the Mermaid text (`load[Load]` is `load`) or the slug of the list entry |
| `warning: step 'x' was never reached` | the run did not pass there | check the entry arguments and the condition |
| `warning: hit=5 was never satisfied` | fewer hits than expected | lower `hit` or use `hit="all"` |
| `warning: show['df'] = ... raised NameError` plus the names that were available | wrong frame or too early | use a name from the list, or move to `after=` / `when="return"` |
| `warning: steps were recorded in a different order than declared` | your model of the flow is off | reorder the steps to match the run |
| `warning: ... level 1 step at the entry of f() is followed by deeper steps` | the key step would not own its details | pause at the return or after the call instead, or set `parent=` |
| `warning: steps ... no shallower step follows them` | trailing details with no summary | add a key step after them or set `parent=` |
| `error: parent='x' is not the id of any step` / `not shallower` | a bad explicit parent | name an existing step with a lower level |
| last step is a `crash` | the program raised | the traceback is a step; fix the invocation or explain the failure |

`codewalk record --strict` exits non-zero on any warning; use it in CI.

## Commands

```
codewalk init [DIR] [--entry "run.py --flag"] [-o walkthrough.py]   # scaffold
codewalk check walkthrough.py                                       # validate without running
codewalk record walkthrough.py -o out [--strict] [--timeout S]      # run once -> out/steps.json + out/index.html
codewalk screenshot out --all [--level N] | --step ID [-o DIR|file.png] [--dark] [--width W --height H]
codewalk serve out [--port 8731] [--open]                           # local server for the page
codewalk build out/steps.json                                       # rebuild index.html from a recording
```
