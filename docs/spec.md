# Spec: codewalk, agent-authored visual walkthroughs of Python code

Version 0.3, 2026-10-28. Decisions below were taken with the project owner; see
[research.md](research.md) for the options that were weighed. `codewalk` is a placeholder
name for the package and CLI. Implemented: milestones 1 to 4 (DSL, `check`, recorder,
all display kinds, the viewer, `build`, `serve`, the demo pipeline, `screenshot`, `init`
and the agent skill).

## 1. Goal and non-goals

**Goal.** Give an agent a toolkit to explain a Python codebase the way a debugger session
would: it writes one small spec file (breakpoints, what to show, what to say), runs one
command, and gets a self-contained interactive page where a reader steps through the
program with a schema of the whole project on top, the running code on the left, captured
objects or plots on the right, and an explanation under them.

**Non-goals for v1.**
- Automatic generation of walkthroughs. The agent curates every step.
- Live stepping of a running process (the step format is designed so it can be added later).
- Editing the walkthrough inside the viewer.
- Notebooks as targets, multi-process targets, breakpoints in worker threads.
- Plotly or other interactive chart libraries (the display union reserves a `plotly` kind).

## 2. Decisions taken

| Topic | Decision |
|---|---|
| Execution model | Record once, play back. Output is one self-contained HTML file. |
| Breakpoint definition | External `walkthrough.py`, steps reference `file:line` (or a function). The target codebase is never modified. |
| Capture mechanism | `bdb.Bdb` subclass; `monitoring` backend on Python 3.14+ (where `bdb` gained the `backend` parameter), `settrace` below. |
| Viewer | React + TypeScript, built once with Vite into a single HTML template embedded in the Python package. Users and agents never need Node. |
| Schema | Mermaid flowchart text; a plain stage list is a shortcut that generates one. Current node highlighted per step. |
| Displays in v1 | pandas tables, numpy/torch array summaries, matplotlib figures and images, JSON trees, HTML reprs, text fallback. |
| Target codebases | Data/ML pipelines, object-oriented systems and services, algorithms and libraries. |
| First target | A small demo pipeline under `examples/` that also serves as the test fixture. |
| Agent verification | `codewalk screenshot` via Playwright (optional dependency). |

## 3. Architecture

```
walkthrough.py ──► codewalk check ──► codewalk record ──► steps.json ──► codewalk build ──► index.html
 (agent writes)     (static checks)    (bdb runner +                      (embed JSON in
                                        serializers)                       viewer template)
```

Three independent layers, one contract (`steps.json`, section 6):

1. **Spec** (`codewalk.spec`): the Python DSL the agent writes, validated with pydantic.
2. **Recorder** (`codewalk.recorder`, `codewalk.serialize`): runs the target under bdb,
   evaluates display expressions at each breakpoint, serializes results, writes `steps.json`.
3. **Viewer** (`viewer/`, built artifact committed at `src/codewalk/viewer/index.html`):
   renders a `steps.json`, nothing else. A later live mode streams the same step objects
   over a WebSocket and the viewer does not change.

## 4. Authoring DSL

A walkthrough is a Python file that defines one module-level `Walkthrough` instance.

```python
from codewalk import Walkthrough

walkthrough = Walkthrough(
    title="How the demo pipeline trains a model",
    entry="run.py --rows 500",            # script + args, or "package.module:function"
    schema="""
    flowchart LR
      load[Load CSV] --> clean[Clean] --> feats[Features] --> train[Train] --> evaluate[Evaluate]
    """,                                  # or schema=["Load CSV", "Clean", "Features", "Train", "Evaluate"]
    root=".",                             # paths below are relative to this; default: the file's directory
)

walkthrough.step(
    id="load",
    title="Read the raw CSV",
    at="src/demo/load.py:18",             # pause BEFORE this line runs
    highlight="load",                     # schema node id(s)
    code="src/demo/load.py::load_csv",    # left pane: a function, or "file:30-55"; default: enclosing function
    focus="src/demo/load.py:18-21",       # optional lines to emphasise inside the code pane
    show={"raw": "df.head(10)", "shape": "df.shape", "dtypes": "df.dtypes"},
    text="""
    The pipeline starts by reading `data/raw.csv` ...
    """,
)

walkthrough.step(
    id="loss-curve",
    after="src/demo/train.py:44",         # pause AFTER this line has run (the assignment is visible)
    highlight="train",
    hit="all", max_hits=5,                # one sub-step per loop iteration, capped
    show={"epoch": "epoch", "loss": "loss"},
    plot="plot_loss(history)",            # any expression returning a matplotlib Figure/Axes, PIL image, or image array
    text="Epoch {{epoch}}: the loss is now {{loss}}.",   # placeholders filled from `show` values
)

walkthrough.step(
    at="src/demo/evaluate.py::score",     # pause on function entry
    when="return",                        # ... or when it returns; `__return__` is then available
    highlight=["evaluate"],
    show={"metrics": "__return__"},
    text="...",
)
```

### 4.1 `Walkthrough` fields

| Field | Type | Meaning |
|---|---|---|
| `title` | str | Shown in the viewer header. |
| `description` | str, optional | Markdown intro shown before step 1 (viewer "step 0"). |
| `entry` | str | What to run: `"script.py arg1 arg2"` (executed with `runpy`, `__name__ == "__main__"`, `sys.argv` set) or `"pkg.module:func"` (imported and called with no args). |
| `schema` | str or list[str] | Mermaid source, or a list of stage labels converted to `flowchart LR` with slugified ids (`"Load CSV"` becomes `load_csv`). |
| `root` | path | Base for all relative paths and the working directory during the run. Default: directory of `walkthrough.py`; a relative `root` is resolved against that directory too (`root=".."` from `walkthroughs/train.py`), never against the current directory. |
| `env` | dict, optional | Extra environment variables for the run. |
| `timeout` | seconds, default 600 | Hard limit for the run. |

### 4.2 `step()` fields

| Field | Type | Meaning |
|---|---|---|
| `at` / `after` | str | Exactly one. `file:line` pauses before / after that line. `file::func` pauses at function entry (first body line). |
| `when` | `"line"` (default), `"return"` | With `at="file::func"`, `"return"` pauses when the function returns and exposes `__return__`. |
| `hit` | int (default 1) or `"all"` | Which hit of this location to capture. `"all"` records every hit as sub-steps `k.1, k.2 ...`. |
| `max_hits` | int, default 10 | Cap for `hit="all"`. |
| `condition` | str, optional | Expression evaluated in the frame; the hit counts only when truthy. |
| `highlight` | str or list[str] | Schema node ids to mark as current. |
| `code` | str, optional | `file:start-end` or `file::func`. Default: enclosing function of the pause location, or 15 lines either side at module level. |
| `focus` | str, optional | `file:start-end` lines emphasised within the code pane. |
| `show` | dict[str, str] | Ordered name to expression. Evaluated in the paused frame's globals and locals. At most 6 entries. |
| `plot` | str, optional | Sugar for a `show` entry named `plot`, pinned first and opened by default. |
| `text` | str | Markdown. `{{name}}` is replaced with the text form of the `show` value of that name. |
| `title` | str, optional | Default: `"<function> (<file>:<line>)"`. |
| `id` | str, optional | Stable id, default slug of the title plus index. Used by `?step=<id>` deep links and the screenshot command. |

### 4.3 Semantics that must be documented for agents

- A breakpoint on line N pauses before N executes, exactly like pdb. To inspect what a
  line assigned, use `after=`. Implementation: break at N, then `set_next(frame)` and capture
  on the next line event in the same frame, which is correct across loop ends and calls.
- Expressions run in the real frame. They can call functions and allocate, but they must
  not mutate state (documented; not enforced). They also see `cw`, the `codewalk.display`
  helper module, unless the frame defines its own `cw`: `cw.image(arr)` displays an HxW,
  HxWx3, HxWx4 or CxHxW array (or raw PNG/JPEG/SVG bytes) as an image.
- A failing expression does not abort the run. It is recorded as an `error` display and
  printed as a warning. `--strict` turns it into a failure.
- Steps are recorded in execution order. If that differs from declaration order the
  recorder warns, because the agent's mental model of the flow is probably wrong.
- Steps whose location is never reached are reported at the end (exit code 2 with `--strict`).
- If the target raises, the steps recorded so far are kept and a final `crash` step holds
  the traceback. The walkthrough is still built, so failures can be explained too.
- Line numbers refer to the file as it is when `record` runs. `check` verifies that the
  line is an executable line of the compiled module and warns otherwise.

## 5. Recorder

- `codewalk record` spawns a child interpreter (`python -m codewalk._run <spec> <out>`), so
  a crashing or hanging target never takes the CLI down; the parent enforces `timeout`.
- The child: imports the spec, sets `cwd` and `env`, builds a `Bdb(backend=...)` subclass,
  registers `set_break(file, line)` for every step, and runs the entry via `runpy`
  (script) or import + call (function) inside `Bdb.run`/`runcall`.
- Backend: `monitoring` on Python 3.14+ (bdb's `backend` parameter is a 3.14 addition), `settrace` otherwise. Overridable with `--backend`.
- On each `user_line` that matches a step: increment the hit counter for that location,
  check `condition`, check `hit`, then capture:
  1. location: file, line, function, hit number, elapsed seconds;
  2. code pane: resolve `code`/`focus` to a line range and read the source text;
  3. objects: evaluate each `show` expression, pass the value through the serializer
     registry (section 7), apply size caps;
  4. console: stdout and stderr written since the previous step (a tee installed at start);
  5. render `{{placeholders}}` in `text`.
  Then `set_continue()`.
- Hot paths are unaffected: bdb installs a local trace only in frames whose file has a
  breakpoint; everything else runs at native speed.
- Output: `<out>/steps.json`, then `build` is invoked automatically to produce
  `<out>/index.html`. `--json-only` skips the build.

## 6. Step payload (`steps.json`)

```jsonc
{
  "version": 1,
  "title": "How the demo pipeline trains a model",
  "description": "markdown or empty",
  "entry": "run.py --rows 500",
  "recorded_at": "2026-10-28T10:42:00Z",
  "python": "3.14.4",
  "schema": { "kind": "mermaid", "source": "flowchart LR\n  load[Load CSV] --> ..." , "nodes": ["load", "clean", "..."] },
  "warnings": ["step 'x' never reached"],
  "steps": [
    {
      "id": "load",
      "index": 1,                       // 1-based; sub-steps are "7.1", "7.2" in `label`
      "label": "1",
      "title": "Read the raw CSV",
      "location": { "file": "src/demo/load.py", "line": 18, "function": "load_csv", "hit": 1, "elapsed": 0.03 },
      "highlight": ["load"],
      "code": { "file": "src/demo/load.py", "start": 12, "end": 31, "current": 18, "focus": [[18, 21]], "source": "def load_csv(...):\n ..." },
      "objects": [
        { "name": "raw", "expr": "df.head(10)", "display": { "kind": "table", "columns": ["id", "price"], "index": [0, 1], "index_name": null, "rows": [[1, 9.5], [2, 3.0]], "shape": [500, 2], "dtypes": { "id": "int64", "price": "float64" }, "truncated": true, "type": "pandas.DataFrame" } },
        { "name": "shape", "expr": "df.shape", "display": { "kind": "json", "value": [500, 2] } },
        { "name": "plot", "expr": "plot_loss(history)", "display": { "kind": "image", "mime": "image/png", "data": "<base64>", "width": 880, "height": 520, "type": "matplotlib.Figure" } },
        { "name": "w", "expr": "model.w", "display": { "kind": "array", "library": "torch", "dtype": "torch.float32", "device": "cpu", "shape": [3, 4], "size": 12, "stats": { "min": -1.2, "max": 0.9, "mean": 0.01, "std": 0.5, "nan": 0 }, "preview": [[0.1, 0.2], [0.3, 0.4]], "preview_shape": [2, 2], "preview_index": null, "truncated": true, "type": "torch.Tensor" } },
        { "name": "model", "expr": "model", "display": { "kind": "html", "html": "<div class=\"sk-top-container\">...", "type": "sklearn.LinearRegression" } },
        { "name": "cfg", "expr": "cfg", "display": { "kind": "text", "text": "Config(lr=0.01, ...)", "truncated": false, "type": "Config" } },
        { "name": "oops", "expr": "undefined_name", "display": { "kind": "error", "message": "NameError: name 'undefined_name' is not defined", "names": ["df", "path", "cfg"] } }
      ],
      "text": "markdown with placeholders already substituted",
      "console": "Loaded 500 rows\n"
    },
    { "id": "crash", "kind": "crash", "title": "Uncaught exception", "traceback": "...", "...": "other fields as above" }
  ]
}
```

Display kinds in v1: `table`, `array`, `image`, `json`, `html`, `text`, `error`. Every
display carries `type` (top-level package plus class name). A `text` display may carry
`note` (why a richer serializer failed) or `over_limit: true` (replaced for size, see
section 7). `preview_index` on an `array` names the leading indices of the shown 2-D slice.
Reserved for later: `plotly`, `diff`, `graph`.

## 7. Serializers

Registry tried in order; the first serializer that returns a display wins (a serializer
may return `None` to pass, e.g. a `_repr_png_` that returns nothing). Optional libraries
are never imported by the serializer: an object of theirs can only exist once its library
is loaded, so `sys.modules` is consulted instead.

| Match | Display | Notes |
|---|---|---|
| `codewalk.image(...)` / `cw.image(...)` wrapper | `image` | Raw PNG/JPEG/GIF/WebP/SVG bytes pass through (mime sniffed); arrays (HxW, HxWx3, HxWx4, CxHxW; uint8, bool, [0, 1] floats, or min-max scaled) are PNG-encoded by a built-in encoder, no PIL needed. |
| `pandas.DataFrame` / `Series` | `table` | First 20 rows and 30 columns, index included (MultiIndex levels joined with " / "), NaN/NaT/None as null, inf as "inf", timestamps ISO strings, strings cut at 200 chars, `shape`, `dtypes`, `index_name`. |
| `numpy.ndarray`, `torch.Tensor` | `array` | Tensors via `.detach().cpu().numpy()` (bfloat16 upcast), `device` recorded. Stats (min, max, mean, std, nan count) for numeric and bool dtypes, over finite values. Preview: 1-D first 20, 2-D first 6x6, n-D first 6x6 of the `[0, 0, ...]` slice. NaN/inf cells as strings. |
| numpy scalar | `json` | `.item()`, with the numpy type name. |
| `matplotlib` `Figure`, `SubFigure` or `Axes` | `image` | Root figure saved as PNG, tight bbox, dpi 110. The figure is not closed. |
| `PIL.Image.Image` | `image` | PNG; exotic modes go through `convert("RGB")`. |
| objects with `_repr_png_` / `_repr_svg_` | `image` | bytes or base64 str accepted; SVG has no width/height. |
| objects with `_repr_html_` | `html` | Raw HTML, sanitised in the viewer with DOMPurify. Covers scikit-learn estimators, pandas Stylers and similar. Checked before the json tree, so a dataclass with `_repr_html_` renders as html. |
| dict, list, tuple, set, dataclass, NamedTuple, pydantic model, Enum, Path | `json` | Depth 4, 200 items per container, NaN/inf as strings, non-JSON leaves become `repr` (200 chars). |
| anything else | `text` | `repr`, truncated to 2000 chars; a broken `__repr__` yields a notice instead of an error. |

Caps: 2 MB per display and 10 MB per step, measured on the JSON. An over-size display is
replaced by a `text` notice with `over_limit: true` that tells the author what to do
(`df.head()`, `arr[:10]`, a smaller figure). A serializer that raises falls back to `text`
with a `note` naming the failure, so recording never stops because of a display.

Known cost, measured on the data fixture (pandas, matplotlib and PIL imported inside the
recorded run): a plain run takes 1.1 s; the `settrace` backend on Python 3.10 takes 1.6 s,
the `monitoring` backend on 3.14 takes 1.5 s, but `settrace` on 3.14 takes 12.5 s. On 3.12
and later `sys.settrace` is emulated on top of `sys.monitoring`, and bdb's Python-level
trace function then runs for every call during the imports. 3.14 defaults to `monitoring`;
3.12 and 3.13 only have `settrace` through bdb, so a `sys.monitoring` tracer of our own for
those two versions is a worthwhile follow-up.

## 8. Viewer

Layout, matching the original sketch:

```
┌──────────────────────────────────────────────────────────────┐
│ title                      schema (Mermaid, current node lit) │
├──────────────────────────────┬───────────────────────────────┤
│ code                         │ objects / plot (tabs)          │
│ file:line header             ├───────────────────────────────┤
│ line numbers, current line,  │ explanation (markdown)        │
│ focus lines, rest dimmed     │                               │
├──────────────────────────────┴───────────────────────────────┤
│ ◀ Prev    step 3 / 12  "Read the raw CSV"    Next ▶   console │
└──────────────────────────────────────────────────────────────┘
```

Implemented in `viewer/` (Vite 6, React 19, TypeScript, strict):

- Navigation: Prev/Next buttons, keyboard (arrows, space, PageUp/Down, Home/End), and
  `?step=<id>` deep links (`<label>` and 1-based numbers also work). The URL follows the
  current step. A non-empty `description` becomes an intro view before step 1.
- Schema pane: Mermaid 11 `render()` per step; the definition gets `classDef cw_active`
  and `classDef cw_done` appended plus `class` lines for the current and the already
  visited nodes. If the classes break parsing (a non-flowchart diagram), it falls back to
  rendering the schema untouched and shows why. Clicking a node jumps to the first step
  that highlights it. The SVG scales with the header height.
- Code pane: Shiki 3 fine-grained bundle (Python grammar, github-light/dark, JavaScript
  regex engine, no wasm). Current line highlighted with a marker (▶ before, ✓ after,
  ↩ return, ✗ crash), focus lines emphasised and the rest dimmed, current line scrolled
  into view.
- Objects pane: one tab per object, the `plot` entry first; the selected name is kept
  across steps when the next step has it. Renderers for the seven kinds: table (sticky
  header, dtypes, nulls in italics), array (stats tiles and preview grid with the slice
  note), image (data URL), html (through DOMPurify), json (collapsible tree, open two
  levels deep), text (with `note` and over-limit styling), error (message plus the names
  that were available). A crash step shows the traceback as its first object.
- Explanation pane: `react-markdown` with GFM. KaTeX is deferred: its fonts would add
  more than a megabyte to every page.
- Console: a toggle in the footer opens the program output captured since the previous
  step; the button shows a dot when there is any.
- Panes are resizable with a small custom splitter (no panel library); the theme follows
  `prefers-color-scheme`.
- Build: `npm run build` type-checks and runs Vite with `vite-plugin-singlefile`, writing
  one file to `src/codewalk/viewer/index.html` (about 4 MB, mostly Mermaid), which is
  committed and shipped in the wheel, so `pip install` needs no Node. The template keeps
  `<script id="codewalk-data" type="application/json">__CODEWALK_DATA__</script>` and a
  `__CODEWALK_TITLE__` placeholder; `codewalk/build.py` replaces both, escaping `</` in
  the JSON so the data block cannot be closed early. In `vite dev` the app loads
  `viewer/fixtures/steps.json` instead.

### 8.1 Automation hooks

The viewer marks the root element with `data-step="<id>"` (`intro` before step 1) and the
schema and code panes with `data-settled="true"` once their asynchronous rendering
(Mermaid, Shiki) matches the current step. `codewalk screenshot` waits for these, for
`document.fonts` and for every image to be decoded before capturing; other automation
can do the same.

## 9. CLI

```
codewalk init [DIR] [--entry "run.py --flag"] [-o PATH] [--force]   # scaffold walkthrough.py that passes check
codewalk check walkthrough.py                                       # static validation, exit 1 on errors
codewalk record walkthrough.py [-o out/] [--strict] [--timeout S] [--backend settrace|monitoring] [--json-only]
codewalk build out/steps.json [-o out/index.html]                   # rebuild the page, e.g. after a viewer upgrade
codewalk serve out/ [--port 8731] [--host 127.0.0.1] [--open]       # static server, Cache-Control: no-store
codewalk screenshot out/ (--all | --step ID ...) [-o DIR|file.png] [--width 1440 --height 900] [--dark] [--timeout S]
```

`check` verifies: the spec imports and defines one `Walkthrough`; entry exists; every
`at`/`after`/`code`/`focus` path exists under `root`, lines are within the file and are
executable lines of the compiled module; every `show` expression parses; `highlight` ids
exist among the schema's node ids (regex-extracted; Mermaid itself is only parsed in the
viewer); ids are unique; `show` has at most 6 entries; `{{placeholders}}` name a `show` entry.

`init` detects the entry script (a top-level `.py` that checks `__name__`, preferring
`main.py`, `run.py`, `app.py`, ...), points the first step at its `main` function or first
statement, lists the modules it found, and refuses to overwrite without `--force`.

`screenshot` needs the `screenshot` extra (Playwright) and `playwright install chromium`.
It serves the folder over a local HTTP port, opens `?step=<id>` for each target, waits
for the settle markers (section 8.1) and writes `NN-<step id>.png` (`00-intro.png` when
the walkthrough has a description). A single `--step` may be written to a `.png` path.
Exit codes: 1 for spec errors or a missing browser, 2 for warnings or a crash under
`--strict`, 3 for a recording timeout.

Errors are written for agents: one line each, `file:line`, what is wrong, and when an
expression fails at record time, the names that were available in the frame.

Running inside the target project's environment, without installing:

```bash
uv run --with codewalk codewalk record walkthroughs/train.py -o walkthroughs/out
```

## 10. Agent skill

`skills/codewalk/SKILL.md` ships with the repository (and is linked from
`.claude/skills/codewalk` so that Claude Code picks it up here). It is the main product
surface for agents and prescribes the workflow:

1. Install the package in the target environment; read the codebase; find the entry
   point and a cheap example invocation that still goes through every stage.
2. Draw the schema: stages for pipelines, components for services, call graph for
   algorithms. 4 to 9 nodes.
3. Choose 6 to 15 breakpoints, one idea each, in execution order. Prefer `after=` when
   the point is to show what a line produced and `when="return"` for a stage's output;
   use `hit`/`condition` inside loops.
4. `codewalk init`, then write the steps; keep `show` to the 2 to 4 objects that matter,
   the one the text talks about first; one plot where a picture explains more than a table.
5. `codewalk check`, fix, `codewalk record`, read the warnings (unreached steps, failed
   expressions, order mismatch); the skill has a table of every message and its fix.
6. `codewalk screenshot --all` and look at the images; tighten text and code ranges.
7. Hand over `out/index.html` (self-contained) or `codewalk serve`.

## 11. Repository layout

```
viz/
  pyproject.toml                  # package codewalk, managed with uv; extras: [screenshot]
  src/codewalk/
    __init__.py                   # Walkthrough, image()
    spec.py                       # DSL + pydantic validation + path/line resolution
    check.py                      # static analysis -> Report (errors, warnings, resolved steps)
    pysource.py                   # cached source/ast helpers: functions, ranges, executable lines
    recorder.py                   # Bdb subclass, hit policies, capture loop
    _run.py                       # child-process entry used by `record`
    serialize.py                  # display registry and size caps
    display.py                    # author helpers: image(), PNG encoder (also `cw` in show= expressions)
    build.py                      # steps.json -> index.html (embeds into viewer/index.html)
    serve.py                      # static server for an output folder
    screenshot.py                 # Playwright capture of built pages (optional extra)
    scaffold.py                   # `init`: walkthrough.py template with entry detection
    cli.py                        # typer app
    viewer/index.html             # built viewer template (committed)
  viewer/                         # Vite + React + TS source of the viewer
    src/App.tsx, components/{SchemaPane,CodePane,ObjectsPane,TextPane,NavBar,Splitter}.tsx
    src/renderers/{TableView,ArrayView,ImageView,HtmlView,JsonView,TextView,ErrorView}.tsx
    src/{highlight,mermaid,data,theme,types}.ts, styles.css
    fixtures/steps.json           # recording of the demo pipeline, used by `vite dev`
  examples/demo_pipeline/
    run.py, demo/{load,clean,features,train,evaluate}.py, data/raw.csv
    walkthroughs/train.py         # the reference walkthrough (root="..")
  skills/codewalk/SKILL.md        # agent workflow, DSL, breakpoint and text guidelines, warning table
  .claude/skills/codewalk -> ../../skills/codewalk
  tests/                          # pytest: spec, check, recorder, serializers, build, cli, demo, scaffold, screenshot
  docs/research.md, docs/spec.md, docs/images/
```

## 12. Milestones

| # | Deliverable | Done when |
|---|---|---|
| M1 | Package skeleton, DSL, `check`, recorder with hit policies, `after`, function entry/return | done |
| M2 | Serializers for the seven display kinds, size caps, console capture, placeholders | done |
| M3 | Viewer: five panes, navigation, Mermaid highlighting, Shiki, renderers; singlefile build; `build` and `serve` | done: both fixtures open with no console errors; one 4 MB HTML file |
| M4 | Demo pipeline, reference walkthrough, `screenshot`, `init`, SKILL.md, README | done: `record examples/demo_pipeline/walkthroughs/train.py` gives 12 steps with no warnings; `screenshot --all` writes 13 readable pages in about 5 s; `init` output passes `check` |
| Later | Live mode over WebSocket, `plotly` display, nested schemas, VS Code wrapper, a native `sys.monitoring` tracer for 3.12/3.13 | |

## 13. Assumptions not yet confirmed

- Package and CLI name `codewalk` (rename is a search-and-replace). Not published to PyPI
  yet; `uv add --editable` or `pip install -e` from the checkout.
- Python 3.10 as the floor; 3.14+ gets the `monitoring` backend automatically.
- Viewer dependencies: React 19, Shiki 3, Mermaid 11, react-markdown 10, DOMPurify; Vite 6
  build. KaTeX and a panel library were dropped (size, API churn).
- `{{placeholder}}` substitution in `text` is in v1 because loops need it; it is small.
- Threads: only main-thread breakpoints are supported in v1 (documented).
- Screenshots use a 1440x900 viewport at scale 1 by default, which matches what the
  built-in browser pane showed during development; agents can pass other sizes.
