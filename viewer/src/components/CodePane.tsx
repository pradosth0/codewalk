import { useEffect, useRef, useState, type ReactNode } from 'react'
import type { Code, Step } from '../types'
import { cachedTokens, tokenize, type Token } from '../highlight'
import { PaneHeader } from './PaneHeader'

interface Props {
  code: Code | null
  step: Step | null
  maximized: boolean
  onMaximize: () => void
  children?: ReactNode
}

function marker(mode: string | undefined): string {
  switch (mode) {
    case 'after':
      return '✓'
    case 'return':
      return '↩'
    case 'crash':
      return '✗'
    default:
      return '▶'
  }
}

/** Where the program is paused, in words: shown as a chip in the header. */
function pausedText(step: Step): string {
  const loc = step.location
  if (!loc) return ''
  const hit = loc.hit > 1 ? ` · hit ${loc.hit}` : ''
  switch (loc.mode) {
    case 'before':
      return `paused before line ${loc.line}${hit}`
    case 'after':
      return `after line ${loc.line} ran${hit}`
    case 'return':
      return `returning from ${loc.function}()${hit}`
    case 'crash':
      return `crashed at line ${loc.line}`
    default:
      return `${loc.mode} line ${loc.line}${hit}`
  }
}

export function CodePane({ code, step, maximized, onMaximize, children }: Props) {
  const [lines, setLines] = useState<{ source: string; tokens: Token[][] } | null>(null)
  const currentRef = useRef<HTMLTableRowElement>(null)
  const scrollRef = useRef<HTMLDivElement>(null)
  const source = code?.source ?? ''
  // Windows tokenised earlier (or pre-tokenised at load) render coloured on the first paint.
  const tokens = cachedTokens(source) ?? (lines && lines.source === source ? lines.tokens : null)
  const settled = !code || tokens !== null

  useEffect(() => {
    if (!code || cachedTokens(source)) return
    let alive = true
    tokenize(source).then((t) => {
      if (alive) setLines({ source, tokens: t })
    })
    return () => {
      alive = false
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [source])

  useEffect(() => {
    // Scroll the code box only: scrollIntoView would also scroll the stacked layout on
    // narrow screens and hide the explanation above the code.
    const row = currentRef.current
    const box = scrollRef.current
    if (!row || !box) return
    const table = row.offsetParent as HTMLElement | null
    const top = row.offsetTop + (table?.offsetTop ?? 0) - box.clientHeight / 2 + row.offsetHeight / 2
    box.scrollTop = Math.max(0, top)
  }, [code?.file, code?.current, tokens])

  if (!code) {
    return (
      <section className="pane code" data-pane="code" data-settled={settled}>
        <PaneHeader maximized={maximized} onMaximize={onMaximize}>
          <span className="label grow">Code</span>
        </PaneHeader>
        <div className="empty-hint">{step ? 'No code window for this step.' : ''}</div>
        {children}
      </section>
    )
  }

  const sourceLines = source.split('\n')
  const hasFocus = code.focus.length > 0
  const inFocus = (n: number) => code.focus.some(([a, b]) => n >= a && n <= b)
  const mode = step?.location?.mode
  const paused = step ? pausedText(step) : ''

  return (
    <section className="pane code" data-pane="code" data-settled={settled}>
      <PaneHeader maximized={maximized} onMaximize={onMaximize}>
        <span className="file">{code.file}</span>
        {step?.location && <span>{step.location.function}()</span>}
        <span className="faint grow">
          lines {code.start}–{code.end}
        </span>
        {paused && (
          <span className={`chip ${mode === 'crash' ? 'error' : ''}`} title={step?.location ? `${step.location.elapsed.toFixed(2)} s into the run` : undefined}>
            {paused}
          </span>
        )}
      </PaneHeader>
      <div className="code-scroll enter" ref={scrollRef} key={`${code.file}:${code.start}`}>
        <table className="code-table">
          <tbody>
            {sourceLines.map((text, i) => {
              const n = code.start + i
              const isCurrent = n === code.current
              const cls = ['line', isCurrent ? 'current' : '', hasFocus ? (inFocus(n) ? 'focus' : 'dim') : '']
                .filter(Boolean)
                .join(' ')
              return (
                <tr key={n} className={cls} ref={isCurrent ? currentRef : undefined}>
                  <td className="ln">{n}</td>
                  <td className="marker">{isCurrent ? marker(mode) : ''}</td>
                  <td className="src">
                    {tokens
                      ? tokens[i]?.map((t, j) => (
                          <span key={j} className="tok" style={t.style}>
                            {t.content}
                          </span>
                        ))
                      : text}
                    {(!tokens || !tokens[i]?.length) && text === '' ? ' ' : null}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
      {children}
    </section>
  )
}
