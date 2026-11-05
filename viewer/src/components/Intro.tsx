import type { Recording } from '../types'
import type { Outline } from '../outline'
import { keySteps, levelName } from '../outline'
import { Md } from './Md'
import { ChevronRight } from './icons'

interface Props {
  recording: Recording
  outline: Outline
  labels: Map<string, string>
  onStart: () => void
  onGo: (index: number) => void
}

function when(iso: string): string {
  const d = new Date(iso)
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleDateString()
}

/** The landing view before step 1: what the program does, what the walk will show. */
export function Intro({ recording, outline, labels, onStart, onGo }: Props) {
  const steps = recording.steps
  const hasLevels = outline.maxLevel > outline.minLevel
  const levels = outline.maxLevel - outline.minLevel + 1
  const keys = keySteps(outline)
  return (
    <div className="intro">
      <div className="intro-card">
        <div className="intro-eyebrow">
          Walkthrough · {steps.length} step{steps.length === 1 ? '' : 's'}
          {hasLevels ? ` in ${levels} levels of detail` : ''}
        </div>
        <h2>{recording.title}</h2>
        <div className="markdown">
          <Md>{recording.description}</Md>
        </div>
        {keys.length > 0 && (
          <>
            <h3 className="intro-h3">
              {hasLevels ? `${levelName(outline, outline.minLevel)}: ${keys.length} key steps` : `${keys.length} steps`}
            </h3>
            <ol className="intro-steps">
              {keys.map((k, i) => {
                const s = steps[k]
                const n = outline.children[k].length
                const stage = s.highlight[0]
                return (
                  <li key={s.id}>
                    <button className="intro-step" onClick={() => onGo(k)}>
                      <span className="n">{i + 1}</span>
                      <span className="t">{s.title}</span>
                      {stage && <span className="stage">{labels.get(stage) ?? stage}</span>}
                      <span className="details">{n > 0 ? `${n} detail${n > 1 ? 's' : ''}` : ''}</span>
                    </button>
                  </li>
                )
              })}
            </ol>
          </>
        )}
        <div className="intro-actions">
          <button className="btn btn-primary btn-lg" onClick={onStart}>
            Start the walkthrough
            <ChevronRight />
          </button>
          <span className="intro-keys">
            <kbd>←</kbd>
            <kbd>→</kbd> steps
            {hasLevels && (
              <>
                {' '}
                · <kbd>↑</kbd>
                <kbd>↓</kbd> levels
              </>
            )}{' '}
            · <kbd>o</kbd> outline · <kbd>?</kbd> all shortcuts
          </span>
        </div>
        <div className="intro-meta">
          <code>{recording.entry}</code> · Python {recording.python} · recorded {when(recording.recorded_at)} in{' '}
          {recording.duration.toFixed(1)} s
        </div>
      </div>
    </div>
  )
}
