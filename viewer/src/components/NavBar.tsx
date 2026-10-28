import type { Step } from '../types'

interface Props {
  pos: number
  min: number
  max: number
  step: Step | null
  onPrev: () => void
  onNext: () => void
  consoleOpen: boolean
  onToggleConsole: () => void
}

function modeWord(mode: string): string {
  switch (mode) {
    case 'before':
      return 'before the line runs'
    case 'after':
      return 'after the line ran'
    case 'return':
      return 'on return'
    case 'crash':
      return 'crashed here'
    default:
      return mode
  }
}

export function NavBar({ pos, min, max, step, onPrev, onNext, consoleOpen, onToggleConsole }: Props) {
  const total = max + 1
  const hasConsole = Boolean(step?.console)
  return (
    <footer className="nav">
      <button className="nav-btn" onClick={onPrev} disabled={pos <= min} title="Previous step (←)">
        ◀ Prev
      </button>
      <div className="nav-center">
        <span className="counter">{step ? `${pos + 1} / ${total}` : `intro · ${total} steps`}</span>
        {step && <span className="nav-title">{step.title}</span>}
        {step?.location && (
          <span className="muted small">
            {step.location.file}:{step.location.line} · {step.location.function}() · {modeWord(step.location.mode)}
            {step.location.hit > 1 ? ` · hit ${step.location.hit}` : ''} · {step.location.elapsed.toFixed(2)}s
          </span>
        )}
      </div>
      <button
        className={`nav-btn small-btn ${consoleOpen ? 'active' : ''}`}
        onClick={onToggleConsole}
        title="Program output since the previous step"
      >
        console{hasConsole ? ' •' : ''}
      </button>
      <button className="nav-btn primary" onClick={onNext} disabled={pos >= max} title="Next step (→)">
        Next ▶
      </button>
    </footer>
  )
}
