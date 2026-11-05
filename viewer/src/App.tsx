import { useCallback, useEffect, useMemo, useState, type CSSProperties, type SyntheticEvent } from 'react'
import type { ObjectEntry, Recording, Step } from './types'
import { SchemaStrip, type NodeStep } from './components/SchemaStrip'
import { CodePane } from './components/CodePane'
import { ObjectsPane } from './components/ObjectsPane'
import { TextPane } from './components/TextPane'
import { TopBar } from './components/TopBar'
import { StepHeader } from './components/StepHeader'
import { Footer } from './components/Footer'
import { Outline } from './components/Outline'
import { Intro } from './components/Intro'
import { ConsoleDrawer } from './components/ConsoleDrawer'
import { ShortcutsOverlay } from './components/ShortcutsOverlay'
import { Splitter } from './components/Splitter'
import { useTheme } from './theme'
import { usePref } from './prefs'
import { schemaLabels } from './schemaLabels'
import {
  ancestors,
  buildOutline,
  effectiveLevel,
  firstChild,
  keySteps,
  levelName,
  nextAt,
  parentOf,
  positionAt,
  prevAt,
  progressAt,
  segmentOf,
} from './outline'

type PaneId = 'code' | 'objects' | 'text'

function initialPosition(rec: Recording, hasIntro: boolean): number {
  const param = new URLSearchParams(window.location.search).get('step')
  if (param) {
    const byId = rec.steps.findIndex((s) => s.id === param || s.label === param)
    if (byId >= 0) return byId
    const n = Number(param)
    if (Number.isInteger(n) && n >= 1 && n <= rec.steps.length) return n - 1
    if (n === 0 && hasIntro) return -1
  }
  return hasIntro ? -1 : 0
}

function lineCount(text: string): number {
  const t = text.replace(/\n$/, '')
  return t ? t.split('\n').length : 0
}

export default function App({ recording }: { recording: Recording }) {
  const steps = recording.steps
  const hasIntro = recording.description.trim().length > 0
  const min = hasIntro ? -1 : 0
  const max = steps.length - 1
  const [pos, setPos] = useState(() => initialPosition(recording, hasIntro))
  const outline = useMemo(() => buildOutline(steps, recording.levels ?? []), [steps, recording.levels])
  const hasLevels = outline.maxLevel > outline.minLevel
  const [detail, setDetail] = useState(() => outline.minLevel)
  const [showConsole, setShowConsole] = useState(false)
  const [split, setSplit] = usePref('split', 0.55)
  const [vsplit, setVsplit] = usePref<number | null>('vsplit', null)
  const [outlineOpen, setOutlineOpen] = usePref('outline', false)
  const [schemaCollapsed, setSchemaCollapsed] = usePref('schema-collapsed', false)
  const [maximized, setMaximized] = useState<PaneId | null>(null)
  const [helpOpen, setHelpOpen] = useState(false)
  const [lastPane, setLastPane] = useState<PaneId>('code')
  const [selectedObject, setSelectedObject] = useState<string | null>(null)
  const [hintObject, setHintObject] = useState<string | null>(null)
  const { pref: themePref, theme, cycle: cycleTheme } = useTheme()
  const dark = theme === 'dark'
  const labels = useMemo(() => schemaLabels(recording.schema.source, recording.schema.nodes), [recording.schema])

  const goTo = useCallback((i: number) => setPos(Math.min(max, Math.max(min, i))), [min, max])
  const step: Step | null = pos >= 0 ? steps[pos] : null
  const level = effectiveLevel(outline, pos, detail)
  const childIdx = firstChild(outline, pos)
  const parentIdx = parentOf(outline, pos)
  const visible = positionAt(outline, pos, level)
  const crumbs = useMemo(() => ancestors(outline, pos).map((i) => ({ index: i, title: steps[i].title })), [outline, steps, pos])
  const keys = useMemo(() => keySteps(outline), [outline])
  const segment = segmentOf(outline, pos)
  const progress = progressAt(outline, pos)

  // Next/Prev walk the steps at the current level; Down enters the details, Up returns to the summary.
  const next = useCallback(() => {
    const j = nextAt(outline, pos, level)
    if (j >= 0) goTo(j)
  }, [outline, pos, level, goTo])
  const prev = useCallback(() => {
    const j = prevAt(outline, pos, level)
    if (j >= 0) goTo(j)
    else if (hasIntro) goTo(-1)
  }, [outline, pos, level, goTo, hasIntro])
  const down = useCallback(() => {
    if (childIdx >= 0) goTo(childIdx)
  }, [childIdx, goTo])
  const up = useCallback(() => {
    if (parentIdx >= 0) goTo(parentIdx)
  }, [parentIdx, goTo])
  const toggleMax = useCallback((id: PaneId) => setMaximized((m) => (m === id ? null : id)), [])
  // Walking at a shallower level than the current step climbs to the summary at that level.
  const walkAt = useCallback(
    (l: number) => {
      setDetail(l)
      if (pos >= 0 && outline.levels[pos] > l) {
        let p = parentOf(outline, pos)
        while (p >= 0 && outline.levels[p] > l) p = parentOf(outline, p)
        if (p >= 0) goTo(p)
      }
    },
    [pos, outline, goTo],
  )

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const target = e.target instanceof Element ? e.target : null
      if (target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement || (target as HTMLElement | null)?.isContentEditable) return
      if (e.metaKey || e.ctrlKey || e.altKey) return
      const onButton = Boolean(target?.closest('button, a, [role="button"]'))
      switch (e.key) {
        case 'ArrowRight':
        case 'PageDown':
          e.preventDefault()
          next()
          return
        case ' ':
          if (onButton) return // the button handles its own activation
          e.preventDefault()
          next()
          return
        case 'ArrowLeft':
        case 'PageUp':
          e.preventDefault()
          prev()
          return
        case 'ArrowDown':
          e.preventDefault()
          down()
          return
        case 'ArrowUp':
          e.preventDefault()
          up()
          return
        case 'Home':
          goTo(min)
          return
        case 'End':
          goTo(max)
          return
        case 'Escape':
          if (maximized) setMaximized(null)
          else if (outlineOpen) setOutlineOpen(false)
          return
        case '?':
          setHelpOpen((v) => !v)
          return
        case '/':
          if (e.shiftKey) setHelpOpen((v) => !v) // layouts that report the key as '/' with Shift held
          return
        case 'f': {
          // The pane under the pointer right now, else the focused one, else the last one entered.
          const hovered = document.querySelector<HTMLElement>('[data-pane]:hover')?.dataset.pane as PaneId | undefined
          const focused = target?.closest<HTMLElement>('[data-pane]')?.dataset.pane as PaneId | undefined
          const pane = hovered ?? focused ?? lastPane
          setMaximized((m) => (m ? null : pane))
          return
        }
        case 'o':
          setOutlineOpen((v) => !v)
          return
        case 'c':
          setShowConsole((v) => !v)
          return
        case 's':
          setSchemaCollapsed((v) => !v)
          return
        case 't':
          cycleTheme()
          return
        default: {
          const l = Number(e.key)
          if (hasLevels && Number.isInteger(l) && l >= outline.minLevel && l <= outline.maxLevel) walkAt(l)
        }
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [next, prev, down, up, goTo, walkAt, min, max, maximized, outlineOpen, setOutlineOpen, setSchemaCollapsed, cycleTheme, hasLevels, outline, lastPane])

  useEffect(() => {
    try {
      const url = new URL(window.location.href)
      if (step) url.searchParams.set('step', step.id)
      else url.searchParams.delete('step')
      window.history.replaceState(null, '', url)
    } catch {
      /* file:// pages may refuse history updates; deep links still work on load */
    }
  }, [step])

  const active = step?.highlight ?? []
  const done = useMemo(() => {
    const seen = new Set<string>()
    steps.slice(0, Math.max(0, pos)).forEach((s) => s.highlight.forEach((h) => seen.add(h)))
    active.forEach((a) => seen.delete(a))
    return [...seen]
  }, [steps, pos, active])

  // The steps that pause in each schema node, for the strip's tooltips and menus.
  const stepsByNode = useMemo(() => {
    const map = new Map<string, NodeStep[]>()
    steps.forEach((s, i) => {
      const level = outline.levels[i]
      const entry: NodeStep = { index: i, title: s.title, level, levelName: hasLevels ? levelName(outline, level) : null }
      s.highlight.forEach((id) => {
        const list = map.get(id)
        if (list) list.push(entry)
        else map.set(id, [entry])
      })
    })
    return map
  }, [steps, outline, hasLevels])
  const stepsOf = useCallback((id: string) => stepsByNode.get(id) ?? [], [stepsByNode])

  const objects: ObjectEntry[] = useMemo(() => {
    if (!step) return []
    if (step.kind === 'crash') {
      const traceback: ObjectEntry = {
        name: 'traceback',
        expr: '',
        display: { kind: 'text', text: step.traceback ?? '', truncated: false, type: 'traceback' },
      }
      return [traceback, ...step.objects]
    }
    return step.objects
  }, [step])

  const consoleLines = step ? lineCount(step.console) : 0
  // `f` maximises the pane the pointer (or the focus) was last in.
  const trackPane = useCallback((e: SyntheticEvent) => {
    const el = e.target instanceof Element ? e.target : null
    const pane = el?.closest<HTMLElement>('[data-pane]')?.dataset.pane as PaneId | undefined
    if (pane) setLastPane(pane)
  }, [])
  const objectNames = useMemo(() => objects.map((o) => o.name), [objects])
  // A chip in the explanation opens its tab, restoring the layout if the objects are hidden.
  const openObject = useCallback((name: string) => {
    setSelectedObject(name)
    setMaximized((m) => (m === 'text' || m === 'code' ? null : m))
  }, [])
  const mainStyle = {
    '--split': `${split * 100}%`,
    '--vsplit': vsplit != null ? `${vsplit * 100}%` : undefined,
  } as CSSProperties

  return (
    <div className="app" data-step={step ? step.id : 'intro'} data-outline={outlineOpen ? 'open' : 'closed'}>
      <TopBar
        recording={recording}
        levels={outline.maxLevel - outline.minLevel + 1}
        hasLevels={hasLevels}
        outlineOpen={outlineOpen}
        onToggleOutline={() => setOutlineOpen((v) => !v)}
        themePref={themePref}
        onCycleTheme={cycleTheme}
        progress={progress}
        onHelp={() => setHelpOpen(true)}
      />
      {helpOpen && <ShortcutsOverlay hasLevels={hasLevels} onClose={() => setHelpOpen(false)} />}
      <div className="sr-only" aria-live="polite">
        {step ? `Step ${visible.index} of ${visible.count}: ${step.title}` : 'Introduction'}
      </div>
      <div className="body">
        {outlineOpen && (
          <>
            <Outline
              steps={steps}
              outline={outline}
              pos={pos}
              level={level}
              labels={labels}
              onGo={goTo}
              onDetail={walkAt}
              onClose={() => setOutlineOpen(false)}
            />
            <div className="outline-backdrop" onClick={() => setOutlineOpen(false)} />
          </>
        )}
        <div className="content">
          <SchemaStrip
            source={recording.schema.source}
            nodes={recording.schema.nodes}
            labels={labels}
            active={active}
            done={done}
            dark={dark}
            collapsed={schemaCollapsed}
            onToggle={() => setSchemaCollapsed((v) => !v)}
            stepsOf={stepsOf}
            pos={pos}
            onGo={goTo}
          />
          {step && (
            <StepHeader
              step={step}
              levelLabel={hasLevels ? levelName(outline, level) : null}
              visible={visible}
              crumbs={crumbs}
              details={pos >= 0 ? outline.children[pos].length : 0}
              canUp={parentIdx >= 0}
              onUp={up}
              onDown={down}
              onGo={goTo}
              consoleLines={consoleLines}
              consoleOpen={showConsole}
              onToggleConsole={() => setShowConsole((v) => !v)}
            />
          )}
          {step ? (
            <main className="main" data-max={maximized ?? undefined} style={mainStyle} onMouseOver={trackPane} onFocus={trackPane}>
              <CodePane code={step.code} step={step} maximized={maximized === 'code'} onMaximize={() => toggleMax('code')}>
                {showConsole && <ConsoleDrawer text={step.console} onClose={() => setShowConsole(false)} />}
              </CodePane>
              <Splitter direction="horizontal" value={split} onDrag={setSplit} onReset={() => setSplit(0.55)} />
              <div className="right" data-vsplit={vsplit != null ? 'fixed' : 'auto'}>
                <TextPane
                  stepId={step.id}
                  text={step.text}
                  objectNames={objectNames}
                  onSelectObject={openObject}
                  onHoverObject={setHintObject}
                  maximized={maximized === 'text'}
                  onMaximize={() => toggleMax('text')}
                />
                <Splitter direction="vertical" value={vsplit} onDrag={setVsplit} onReset={() => setVsplit(null)} />
                <ObjectsPane
                  stepId={step.id}
                  objects={objects}
                  selected={selectedObject}
                  onSelect={setSelectedObject}
                  hint={hintObject}
                  maximized={maximized === 'objects'}
                  onMaximize={() => toggleMax('objects')}
                />
              </div>
            </main>
          ) : (
            <main className="main intro-main">
              <Intro recording={recording} outline={outline} labels={labels} onStart={next} onGo={goTo} />
            </main>
          )}
          <Footer
            canPrev={pos > min}
            canNext={pos < max}
            onPrev={prev}
            onNext={next}
            keys={keys}
            titles={steps.map((s) => s.title)}
            segment={segment}
            atKey={pos >= 0 && outline.levels[pos] === outline.minLevel}
            onJump={goTo}
          />
        </div>
      </div>
    </div>
  )
}
