# Research notes: stack for agent-authored visual code walkthroughs

Date: 2026-10-28. Status: research done; the open questions at the end were settled the same day, see [spec.md](spec.md).

## 1. What we are building, in one paragraph

A toolkit that lets an agent (Claude Code or similar) turn a Python codebase into a
"debug-mode" walkthrough: the agent defines breakpoints, and for each one says which code
to show, which objects or plots to display, which part of the project schema to highlight,
and what to explain. The toolkit runs the example, captures everything at each breakpoint,
and renders a five-pane viewer (schema on top, code left, objects/plot right-top,
explanation right-bottom, navigation at the bottom).

The architecture that makes this cheap to build and to extend is a strict split:

```
 walkthrough.py (agent writes)  ──►  recorder (Python, runs the target)  ──►  steps.json  ──►  viewer (browser)
```

`steps.json` is the contract. A recorded walkthrough is a list of step payloads; a future
live mode just streams the same payloads over a WebSocket. The viewer never knows the
difference.

## 2. Prior art and what to borrow

| Project | What it is | Borrow |
|---|---|---|
| [CodeTour](https://github.com/microsoft/codetour) (VS Code) | JSON "tours": steps anchored at `file` + `line` (or a regex `pattern`), markdown `description`, playback with Next/Prev. No runtime values. | The step-anchoring model (`file:line` or pattern), markdown per step, the idea that a tour is a small declarative file beside the repo. |
| [Python Tutor](https://github.com/ph-kather/OnlinePythonTutor) | Runs code under `bdb`, emits a JSON trace, JS frontend steps through it. | Proof that "bdb recorder to JSON to static web frontend" is a solid architecture. |
| [birdseye](https://github.com/alexmojaki/birdseye) | AST-instruments decorated functions, records every expression value, browser UI. | Validates runtime-value capture plus browser UI, but it captures everything; we want curated capture. |
| [python-code-visualizer](https://pypi.org/project/python-code-visualizer/) (Jan 2026) | Library that traces a run and writes an interactive HTML file. | Same "record to self-contained HTML" delivery; automatic rather than curated. |
| [Code Hike](https://pomb.us/) | React/MDX "scrollycoding" code walkthroughs with focus/mark annotations. | Presentation ideas for the code pane (focus lines, dim the rest). Not reused: it is tied to MDX/React authoring. |
| Jupyter display protocol | `_repr_html_`, `_repr_png_`, `_repr_mimebundle_` | Use as a fallback so any Jupyter-aware object renders. See section 4 for why it is only a fallback. |

Nothing found that combines agent-authored curated steps with captured runtime values and
a project-level schema. The pieces exist; the product does not.

## 3. Capture side (Python): verified findings

Probed on this machine (Python 3.14.4) with a `bdb.Bdb` subclass running a script via
`runpy.run_path(..., run_name="__main__")`:

- **Non-invasive breakpoints work.** `set_break(file, line)` + `user_line()` stops at the
  line, `eval(expr, frame.f_globals, frame.f_locals)` evaluates display expressions in the
  paused scope, `set_continue()` resumes. The target code is never modified.
- **Both backends work.** Python 3.14 added `Bdb(backend="monitoring")` built on
  `sys.monitoring` ([PEP 669](https://peps.python.org/pep-0669/)); the default `settrace`
  backend keeps compatibility with 3.10 to 3.13. bdb only installs a local trace in frames
  whose file has a breakpoint, so untouched hot loops and C-backed libraries (numpy, pandas,
  torch) run at near-native speed either way.
- **A breakpoint at line N stops before line N runs.** Same as every debugger. The spec
  must say this clearly, and the authoring helper should offer `after="file:line"` sugar
  (internally: break on the next executable line) because agents will otherwise put the
  break on the assignment they want to inspect.
- **Loops hit a breakpoint repeatedly.** Needs an explicit policy per step:
  first hit (default), nth hit, every hit (one sub-step per iteration), or a condition
  expression evaluated in the frame.
- **The recorder must run inside the target project's interpreter** so imports resolve.
  `uv run --with <our-package> python -m <our-package> record walkthrough.py` does this
  without installing anything permanently; pip-installing into the project venv also works.
- Alternatives considered and rejected for v1: `debugpy`/DAP (heavy, only needed for a
  real IDE-style live debugger), AST instrumentation (birdseye-style, invasive, captures
  too much), `sys.settrace` by hand (bdb already does the bookkeeping).

## 4. Object and plot display: verified findings

IPython's `DisplayFormatter` run outside Jupyter (checked with pandas, matplotlib, plotly):

| Object | MIME types returned |
|---|---|
| `DataFrame` | `text/html`, `text/plain` |
| `Series`, `ndarray`, `dict` | `text/plain` only |
| matplotlib `Figure` | `text/plain` only (`_repr_html_` exists but returns nothing without the webagg backend) |
| plotly `Figure` | nothing (`_repr_mimebundle_` needs a renderer), but `fig.to_json()` works |

So the display protocol is not enough on its own. We need a small serializer registry that
produces a typed "display" union the viewer knows how to render:

- `table` for DataFrame/Series (head N rows + shape + dtypes, as JSON, not HTML, so the
  viewer can style it),
- `image` (PNG or SVG, base64) for matplotlib figures, PIL images, anything with
  `_repr_png_`/`_repr_svg_`,
- `plotly` (figure JSON) for plotly figures, rendered interactively in the viewer,
- `json` tree for dicts, lists, dataclasses, pydantic models,
- `array` summary for numpy/torch (shape, dtype, min/mean/max, small preview),
- `text` fallback (`repr`, truncated).

Jupyter `_repr_*_` methods are consulted before the `text` fallback, so custom classes
that already render in notebooks render here too.

## 5. Viewer side: options

### Option A (recommended): prebuilt static web viewer, shipped inside the Python package

- Vite + React + TypeScript, built once into a single `index.html` with
  [vite-plugin-singlefile](https://github.com/richardtallent/vite-plugin-singlefile); the
  Python package embeds that template and injects `steps.json`. Users and agents never run
  Node; only tool developers do.
- Output is one self-contained HTML file: open it, share it, or serve it with
  `codewalk serve`. The Claude desktop app's browser pane can open it, so the agent can look
  at what it built.
- Component picks:
  - Code pane: [Shiki](https://shiki.style/guide/) with a fine-grained bundle (Python
    grammar + one theme + the JavaScript regex engine, no wasm) for VS Code-quality
    highlighting with current-line and focus-range highlighting. Lighter fallback: Prism.
    Alternative: run Pygments at record time and ship HTML; simplest, but then the JSON
    carries presentation and live mode has to do the same on the server.
  - Schema pane: [Mermaid](https://mermaid.js.org/) `render()` per step, highlighting the
    current node by appending a `classDef active` + `class <id> active` to the definition
    before rendering. Agents write Mermaid fluently; a linear stage list can be converted to
    a Mermaid flowchart automatically. Alternative: [React Flow](https://reactflow.dev/examples/layout/auto-layout)
    with dagre/ELK auto-layout from nodes/edges JSON; richer (clickable nodes, nested
    groups) but more code and less natural for agents to author.
  - Explanation pane: `react-markdown` + `remark-gfm`, optional KaTeX for formulas.
  - Objects pane: tabs, one per captured object; table / image / plotly / json-tree / text
    renderers. Plotly's basic bundle is roughly 1 MB minified, so load it lazily only when a
    recording contains plotly displays.
  - Layout: CSS grid + `react-resizable-panels`; keyboard Left/Right for Prev/Next.

### Option B: Python-native UI (Streamlit, Panel, NiceGUI)

No JavaScript toolchain, a first version in a day. Costs: Streamlit reruns the whole
script on every click, code blocks cannot highlight a current line without a custom
component, Mermaid and schema highlighting need custom components anyway, nothing is
shareable as a file, and a server must run for viewing. Panel/NiceGUI are more flexible but
you end up writing the same custom JS components, now inside a Python framework.
Reasonable only if avoiding Node entirely is a hard requirement.

### Option C: VS Code extension (CodeTour-style)

Best code pane for free (the editor itself), but the schema/objects/explanation panes
become webviews anyway, and the walkthrough is only viewable inside VS Code. Not for v1.

## 6. Agent-facing tooling (the actual product surface)

- **Authoring DSL in Python** (typed, validated, IDE-friendly). Sketch:

```python
from codewalk import Walkthrough

w = Walkthrough(
    title="How the training pipeline works",
    entry="scripts/train.py --config configs/small.yaml",  # what to run
    schema="""
    flowchart LR
      load[Load data] --> clean[Clean] --> feat[Features] --> train[Train] --> eval[Evaluate]
    """,
)

w.step(
    at="src/data/load.py:42",             # pause BEFORE this line runs
    highlight="load",                     # schema node id
    code="src/data/load.py:30-55",        # left pane; default = enclosing function
    show={"raw": "df.head(10)", "shape": "df.shape"},   # evaluated in the paused frame
    plot="df['price'].plot.hist().figure",
    text="""We start by reading the raw CSV ...""",   # markdown
    hit=1,                                # or "all", or n, or condition="epoch == 3"
)
```

- **CLI**: `codewalk check` (files and lines exist, expressions parse, schema node ids
  exist), `codewalk record` (runs and writes `steps.json` + `index.html`),
  `codewalk serve` (local server with reload), `codewalk screenshot` (optional, via
  Playwright, so a headless agent can verify the result).
- **SKILL.md** shipped with the package: the authoring workflow for Claude Code
  (read the codebase, draw the schema, pick 8 to 15 breakpoints, write `walkthrough.py`,
  check, record, view, iterate). This is what makes the tool "quick" for an agent.
- **Validation errors written for agents**: exact file:line, the expression that failed and
  the names available in the frame.

## 7. Recommended stack, summarised

| Layer | Choice | Why |
|---|---|---|
| Capture | `bdb.Bdb` subclass, `runpy`, `monitoring` backend on 3.14+ | stdlib, non-invasive, verified |
| Serialisation | small registry + Jupyter `_repr_*_` fallback | display protocol alone is insufficient outside Jupyter |
| Spec | Python DSL, pydantic or dataclasses for validation | agents write Python well; typed errors |
| Package / CLI | `uv`-managed, `typer` | run inside the target env with `uv run --with` |
| Viewer | Vite + React + TS, Shiki, Mermaid, react-markdown, plotly (lazy) | full layout control, single-file output |
| Live mode (later) | FastAPI WebSocket streaming the same step payloads | zero change to the viewer |

## 8. Open questions (settled 2026-10-28, recorded in spec.md section 2)

Decisions: 1 recorded, 2 external file:line, 3 web viewer, 4 Mermaid, 5 pandas + numpy/torch + matplotlib/images (no plotly in v1), 6 pipelines + OO systems + algorithms, 7 to 9 defaults kept, plus a Playwright screenshot command.

1. Recorded playback vs live stepping for v1. Default: recorded, live-ready payload.
2. Breakpoints in an external `walkthrough.py` (file:line, never touching the target) vs
   inline `checkpoint()` calls. Default: external, inline as escape hatch.
3. Viewer: prebuilt web bundle shipped in the package vs Python-native UI. Default: web.
4. Schema authoring: Mermaid (+ stage-list shortcut) vs structured React Flow vs linear
   strip only. Default: Mermaid.
5. Object and plot libraries to support in v1. Default: pandas, numpy, matplotlib, plotly,
   plain Python containers; torch/PIL as cheap extras.
6. Primary kind of codebase (ML/data pipelines vs services vs libraries). Default: pipelines.
7. Loop policy default. Default: first hit; `hit="all"` creates one sub-step per iteration.
8. Python floor. Default: 3.10+ (settrace backend), monitoring backend auto-selected on 3.12+.
9. Agent self-verification: is a Playwright screenshot command worth including in v1?
   Default: yes, optional dependency.

## Sources

- bdb backend parameter: https://docs.python.org/3/library/bdb.html
- PEP 669 low-impact monitoring: https://peps.python.org/pep-0669/
- CodeTour: https://github.com/microsoft/codetour
- Python Tutor developer overview (bdb-based tracer): https://github.com/ph-kather/OnlinePythonTutor
- birdseye: https://github.com/alexmojaki/birdseye
- python-code-visualizer: https://pypi.org/project/python-code-visualizer/
- Code Hike: https://pomb.us/
- IPython formatters: https://ipython.readthedocs.io/en/stable/config/integrating.html
- Shiki guide and bundles: https://shiki.style/guide/ , https://shiki.style/guide/bundles
- Mermaid render API: https://www.mintlify.com/mermaid-js/mermaid/api/methods/render
- React Flow auto layout: https://reactflow.dev/examples/layout/auto-layout
- vite-plugin-singlefile: https://github.com/richardtallent/vite-plugin-singlefile
- plotly.js partial bundles: https://github.com/plotly/plotly.js/tree/master/dist
- Streamlit vs Panel comparison: https://panel.holoviz.org/explanation/comparisons/compare_streamlit.html
