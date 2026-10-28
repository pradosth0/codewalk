import { useEffect, useRef, useState } from 'react'
import type { Code, Step } from '../types'
import { tokenize, type Token } from '../highlight'

interface Props {
  code: Code | null
  step: Step | null
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

export function CodePane({ code, step }: Props) {
  const [lines, setLines] = useState<{ source: string; tokens: Token[][] } | null>(null)
  const currentRef = useRef<HTMLTableRowElement>(null)
  const source = code?.source ?? ''
  const settled = !code || (lines !== null && lines.source === source)

  useEffect(() => {
    if (!code) return
    let alive = true
    tokenize(source).then((tokens) => {
      if (alive) setLines({ source, tokens })
    })
    return () => {
      alive = false
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [source])

  useEffect(() => {
    currentRef.current?.scrollIntoView({ block: 'center' })
  }, [code?.file, code?.current, lines])

  if (!code) {
    return (
      <section className="pane code" data-settled={settled}>
        <div className="pane-header">
          <span className="muted">no code for this step</span>
        </div>
        <div className="empty-hint">{step ? '' : 'Press Next (→) to start the walkthrough.'}</div>
      </section>
    )
  }

  const sourceLines = source.split('\n')
  const tokens = lines && lines.source === source ? lines.tokens : null
  const hasFocus = code.focus.length > 0
  const inFocus = (n: number) => code.focus.some(([a, b]) => n >= a && n <= b)
  const mode = step?.location?.mode

  return (
    <section className="pane code" data-settled={settled}>
      <div className="pane-header">
        <span className="file">{code.file}</span>
        <span className="muted">
          lines {code.start}–{code.end}
        </span>
        {step?.location && <span className="muted">{step.location.function}()</span>}
      </div>
      <div className="code-scroll">
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
    </section>
  )
}
