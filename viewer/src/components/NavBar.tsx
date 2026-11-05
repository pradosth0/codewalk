import type { Step } from '../types'
import type { Outline } from '../outline'
import { levelName } from '../outline'

interface Props {
  pos: number
  min: number
  max: number
  step: Step | null
  outline: Outline
  level: number
  detail: number
  visible: { index: number; count: number }
  canUp: boolean
  canDown: boolean
  onPrev: () => void
  onNext: () => void
  onUp: () => void
  onDown: () => void
  onDetail: (level: number) => void
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

export function NavBar({
  pos,
  min,
  max,
  step,
  outline,
  level,
  detail,
  visible,
  canUp,
  canDown,
  onPrev,
  onNext,
  onUp,
  onDown,
  onDetail,
  consoleOpen,
  onToggleConsole,
}: Props) {
  const total = max + 1
  const hasConsole = Boolean(step?.console)
  const hasLevels = outline.maxLevel > outline.minLevel
  const levels: number[] = []
  for (let l = outline.minLevel; l <= outline.maxLevel; l++) levels.push(l)
  return (
    <footer className="nav">
      <button className="nav-btn" onClick={onPrev} disabled={pos <= min} title="Previous step at this level (←)">
        ◀ Prev
      </button>
      {hasLevels && (
        <div className="nav-group" role="group" aria-label="Level of detail">
          <button className="nav-btn small-btn" onClick={onUp} disabled={!canUp} title="Up to the step that summarises this one (↑)">
            ▲ Up
          </button>
          <button className="nav-btn small-btn" onClick={onDown} disabled={!canDown} title="Down into the details of this step (↓)">
            ▼ Down
          </button>
        </div>
      )}
      <div className="nav-center">
        <span className="counter" title={step ? `step ${pos + 1} of ${total} overall` : undefined}>
          {step ? `${visible.index} / ${visible.count}` : `intro · ${total} steps`}
        </span>
        {hasLevels && step && (
          <span className="level-badge" title={`this step is at ${levelName(outline, level)} of ${outline.maxLevel}`}>
            {levelName(outline, level)}
          </span>
        )}
        {step && <span className="nav-title">{step.title}</span>}
        {step?.location && (
          <span className="muted small">
            {step.location.file}:{step.location.line} · {step.location.function}() · {modeWord(step.location.mode)}
            {step.location.hit > 1 ? ` · hit ${step.location.hit}` : ''} · {step.location.elapsed.toFixed(2)}s
          </span>
        )}
      </div>
      {hasLevels && (
        <div className="detail-select" title="Walk through every step up to this level of detail">
          <span className="muted small">walk at</span>
          {levels.map((l) => (
            <button
              key={l}
              className={`nav-btn small-btn ${detail === l ? 'active' : ''}`}
              onClick={() => onDetail(l)}
              title={levelName(outline, l)}
            >
              {l}
            </button>
          ))}
        </div>
      )}
      <button
        className={`nav-btn small-btn ${consoleOpen ? 'active' : ''}`}
        onClick={onToggleConsole}
        title="Program output since the previous step"
      >
        console{hasConsole ? ' •' : ''}
      </button>
      <button className="nav-btn primary" onClick={onNext} disabled={pos >= max} title="Next step at this level (→)">
        Next ▶
      </button>
    </footer>
  )
}
