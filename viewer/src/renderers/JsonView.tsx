import { useState } from 'react'
import type { JsonDisplay } from '../types'

function isContainer(v: unknown): v is Record<string, unknown> | unknown[] {
  return v !== null && typeof v === 'object'
}

function Node({ k, v, depth }: { k?: string; v: unknown; depth: number }) {
  const [open, setOpen] = useState(depth < 2)
  if (isContainer(v)) {
    const entries: [string, unknown][] = Array.isArray(v)
      ? v.map((x, i) => [String(i), x] as [string, unknown])
      : Object.entries(v)
    const summary = Array.isArray(v) ? `[${entries.length}]` : `{${entries.length}}`
    return (
      <div className="json-node">
        <span className="json-row" onClick={() => setOpen(!open)}>
          <span className="toggle">{open ? '▾' : '▸'}</span>
          {k !== undefined && <span className="key">{k}: </span>}
          <span className="muted">{summary}</span>
        </span>
        {open && (
          <div className="children">
            {entries.map(([ck, cv]) => (
              <Node key={ck} k={ck} v={cv} depth={depth + 1} />
            ))}
          </div>
        )}
      </div>
    )
  }
  return (
    <div className="json-leaf">
      {k !== undefined && <span className="key">{k}: </span>}
      <span className={`val ${v === null ? 'null' : typeof v}`}>{JSON.stringify(v)}</span>
    </div>
  )
}

export function JsonView({ d }: { d: JsonDisplay }) {
  return (
    <div className="json-view">
      <Node v={d.value} depth={0} />
    </div>
  )
}
