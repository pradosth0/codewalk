import type { TextDisplay } from '../types'

export function TextView({ d }: { d: TextDisplay }) {
  return (
    <div className="text-view-wrap">
      {d.note && <div className="note">{d.note}</div>}
      <pre className={`text-view ${d.over_limit ? 'over-limit' : ''}`}>{d.text}</pre>
      {d.truncated && !d.over_limit && <div className="muted small">truncated</div>}
    </div>
  )
}
