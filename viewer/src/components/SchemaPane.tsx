import { useEffect, useRef, useState } from 'react'
import { renderSchema, type SchemaRender } from '../mermaid'

interface Props {
  source: string
  active: string[]
  done: string[]
  dark: boolean
  onNodeClick: (id: string) => void
}

// Mermaid 11 ids look like "<renderId>-flowchart-<nodeId>-<n>"; older versions omit the render id.
const NODE_ID = /(?:^|-)(?:flowchart|graph)-(.+)-\d+$/

export function SchemaPane({ source, active, done, dark, onNodeClick }: Props) {
  const ref = useRef<HTMLDivElement>(null)
  const [state, setState] = useState<SchemaRender & { key?: string }>({ svg: '' })
  const activeKey = active.join(',')
  const doneKey = done.join(',')
  // `settled` tells automation (codewalk screenshot) that the SVG matches the current inputs.
  const key = [source, activeKey, doneKey, dark ? 'dark' : 'light'].join('\u0000')
  const settled = state.key === key

  useEffect(() => {
    let alive = true
    renderSchema(source, active, done, dark).then((r) => {
      if (alive) setState({ ...r, key })
    })
    return () => {
      alive = false
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [source, activeKey, doneKey, dark])

  useEffect(() => {
    const root = ref.current
    if (!root) return
    const handlers: [Element, () => void][] = []
    root.querySelectorAll<SVGGElement>('g.node[id]').forEach((g) => {
      const m = NODE_ID.exec(g.id)
      if (!m) return
      const id = m[1]
      g.style.cursor = 'pointer'
      const handler = () => onNodeClick(id)
      g.addEventListener('click', handler)
      handlers.push([g, handler])
    })
    return () => handlers.forEach(([g, h]) => g.removeEventListener('click', h))
  }, [state.svg, onNodeClick])

  return (
    <div className="schema" ref={ref} data-settled={settled}>
      {state.error && <div className="schema-error">{state.error}</div>}
      <div className="schema-svg" dangerouslySetInnerHTML={{ __html: state.svg }} />
    </div>
  )
}
