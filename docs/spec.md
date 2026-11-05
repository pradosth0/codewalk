# Spec: codewalk, agent-authored visual walkthroughs of Python code

Version 0.4, 2026-11-05. Decisions below were taken with the project owner; see
[research.md](research.md) for the options that were weighed. `codewalk` is a placeholder
name for the package and CLI. Implemented: milestones 1 to 4 (DSL, `check`, recorder,
all display kinds, the viewer, `build`, `serve`, the demo pipeline, `screenshot`, `init`,
the agent skill, and levels of detail with Up/Down navigation).

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
| `levels` | list[str], optional | Names for the levels of detail, index 0 = level 1 (e.g. `["Overview", "Walkthrough", "Line by line"]`). Shown in the viewer; levels are numbered when absent. |

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
| `level` | int >= 1, default 2 | Level of detail: 1 for the key steps a reader sees first, 2 for the normal walk, 3 and beyond for line-by-line detail. Not limited to three. |
| `parent` | str, optional | Id of the step that summarises this one, when the default rule (section 4.4) is not what you mean. Must be a shallower step. |

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

### 4.4 Levels of detail

Readers should be able to walk the whole program in a few key steps and then deep-dive
into one part without re-prompting the agent. Every step carries a `level`; nothing
forces three, but the skill prescribes three by default: 1 for what a project manager
needs (one key step per schema node, showing the stage's result), 2 for a teammate who
must understand and vouch for the output, 3 for line-by-line understanding of the
non-obvious parts.

The hierarchy is derived from the recorded sequence by one rule (`outline.py`):

- a deeper step belongs to the first shallower step recorded after it: **a key step
  summarises the deeper steps recorded before it**, back to the previous step at its
  level. Key steps therefore sit where a stage's result is visible, at the function's
  return or in the caller right after the call;
- deeper steps with no shallower step after them (trailing details) hang off the last
  shallower step before them; `check` warns;
- `parent="id"` overrides the rule for one step. With `hit="all"` parents, the first
  instance recorded after the step is used, else the last one before it.

`check` also warns when a key step pauses at a function's entry and is followed by
deeper steps, because those will belong to the *next* key step. Declaration order must
still follow first execution, so a `hit="all"` loop step is declared before the
line-by-line steps inside one of its iterations.

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
  "version": 2,
  "title": "How the demo pipeline trains a model",
  "description": "markdown or empty",
  "entry": "run.py --rows 500",
  "recorded_at": "2026-10-28T10:42:00Z",
  "python": "3.14.4",
  "schema": { "kind": "mermaid", "source": "flowchart LR\n  load[Load CSV] --> ..." , "nodes": ["load", "clean", "..."] },
  "levels": ["Overview", "Walkthrough", "Line by line"],   // optional names, index 0 = level 1
  "warnings": ["step 'x' never reached"],
  "steps": [
    {
      "id": "load",
      "index": 1,                       // 1-based; sub-steps are "7.1", "7.2" in `label`
      "label": "1",
      "title": "Read the raw CSV",
      "location": { "file": "src/demo/load.py", "line": 18, "function": "load_csv", "hit": 1, "elapsed": 0.03 },
      "highlight": ["load"],
      "level": 1,                       // level of detail (section 4.4)
      "parent": null,                   // id of the summarising step, filled by the recorder
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

Layout (revamp of 2026-11-05, phases 0 and 1 of [ui-revamp-plan.md](ui-revamp-plan.md)):

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ ≡ Outline   title                                        ⓘ  ⌨  ☾ (theme)     │  top bar + progress line
├──────────────────────────────────────────────────────────────────────────────┤
│   (raw.csv) ─▶ Load ─▶ [Clean] ─▶ Features ─▶ Train ─▶ Evaluate ─▶ Report   │  schema strip (collapsible)
├──────────────────────────────────────────────────────────────────────────────┤
│ Overview · step 2 of 6 · in …       Clean the frame        ↑ Up   ▾ 4 details │  step header
├────────────────────────────────┬─────────────────────────────────────────────┤
│ code (file · fn · paused chip) │ explanation (sized to its text, max 45%)    │
│ gutter, current line, focus    ├─────────────────────────────────────────────┤
│ [program output drawer]        │ objects (tabs; takes the remaining height)  │
├────────────────────────────────┴─────────────────────────────────────────────┤
│ ‹ Prev                   ● ● ○ ○ ○ ○  (key steps)                    Next ›  │  footer
└──────────────────────────────────────────────────────────────────────────────┘
```

Implemented in `viewer/` (Vite 6, React 19, TypeScript, strict):

- Shell: `TopBar` (outline toggle, title, warnings and run metadata popovers, keyboard
  help, theme control) with a progress line that fills per key step and per detail inside
  the current segment (`outline.ts` `progressAt`); `SchemaStrip`; `StepHeader`; the three
  panes; `Footer` (Prev, a rail of key-step dots, Next). Before step 1 a non-empty
  `description` renders as an `Intro` landing card: eyebrow, title, description, the key
  steps with their stage and number of details, Start, keyboard legend, run metadata.
- Navigation: Prev/Next walk the steps at the current step's level (deeper steps are
  skipped); Down enters the first detail of the current step and Up jumps to the step
  that summarises it (`outline.ts`, mirroring `outline.py`). The `Outline` drawer (`o`)
  lists the steps as a tree with the current one marked, visited ones ticked and steps
  deeper than the current level greyed; its level selector walks at that level, climbing
  to the summary when the current step is deeper. Keyboard: ← → (and Space, PageUp/Down)
  at the current level, ↓ ↑ between levels, Home/End, `1`..`9` level, `o` outline, `s`
  schema, `c` output, `t` theme, `f` maximises the pane under the pointer, `?` opens the
  shortcuts overlay, Esc restores a maximised pane or closes the outline, a menu or the
  overlay.
  `?step=<id>` deep links (`<label>` and 1-based numbers also work); the URL follows the
  current step. With a single level, Up/Down and the selector are hidden.
- Schema strip: a linear `flowchart LR` (what `schema=[...]` produces) is drawn as an
  HTML stepper (`chain.ts`, `Stepper.tsx`): stages ahead outlined, visited ones muted
  with a tick, the current one filled with the accent; data stores (`[( )]`) as dashed
  pills. Any other schema is rendered once per recording and theme by Mermaid 11 with
  `theme: 'base'` and variables from the tokens (`mermaid.ts`); node states are then
  applied to the SVG (inline styles using the CSS variables, rounded rects, a tick badge
  on visited nodes, a glow on the current one) without re-rendering, so the strip never
  reflows between steps. Hovering a stage names its step; clicking opens the step, or a
  menu of the stage's steps when there are several. The strip collapses (`s`) to one
  line of stage names; labels are parsed from the Mermaid text (`schemaLabels.ts`).
- Code pane: Shiki 3 fine-grained bundle (Python grammar, github-light/dark, JavaScript
  regex engine). Every code window is tokenised once and cached (`highlight.ts`); the
  whole recording is pre-tokenised in the background after the first render, so a step
  never shows plain text. Header: file, function, line window and a chip saying where the
  program is paused (before / after / returning / crashed, hit count). Current line
  tinted with an accent bar in the gutter, focus lines marked with a rule and the rest
  dimmed, current line centred in the code box (never the page). The program output
  drawer (`c`, or the chip in the step header) docks under the code.
- Right column: the explanation sits above the objects and sizes to its text (at most 45%
  of the column); the splitter overrides it, double-click returns to automatic. Inline
  code in the explanation that names a captured object is a chip: hovering it highlights
  the tab, clicking opens it (`Md.tsx`). Objects: one tab per object with an icon for its
  kind, the `plot` entry first; the chosen name is kept across steps. A Copy button gives
  JSON, text, and tables or array previews as tab-separated text. Tables have zebra rows
  and a sticky index column; figures sit in a padded card and open in a lightbox. Any
  pane maximises from its header button or a double-click; Esc restores.
- Theme: design tokens in `styles/tokens.css` (surfaces, one accent, current/focus,
  status colours, type scale) with `data-theme` on `<html>`; `index.html` sets it before
  paint from `localStorage` or `prefers-color-scheme`, `useTheme` keeps it current. The
  preference (system / light / dark), the splitter positions, the outline and the schema
  state persist in `localStorage` under `codewalk.*` (`prefs.ts`), guarded for `file://`.
- Motion: a step change fades the explanation, the objects and a new code window in
  (150 to 180 ms), the current line flashes briefly, the progress line, the rail dots
  and the schema nodes transition; popovers, menus, the outline and the overlay enter
  with the same short curves. `prefers-reduced-motion` cancels all of it, and
  `codewalk screenshot` captures with animations disabled.
- Responsive: under 1100px the outline overlays, the footer rail and button labels go;
  under 900px the panes stack (explanation, objects, code), the main area scrolls and
  every control is at least 44px tall.
- Accessibility: landmarks (`header`, the schema `section`, `main`, `aside` for the
  outline, `footer`), a polite live region announcing "Step n of m: title", `aria-current`
  on the current stage (stepper, Mermaid node, collapsed strip), the current outline row
  and the current rail dot. Everything works from the keyboard: Mermaid stages are
  buttons (Tab, Enter), the object tabs follow the ARIA tabs pattern (← → Home End move
  between tabs without changing the step), the splitters are focusable separators
  (arrows resize by 2%, Home resets), the stage menu and the outline take the focus when
  they open (↑ ↓ in the menu), the shortcuts overlay traps Tab and returns the focus on
  close. Colour: `tests/test_tokens_contrast.py` checks every text pair of
  `tokens.css` against WCAG AA (4.5:1, 3:1 for the large and non-text pairs) in both
  themes; the accent is split into `--accent` (text) and `--accent-fill` (white text on
  it) because in dark mode one blue cannot satisfy both. Known exception: 1px hairline
  borders stay below the 3:1 non-text ratio by design; every bordered control also has
  a text label or a fill that passes.
- Build: `npm run build` type-checks and runs Vite with `vite-plugin-singlefile`, writing
  one file to `src/codewalk/viewer/index.html` (4.15 MB after the revamp, 4.09 MB
  before it, almost all of it Mermaid; no runtime dependency was added), which is
  committed and shipped in the wheel, so `pip install` needs no Node. The template keeps
  `<script id="codewalk-data" type="application/json">__CODEWALK_DATA__</script>` and a
  `__CODEWALK_TITLE__` placeholder; `codewalk/build.py` replaces both, escaping `</` in
  the JSON so the data block cannot be closed early. In `vite dev` the app loads
  `viewer/fixtures/steps.json` instead (`.claude/launch.json` has a `viewer-dev` entry).

### 8.1 Automation hooks

The viewer marks the root element with `data-step="<id>"` (`intro` before step 1) and
every pane that renders asynchronously (the schema, the code) with `data-settled="true"`
once it matches the current step. `codewalk screenshot` waits for the step, then for every
`[data-settled]` element to be `true`, for `document.fonts` and for every image to be
decoded before capturing; other automation can do the same.

## 9. CLI

```
codewalk init [DIR] [--entry "run.py --flag"] [-o PATH] [--force]   # scaffold walkthrough.py that passes check
codewalk check walkthrough.py                                       # static validation, exit 1 on errors
codewalk record walkthrough.py [-o out/] [--strict] [--timeout S] [--backend settrace|monitoring] [--json-only]
codewalk build out/steps.json [-o out/index.html]                   # rebuild the page, e.g. after a viewer upgrade
codewalk serve out/ [--port 8731] [--host 127.0.0.1] [--open]       # static server, Cache-Control: no-store
codewalk screenshot out/ (--all [--level N] | --step ID ...) [-o DIR|file.png] [--width 1440 --height 900] [--dark] [--timeout S]
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
the walkthrough has a description). `--all --level 1` renders the overview only. A single
`--step` may be written to a `.png` path.
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
    outline.py                    # levels of detail: parent assignment (summary-after rule)
    cli.py                        # typer app
    viewer/index.html             # built viewer template (committed)
  viewer/                         # Vite + React + TS source of the viewer
    src/App.tsx, components/{SchemaPane,CodePane,ObjectsPane,TextPane,NavBar,Splitter}.tsx
    src/renderers/{TableView,ArrayView,ImageView,HtmlView,JsonView,TextView,ErrorView}.tsx
    src/{highlight,mermaid,outline,data,theme,types}.ts, styles.css
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
| M5 | Levels of detail: `level=`/`parent=`, summary-after hierarchy, Up/Down navigation, level selector, breadcrumb, `screenshot --level`, demo in three levels | done: the demo records 20 steps in 3 levels with no warnings; the overview is 6 key steps; ↓ from a key step enters its details and ↑ returns |
| Later | Live mode over WebSocket, `plotly` display, nested schemas, an outline panel listing the steps as a tree, automatic levels when none are given, VS Code wrapper, a native `sys.monitoring` tracer for 3.12/3.13 | |

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
