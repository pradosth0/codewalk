import { useState } from 'react'
import type { ObjectEntry } from '../types'
import { Renderer } from '../renderers'

interface Props {
  objects: ObjectEntry[]
}

export function ObjectsPane({ objects }: Props) {
  const [selected, setSelected] = useState<string | null>(null)
  const names = objects.map((o) => o.name)
  const current = selected && names.includes(selected) ? selected : (names[0] ?? null)
  const obj = objects.find((o) => o.name === current) ?? null

  return (
    <section className="pane objects">
      <div className="tabs">
        {objects.map((o) => (
          <button
            key={o.name}
            className={`tab ${o.name === current ? 'active' : ''}`}
            onClick={() => setSelected(o.name)}
            title={o.expr}
          >
            {o.name}
            <span className={`kind kind-${o.display.kind}`}>{o.display.kind}</span>
          </button>
        ))}
        {objects.length === 0 && <span className="muted small pad">no objects at this step</span>}
      </div>
      <div className="object-body">
        {obj && (
          <>
            {(obj.expr || ('type' in obj.display && obj.display.type)) && (
              <div className="expr muted small">
                {obj.expr && <code>{obj.expr}</code>}
                {'type' in obj.display && obj.display.type ? <span> · {obj.display.type}</span> : null}
              </div>
            )}
            <Renderer display={obj.display} />
          </>
        )}
      </div>
    </section>
  )
}
