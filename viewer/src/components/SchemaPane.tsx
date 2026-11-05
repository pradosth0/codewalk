import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import { renderSchema, type SchemaRender } from '../mermaid'

export type NodeState = 'active' | 'done' | 'todo'

interface Props {
  source: string
  active: string[]
  done: string[]
  dark: boolean
  onNodeClick: (id: string, anchor: Element) => void
  nodeTip: (id: string) => string | null
}

// Mermaid 11 ids look like "<renderId>-flowchart-<nodeId>-<n>"; older versions omit the render id.
const NODE_ID = /(?:^|-)(?:flowchart|graph)-(.+)-\d+$/
const SVG_NS = 'http://www.w3.org/2000/svg'
const SHAPES = ':scope > rect, :scope > path, :scope > polygon, :scope > circle, :scope > ellipse'

const STYLE: Record<NodeState, { fill: string; stroke: string; width: string; text: string }> = {
  active: { fill: 'var(--accent-fill)', stroke: 'var(--accent-fill)', width: '2', text: 'var(--accent-fg)' },
  done: { fill: 'var(--bg-2)', stroke: 'var(--border-strong)', width: '1.5', text: 'var(--fg-muted)' },
  todo: { fill: 'var(--bg-0)', stroke: 'var(--border-strong)', width: '1.5', text: 'var(--fg)' },
}

function badge(x: number, y: number): SVGGElement {
  // Inline styles: Mermaid's embedded `#id .node circle` rules would win over a stylesheet.
  const g = document.createElementNS(SVG_NS, 'g')
  g.setAttribute('class', 'cw-badge')
  g.setAttribute('transform', `translate(${x}, ${y})`)
  const c = document.createElementNS(SVG_NS, 'circle')
  c.setAttribute('r', '7.5')
  c.style.fill = 'var(--fg-faint)'
  c.style.stroke = 'var(--bg-1)'
  c.style.strokeWidth = '2'
  const p = document.createElementNS(SVG_NS, 'path')
  p.setAttribute('d', 'M-3.2 0.2 L-1 2.4 L3.2 -2.2')
  p.style.fill = 'none'
  p.style.stroke = '#ffffff'
  p.style.strokeWidth = '2'
  p.style.strokeLinecap = 'round'
  p.style.strokeLinejoin = 'round'
  g.append(c, p)
  return g
}

/** Node states as inline styles (CSS variables resolve there, so the theme can change)
 *  plus a visited badge; rects get rounded corners. */
function applyStates(root: HTMLElement, active: string[], done: string[]): void {
  root.querySelectorAll<SVGGElement>('g.node[id]').forEach((g) => {
    const m = NODE_ID.exec(g.id)
    if (!m) return
    const id = m[1]
    const state: NodeState = active.includes(id) ? 'active' : done.includes(id) ? 'done' : 'todo'
    g.dataset.state = state
    if (state === 'active') g.setAttribute('aria-current', 'step')
    else g.removeAttribute('aria-current')
    const s = STYLE[state]
    let box: DOMRect | null = null
    g.querySelectorAll<SVGGraphicsElement>(SHAPES).forEach((shape) => {
      if (shape instanceof SVGRectElement) {
        shape.setAttribute('rx', '8')
        shape.setAttribute('ry', '8')
      }
      shape.style.fill = s.fill
      shape.style.stroke = s.stroke
      shape.style.strokeWidth = s.width
      try {
        const b = shape.getBBox()
        box = box ? (b.x + b.width > box.x + box.width ? b : box) : b
      } catch {
        /* detached or unsupported shape */
      }
    })
    g.querySelectorAll<HTMLElement>('.nodeLabel, text').forEach((label) => {
      label.style.color = s.text
      label.style.fill = s.text
    })
    g.querySelector('.cw-badge')?.remove()
    if (state === 'done' && box) {
      const b: DOMRect = box
      g.append(badge(b.x + b.width - 1, b.y + 1))
    }
  })
}

/** Size the SVG at its natural scale (so the 14px labels stay 14px), capped by the strip's
 *  width and height. */
function fit(svg: SVGSVGElement, container: HTMLElement): void {
  const vb = svg.viewBox.baseVal
  if (!vb || !vb.width || !vb.height) return
  const style = getComputedStyle(container)
  const maxW = container.clientWidth - parseFloat(style.paddingLeft) - parseFloat(style.paddingRight)
  const maxH = parseFloat(getComputedStyle(svg).getPropertyValue('--schema-max-h')) || 120
  const scale = Math.min(1, maxW / vb.width, maxH / vb.height)
  svg.style.width = `${Math.floor(vb.width * scale)}px`
  svg.style.height = 'auto'
  svg.style.maxWidth = '100%'
  svg.style.overflow = 'visible' // the visited badges sit on node corners, outside the viewBox
}

export function SchemaPane({ source, active, done, dark, onNodeClick, nodeTip }: Props) {
  const ref = useRef<HTMLDivElement>(null)
  const [state, setState] = useState<SchemaRender & { key?: string }>({ svg: '' })
  const [applied, setApplied] = useState('')
  const renderKey = [source, dark ? 'dark' : 'light'].join('\u0000')
  const stepKey = [renderKey, active.join(','), done.join(',')].join('\u0000')
  // `settled` tells automation (codewalk screenshot) that the SVG shows the current step.
  const settled = state.key === renderKey && applied === stepKey

  useEffect(() => {
    let alive = true
    renderSchema(source, dark).then((r) => {
      if (alive) setState({ ...r, key: renderKey })
    })
    return () => {
      alive = false
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [renderKey])

  useLayoutEffect(() => {
    const root = ref.current
    if (!root || state.key !== renderKey) return
    applyStates(root, active, done)
    const svg = root.querySelector('svg')
    if (svg) fit(svg, root)
    setApplied(stepKey)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state.svg, state.key, stepKey])

  useEffect(() => {
    const root = ref.current
    if (!root || typeof ResizeObserver === 'undefined') return
    const ro = new ResizeObserver(() => {
      const svg = root.querySelector('svg')
      if (svg) fit(svg, root)
    })
    ro.observe(root)
    return () => ro.disconnect()
  }, [])

  useEffect(() => {
    const root = ref.current
    if (!root) return
    const handlers: [Element, string, EventListener][] = []
    root.querySelectorAll<SVGGElement>('g.node[id]').forEach((g) => {
      const m = NODE_ID.exec(g.id)
      if (!m) return
      const id = m[1]
      const click = () => onNodeClick(id, g)
      const key = (e: Event) => {
        const k = (e as KeyboardEvent).key
        if (k === 'Enter' || k === ' ') {
          e.preventDefault()
          e.stopPropagation()
          onNodeClick(id, g)
        }
      }
      g.addEventListener('click', click)
      g.addEventListener('keydown', key)
      handlers.push([g, 'click', click], [g, 'keydown', key])
      // Stages are buttons for the keyboard and screen readers.
      g.setAttribute('tabindex', '0')
      g.setAttribute('role', 'button')
      g.querySelector(':scope > title')?.remove()
      const tip = nodeTip(id)
      if (tip) {
        g.setAttribute('aria-label', tip)
        const title = document.createElementNS(SVG_NS, 'title')
        title.textContent = tip
        g.prepend(title)
      }
    })
    return () => handlers.forEach(([g, type, h]) => g.removeEventListener(type, h))
  }, [state.svg, onNodeClick, nodeTip])

  return (
    <div className="schema" ref={ref} data-settled={settled}>
      {state.error && <div className="schema-error">{state.error}</div>}
      <div className="schema-svg" dangerouslySetInnerHTML={{ __html: state.svg }} />
    </div>
  )
}
