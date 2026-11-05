import { useEffect, useRef } from 'react'
import type { Step } from '../types'
import type { Outline as OutlineModel } from '../outline'
import { levelName } from '../outline'
import { CheckIcon, XIcon } from './icons'

interface Props {
  steps: Step[]
  outline: OutlineModel
  pos: number
  /** The level Next and Prev walk at. */
  level: number
  labels: Map<string, string>
  onGo: (index: number) => void
  onDetail: (level: number) => void
  onClose: () => void
}

/** The walkthrough as a tree: key steps at the root, their details nested. */
export function Outline({ steps, outline, pos, level, labels, onGo, onDetail, onClose }: Props) {
  const hasLevels = outline.maxLevel > outline.minLevel
  const levels: number[] = []
  for (let l = outline.minLevel; l <= outline.maxLevel; l++) levels.push(l)
  const roots = steps.map((_, i) => i).filter((i) => outline.parent[i] === null)
  const ref = useRef<HTMLElement>(null)
  useEffect(() => {
    ref.current?.querySelector<HTMLElement>('.outline-row.current, .outline-row')?.focus()
  }, [])

  const row = (i: number) => {
    const s = steps[i]
    const cls = ['outline-row', i === pos ? 'current' : i < pos ? 'visited' : '', outline.levels[i] > level ? 'skipped' : '']
      .filter(Boolean)
      .join(' ')
    const stage = s.highlight[0]
    return (
      <li key={s.id}>
        <button className={cls} onClick={() => onGo(i)} aria-current={i === pos ? 'step' : undefined} title={s.title}>
          <span className="mark">{i < pos ? <CheckIcon /> : null}</span>
          <span className="label">{s.title}</span>
          {stage && <span className="stage">{labels.get(stage) ?? stage}</span>}
        </button>
        {outline.children[i].length > 0 && <ul>{outline.children[i].map(row)}</ul>}
      </li>
    )
  }

  return (
    <aside className="outline" aria-label="Outline" ref={ref}>
      <div className="outline-head">
        <h2>Outline</h2>
        <button className="btn btn-ghost btn-icon" onClick={onClose} title="Close the outline (o)" aria-label="Close the outline">
          <XIcon />
        </button>
      </div>
      {hasLevels && (
        <div className="outline-levels">
          <div className="seg" role="group" aria-label="Level of detail">
            {levels.map((l) => (
              <button key={l} className={level === l ? 'active' : ''} onClick={() => onDetail(l)} aria-pressed={level === l}>
                {levelName(outline, l)}
              </button>
            ))}
          </div>
          <p className="outline-help">Next and Prev visit every step up to this level; greyed steps are skipped.</p>
        </div>
      )}
      <nav className="outline-tree">
        <ul>{roots.map(row)}</ul>
      </nav>
    </aside>
  )
}
