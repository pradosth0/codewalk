import { useCallback, useEffect, useMemo, useState } from 'react'
import type { ObjectEntry, Recording, Step } from './types'
import { SchemaPane } from './components/SchemaPane'
import { CodePane } from './components/CodePane'
import { ObjectsPane } from './components/ObjectsPane'
import { TextPane } from './components/TextPane'
import { NavBar } from './components/NavBar'
import { Splitter } from './components/Splitter'
import { usePrefersDark } from './theme'

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

export default function App({ recording }: { recording: Recording }) {
  const steps = recording.steps
  const hasIntro = recording.description.trim().length > 0
  const min = hasIntro ? -1 : 0
  const max = steps.length - 1
  const [pos, setPos] = useState(() => initialPosition(recording, hasIntro))
  const [showConsole, setShowConsole] = useState(false)
  const [split, setSplit] = useState(0.55)
  const [vsplit, setVsplit] = useState(0.58)
  const dark = usePrefersDark()

  const goTo = useCallback((i: number) => setPos(Math.min(max, Math.max(min, i))), [min, max])
  const step: Step | null = pos >= 0 ? steps[pos] : null

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return
      if (e.metaKey || e.ctrlKey || e.altKey) return
      if (e.key === 'ArrowRight' || e.key === 'ArrowDown' || e.key === ' ' || e.key === 'PageDown') {
        e.preventDefault()
        goTo(pos + 1)
      } else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp' || e.key === 'PageUp') {
        e.preventDefault()
        goTo(pos - 1)
      } else if (e.key === 'Home') {
        goTo(min)
      } else if (e.key === 'End') {
        goTo(max)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [pos, goTo, min, max])

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

  const onNodeClick = useCallback(
    (id: string) => {
      const i = steps.findIndex((s) => s.highlight.includes(id))
      if (i >= 0) goTo(i)
    },
    [steps, goTo],
  )

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

  const warnings = recording.warnings
  return (
    <div className="app" data-step={step ? step.id : 'intro'}>
      <header className="top">
        <div className="title-block">
          <h1>{recording.title}</h1>
          <div className="muted small">
            <code>{recording.entry}</code> · Python {recording.python} · {steps.length} step{steps.length === 1 ? '' : 's'}
            {warnings.length > 0 && (
              <span className="warn-badge" title={warnings.join('\n')}>
                ⚠ {warnings.length} warning{warnings.length > 1 ? 's' : ''}
              </span>
            )}
          </div>
        </div>
        <SchemaPane source={recording.schema.source} active={active} done={done} dark={dark} onNodeClick={onNodeClick} />
      </header>
      <main className="main" style={{ gridTemplateColumns: `${split * 100}% 6px minmax(0, 1fr)` }}>
        <CodePane code={step?.code ?? null} step={step} />
        <Splitter direction="horizontal" onDrag={setSplit} />
        <div className="right" style={{ gridTemplateRows: `${vsplit * 100}% 6px minmax(0, 1fr)` }}>
          <ObjectsPane objects={objects} />
          <Splitter direction="vertical" onDrag={setVsplit} />
          <TextPane
            text={step ? step.text : recording.description}
            title={step ? step.title : recording.title}
            intro={!step}
          />
        </div>
      </main>
      {showConsole && (
        <pre className="console">{step?.console || '(no program output since the previous step)'}</pre>
      )}
      <NavBar
        pos={pos}
        min={min}
        max={max}
        step={step}
        onPrev={() => goTo(pos - 1)}
        onNext={() => goTo(pos + 1)}
        consoleOpen={showConsole}
        onToggleConsole={() => setShowConsole((v) => !v)}
      />
    </div>
  )
}
