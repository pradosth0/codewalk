import type { Step } from '../types'
import { ChevronDown, ChevronUp, TerminalIcon } from './icons'

interface Crumb {
  index: number
  title: string
}

interface Props {
  step: Step
  levelLabel: string | null
  visible: { index: number; count: number }
  crumbs: Crumb[]
  details: number
  canUp: boolean
  onUp: () => void
  onDown: () => void
  onGo: (index: number) => void
  consoleLines: number
  consoleOpen: boolean
  onToggleConsole: () => void
}

/** Where the reader is: level and position, the summaries above, the title; and the
 *  moves that belong to this step (up, down, program output). */
export function StepHeader({
  step,
  levelLabel,
  visible,
  crumbs,
  details,
  canUp,
  onUp,
  onDown,
  onGo,
  consoleLines,
  consoleOpen,
  onToggleConsole,
}: Props) {
  return (
    <div className="step-header">
      <div className="step-meta">
        <div className="step-line">
          {levelLabel && (
            <>
              <span className="step-level">{levelLabel}</span>
              <span className="faint">·</span>
            </>
          )}
          <span className="step-pos">
            step {visible.index} of {visible.count}
          </span>
          {crumbs.length > 0 && (
            <>
              <span className="faint">·</span>
              <span className="step-crumbs" title="The steps that summarise this one">
                in{' '}
                {crumbs.map((c, i) => (
                  <span key={c.index}>
                    {i > 0 && <span className="faint"> › </span>}
                    <button className="link" onClick={() => onGo(c.index)}>
                      {c.title}
                    </button>
                  </span>
                ))}
              </span>
            </>
          )}
        </div>
        <h2 className="step-title" title={step.title} key={step.id}>
          {step.title}
        </h2>
      </div>
      <div className="step-actions">
        {step.kind === 'crash' && <span className="chip error">the program crashed here</span>}
        {consoleLines > 0 && (
          <button
            className={`chip ${consoleOpen ? 'accent' : ''}`}
            onClick={onToggleConsole}
            title="Program output since the previous step (c)"
            aria-pressed={consoleOpen}
          >
            <TerminalIcon />
            output · {consoleLines} line{consoleLines > 1 ? 's' : ''}
          </button>
        )}
        {canUp && (
          <button className="btn" onClick={onUp} title="Up to the step that summarises this one (↑)">
            <ChevronUp />
            Up
          </button>
        )}
        {details > 0 && (
          <button className="btn" onClick={onDown} title="Down into the details of this step (↓)">
            <ChevronDown />
            {details} detail{details > 1 ? 's' : ''}
          </button>
        )}
      </div>
    </div>
  )
}
