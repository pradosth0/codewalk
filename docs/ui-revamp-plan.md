# Viewer revamp plan (UI/UX)

Status: proposal of 2026-11-05; all five phases implemented the same day with the
recommended defaults (explanation above the objects, outline closed by default, a
system / light / dark control, run metadata in a popover with warnings kept visible).
Scope: the viewer only (`viewer/`), plus the small Python touch points that depend on its
DOM (`codewalk/screenshot.py`) and the docs that show it. The DSL, the recorder and
`steps.json` do not change.

## What the viewer is today

One self-contained page per recording. A header holds the title and a Mermaid schema
with the current stage lit; under it a 2x2 grid: code (left), captured objects (top
right), explanation (bottom right); a footer carries every control: Prev, Up, Down, the
counter, the level badge, the step title, the location, "walk at 1 2 3", console, Next.
Theme follows the OS. Before step 1 an "intro" view shows the description in the
explanation pane and leaves the other panes empty.

Before pictures: `out/demo/screenshots/00-intro.png` (intro), `01-load.png` (a key step
with a table), `13-epoch.3.png` (a loop hit with a plot), `12-grad.png` (a line-by-line
step), `20-report.png` (last step, console).

## Findings

### Usage friction, most important first

1. **The first screen is empty.** The intro shows "no code for this step" and "no objects
   at this step" in two large blank panes, with the description squeezed into the
   bottom-right box. A reader does not learn what they are about to see or how to move.
2. **No outline.** With 20 steps in 3 levels there is no way to see the whole walk, where
   the current step sits in it, or to jump to a step. The only jump is clicking a schema
   node, which has no hover state, so nobody finds it. The spec lists an outline panel
   under "Later".
3. **The footer carries ten controls and overflows.** Below about 1100px the "console"
   and "Next" buttons leave the screen (verified at 1000x700 and 768x1024). "walk at
   1 2 3" explains nothing by itself, and the location text repeats the code pane header.
4. **Position is hard to read.** The counter says "1 / 6" on a key step and "2 / 17" one
   Down later: the denominator changes with the level. Nothing on the step itself says
   "this step has 4 details" except a small enabled Down button at the far left.
5. **Clicking a schema node lands on the wrong step.** It jumps to the first step that
   highlights the node, which is usually a level-2 detail (Clean goes to "Drop duplicated
   rows", not the "Clean the frame" key step), and from there Next walks level 2.
6. **Space is badly shared.** The explanation pane keeps 42% of the right column whatever
   the text length, so most steps show 150px of empty prose area while the table above is
   cut to 8 columns and the plot shrinks. The code pane keeps 55% of the width for
   functions of 10 to 20 lines, leaving the lower half blank.
7. **The explanation is the last thing the eye reaches.** It is the author's voice and
   the reason the page exists, but it sits in the smallest pane, under a mono bold
   header, with the breadcrumb crammed into the same line at 50% width.
8. **Every step change flickers.** The schema is re-rendered by Mermaid on each step and
   the code is shown unstyled until Shiki finishes, so the page jumps twice per Next.
9. **Nothing is adjustable or remembered.** No theme toggle (OS only), splitter positions
   reset on reload, no way to hide the schema or enlarge one pane, no keyboard help.
10. **Below 900px the layout is unusable**: panes never stack, the schema overflows, the
    header takes 175px. Tablets are a realistic case for a walkthrough someone was sent.
11. Small things: auto titles like "One gradient step (hit 3)"; "no explanation for this
    step" as the only content of a pane; the tab labels shout their kind in uppercase
    (TABLE, JSON, ARRAY); the console is a dot on a button; no focus rings for keyboard
    users; the empty-state copy "Press Next (→)" is the only onboarding.

### Visual

- **No identity.** GitHub-grey panels, 1px borders everywhere, the same `bg-2` for every
  header, system fonts at 12 to 14.5px with no scale. It reads as a debugging utility,
  not as a document someone wrote for you.
- **The schema looks like default Mermaid**: square boxes, black arrows, a blue block for
  the current node; in dark mode the done nodes turn navy with no other cue.
- **Competing highlights**: the current line is yellow, the focus range pale blue, the
  accent blue, the done nodes another blue, the dimmed lines at 45% opacity. Too many
  signals of equal weight.
- **Plots are white rectangles in dark mode**, with a hairline border and no breathing
  room.
- **Controls are text with glyphs** ("◀ Prev", "▲ Up", "walk at 1 2 3") in three sizes
  and two weights, with no hierarchy beyond one filled Next button.

## Direction

Three rules for every decision below.

- **It is a document, not an IDE.** The reader follows a story the author wrote. The
  explanation, the schema and the step title get the hierarchy; code and objects are
  evidence next to them.
- **One accent, one current-ness.** A single accent colour marks "where you are" in the
  schema, the outline, the code gutter and the progress bar. Everything else is neutral.
- **Calm transitions.** Nothing re-lays out when a step changes; content crossfades,
  the schema node and the progress bar animate, and the page respects reduced motion.

### Proposed desktop layout

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ ≡ outline   How the demo pipeline trains a rentals model      ⌨ ?  ☾  ⋯      │  40px
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━░░░░░░░░░░  │  progress
├──────────────────────────────────────────────────────────────────────────────┤
│   (raw.csv) ─▶ ✓ Load ─▶ ● Clean ─▶ Features ─▶ Train ─▶ Evaluate ─▶ Report  │  ~80px, collapsible
├──────────────────────────────────────────────────────────────────────────────┤
│ Overview · 2 of 6 ‹ Clean the frame ›  ▾ 4 details    demo/clean.py:30 ↩ return │  step header
├────────────────────────────────┬─────────────────────────────────────────────┤
│ code (file · fn · paused chip) │ explanation (auto height, 15px/1.6, 70ch)   │
│  14  def clean(raw):           │ `clean` returns the cleaned frame and …     │
│  ..                            ├─────────────────────────────────────────────┤
│ ▶30      return df, report     │ ▤ report  ▦ clean  ▦ summary                │
│                                │ objects (takes the remaining height)        │
│                                │                                             │
├────────────────────────────────┴─────────────────────────────────────────────┤
│ ‹ Prev                      ● ● ○ ○ ○ ○   (6 key steps)            Next ›     │  48px
└──────────────────────────────────────────────────────────────────────────────┘
```

- The **top bar** is 40px: outline toggle, title, help, theme, and a menu for the
  metadata that is in the header today (entry, Python, duration, warnings).
- The **progress bar** spans the key steps; it fills as the reader advances, sub-steps
  fill the current segment.
- The **schema** keeps Mermaid for flowcharts but is styled with our tokens; list schemas
  render as an HTML stepper. The strip can be collapsed and the state is remembered.
- The **step header** replaces the footer's clutter: level and position, breadcrumb,
  title, a "4 details" chip that is also the Down button, Up when inside details, and
  the location chip (file:line plus before / after / return / crashed).
- The **explanation moves above the objects** and sizes to its content (min 3 lines, max
  45% of the column, then scrolls). Objects take the rest. The splitter stays for
  manual override, and double-clicking a pane header maximises it.
- The **footer** is Prev, a step rail, Next. Nothing else.
- The **outline drawer** (left, 280px, `o`) lists the steps as a tree grouped by level:
  current highlighted, visited ticked, each row with its schema node. It also holds the
  detail selector as a labelled segmented control ("Overview / Walkthrough / Line by
  line") with one line of help.
- The **intro** becomes a landing card in the main area: title, description, the list of
  key steps with their stages, "Start" and the keyboard legend.

Below 1100px the step header wraps and the footer drops the rail; below 900px the panes
stack (explanation, objects, code) with the schema scrolling horizontally under a
sticky top bar and the footer sticky at the bottom.

## Plan by phase

Each phase ships on its own, keeps `npm run build` green and the Playwright tests
passing, and ends with regenerating `out/demo` screenshots and the two README images.

### Phase 0: foundations (S)

- `styles.css` becomes tokens plus one file per area: spacing (4px scale), radii, a type
  scale (12 / 13 / 14 / 15 / 17 / 22), semantic colours (`--accent`, `--current`,
  `--focus`, `--done`, surfaces 0 to 3), light and dark, with `data-theme` on `<html>`.
- Theme control: system / light / dark, persisted in `localStorage`; the OS default stays
  the default so `screenshot --dark` keeps working through `prefers-color-scheme`.
- `:focus-visible` rings, `prefers-reduced-motion`, a `<noscript>`-free fallback for the
  fatal state. Fonts stay the system stack: the page is one 4 MB file and must open from
  disk; embedding Inter would add 300 KB for little.

### Phase 1: shell and navigation (L)

- `TopBar`, `ProgressBar`, `StepHeader`, `Footer` replace `NavBar`; `App.tsx` becomes
  the shell. Up/Down move to the step header; the "details" chip shows the count.
- `Outline` drawer with the tree, the detail selector and keyboard focus handling; `o`
  toggles it, Escape closes it. The outline is derived from `outline.ts` as it is.
- `Intro` landing card with the key-step list and a Start button; the empty panes go.
- Schema click goes to the step of the node at the current detail level (the key step
  when walking at level 1), and a hover tooltip names it.
- The right column becomes explanation-above-objects with content-sized height; splitter
  positions and the schema collapsed state persist.
- Responsive rules at 1100px and 900px as sketched. Remove the `minmax(200px, 320px)`
  title column and the 120px minimum header.
- `screenshot.py` selectors (`.app[data-step]`, `.schema[data-settled]`,
  `.code[data-settled]`) are kept verbatim; `test_screenshot.py` still passes.

### Phase 2: pane polish (M)

- Code: gutter with a 3px accent bar on the current line instead of a yellow row, the
  marker glyph in the gutter, focus range as a left rule with the rest at 70% instead of
  45%, a "paused before line 23" chip in the header. Pre-tokenise every code window once
  at load (20 to 40 small windows) so there is never unstyled code; keep the previous
  tokens until the new ones arrive as a second guard.
- Objects: an icon per kind replaces the uppercase label; the expression and type form
  one subtle sub-header; tables get zebra rows, a sticky index column and a column count;
  plots sit centred in a padded card with rounded corners and a click-to-enlarge
  lightbox; JSON gets a copy button and matching type colours.
- Inline `code` in the explanation that names a captured object becomes a chip: hover
  highlights the tab, click selects it. This makes "look at the `dtypes` tab" work.
- Explanation typography: 15px / 1.6, 70ch measure, real heading and list styles,
  quieter "no explanation" state.
- Console becomes a drawer under the code pane with a line count badge in the step
  header; hidden when there is no output.

### Phase 3: schema (M)

- Mermaid `themeVariables` from our tokens and a CSS pass over the SVG: 8px radius,
  1.5px borders, done nodes muted with a ✓, the current node filled with the accent and
  a soft ring, upcoming nodes outlined, arrows in `--border`.
- Render the SVG once per recording and toggle classes per step instead of re-rendering,
  so the strip never reflows; the `data-settled` contract stays (it becomes "classes
  applied").
- List schemas (`schema=[...]`) render as an HTML stepper with the same states; it is
  responsive and needs no Mermaid at all.
- Hovering a node shows "3 steps · Overview" and clicking it opens a small popover with
  the node's steps when there is more than one.

### Phase 4: motion and keyboard (S)

- 150ms crossfade for explanation and objects, a slide for the code current line, the
  progress segment and the schema node fill animate; all off under reduced motion.
- `?` opens a shortcuts overlay. Shortcuts: ← → (also Space, PageUp/Down), ↑ ↓, Home,
  End, `o` outline, `c` console, `t` theme, `s` schema, `1`/`2`/`3` detail level, `f`
  maximise the focused pane.

### Phase 5: accessibility and verification (S)

- Landmarks (`header`, `nav`, `main`, `aside`), `aria-current` on the schema node and
  the outline row, a live region announcing "Step 3 of 6, Build the design matrix", 44px
  targets under 900px, contrast checked on both themes (muted text on surfaces is the
  risk).
- Bundle budget: at most the current 4.1 MB; no new runtime dependency heavier than
  20 KB. Regenerate the demo screenshots, the README images and update spec section 8.
  Outcome: 4.15 MB (+1.3%, all viewer code, no new dependency); the token pairs are
  checked by `tests/test_tokens_contrast.py`.

## Constraints kept

- `steps.json` and the DSL are untouched; old recordings re-render with
  `codewalk build`.
- The page stays one file that opens from `file://`; no web fonts, no network.
- The automation hooks and the `?step=` deep links stay as they are.
- Keep React 19, Shiki 3, Mermaid 11, react-markdown; no panel or UI library.

## Out of scope

Live mode, editing in the viewer, Plotly, a phone-first layout (phones get the stacked
layout and nothing more), and changes to how walkthroughs are authored.

## Decisions to take before phase 1

1. Explanation above the objects (recommended, content-sized) or kept below them?
2. Should the outline drawer be open by default on wide screens (≥ 1440px)?
3. Is a manual theme toggle wanted, or is following the OS enough?
4. Does the title block's metadata (entry, Python version, duration, warnings) belong
   in a menu, or should it stay visible for agents reviewing their work?
