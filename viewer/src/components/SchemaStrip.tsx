import { useCallback, useEffect, useMemo, useRef, useState, type KeyboardEvent as ReactKeyboardEvent } from 'react'
import { parseChain } from '../chain'
import { SchemaPane } from './SchemaPane'
import { Stepper } from './Stepper'
import { ChevronDown, ChevronUp } from './icons'

export interface NodeStep {
  index: number
  title: string
  level: number
  levelName: string | null
}

interface Props {
  source: string
  nodes: string[]
  labels: Map<string, string>
  active: string[]
  done: string[]
  dark: boolean
  collapsed: boolean
  onToggle: () => void
  /** The steps that highlight a node, in recording order. */
  stepsOf: (id: string) => NodeStep[]
  pos: number
  onGo: (index: number) => void
}

interface Menu {
  id: string
  left: number
  top: number
}

/** The schema band under the top bar: an HTML stepper for linear chains, Mermaid for the
 *  rest. Collapsed, it becomes one line of stage names (`s`). Clicking a stage opens its
 *  step, or a menu of its steps when there are several. */
export function SchemaStrip({ source, nodes, labels, active, done, dark, collapsed, onToggle, stepsOf, pos, onGo }: Props) {
  const ref = useRef<HTMLDivElement>(null)
  const chain = useMemo(() => parseChain(source), [source])
  const [menu, setMenu] = useState<Menu | null>(null)

  const nodeTip = useCallback(
    (id: string): string | null => {
      const label = labels.get(id) ?? id
      const steps = stepsOf(id)
      if (steps.length === 0) return `${label}: no step pauses here`
      if (steps.length === 1) return `${label}: ${steps[0].title}`
      return `${label}: ${steps.length} steps, click to choose`
    },
    [labels, stepsOf],
  )

  const onNodeClick = useCallback(
    (id: string, anchor: Element) => {
      const steps = stepsOf(id)
      if (steps.length === 0) return
      if (steps.length === 1) {
        onGo(steps[0].index)
        return
      }
      const strip = ref.current
      if (!strip) return
      const a = anchor.getBoundingClientRect()
      const s = strip.getBoundingClientRect()
      setMenu({ id, left: a.left - s.left + a.width / 2, top: a.bottom - s.top + 6 })
    },
    [stepsOf, onGo],
  )

  useEffect(() => {
    if (!menu) return
    const onDown = (e: MouseEvent) => {
      const el = ref.current?.querySelector('.node-menu')
      if (el && !el.contains(e.target as Node)) setMenu(null)
    }
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.stopPropagation()
        setMenu(null)
      }
    }
    document.addEventListener('mousedown', onDown)
    document.addEventListener('keydown', onKey, true)
    return () => {
      document.removeEventListener('mousedown', onDown)
      document.removeEventListener('keydown', onKey, true)
    }
  }, [menu])

  useEffect(() => setMenu(null), [pos, collapsed])

  // The menu takes the focus on its current item; ↑ ↓ move, Enter chooses.
  useEffect(() => {
    if (!menu) return
    const el = ref.current?.querySelector<HTMLElement>('.node-menu-item.current, .node-menu-item')
    el?.focus()
  }, [menu])
  const onMenuKey = (e: ReactKeyboardEvent<HTMLDivElement>) => {
    if (e.key !== 'ArrowDown' && e.key !== 'ArrowUp') return
    e.preventDefault()
    e.stopPropagation()
    const items = Array.from(e.currentTarget.querySelectorAll<HTMLElement>('.node-menu-item'))
    const i = items.indexOf(document.activeElement as HTMLElement)
    const j = (i + (e.key === 'ArrowDown' ? 1 : items.length - 1)) % items.length
    items[j]?.focus()
  }

  const menuSteps = menu ? stepsOf(menu.id) : []
  const minLevel = menuSteps.length ? Math.min(...menuSteps.map((s) => s.level)) : 1

  return (
    <section className={`schema-strip ${collapsed ? 'collapsed' : ''}`} ref={ref} aria-label="Schema">
      {chain ? (
        <Stepper nodes={chain} active={active} done={done} onNodeClick={onNodeClick} nodeTip={nodeTip} />
      ) : (
        <SchemaPane source={source} active={active} done={done} dark={dark} onNodeClick={onNodeClick} nodeTip={nodeTip} />
      )}
      {collapsed && (
        <div className="schema-mini" aria-label="Schema">
          {nodes.map((id, i) => (
            <span key={id}>
              {i > 0 && <span className="sep">›</span>}
              <button
                className={active.includes(id) ? 'active' : done.includes(id) ? 'done' : ''}
                onClick={(e) => onNodeClick(id, e.currentTarget)}
                title={nodeTip(id) ?? undefined}
                aria-current={active.includes(id) ? 'step' : undefined}
              >
                {labels.get(id) ?? id}
              </button>
            </span>
          ))}
        </div>
      )}
      <button
        className="btn btn-ghost btn-icon schema-toggle"
        onClick={onToggle}
        title={collapsed ? 'Show the schema (s)' : 'Hide the schema (s)'}
        aria-label={collapsed ? 'Show the schema' : 'Hide the schema'}
        aria-expanded={!collapsed}
      >
        {collapsed ? <ChevronDown /> : <ChevronUp />}
      </button>
      {menu && menuSteps.length > 1 && (
        <div className="node-menu popover" role="menu" aria-label={`Steps in ${labels.get(menu.id) ?? menu.id}`} style={{ left: menu.left, top: menu.top }} onKeyDown={onMenuKey}>
          <h3>{labels.get(menu.id) ?? menu.id}</h3>
          {menuSteps.map((s) => (
            <button
              key={s.index}
              role="menuitem"
              className={`node-menu-item ${s.index === pos ? 'current' : ''}`}
              style={{ paddingLeft: 10 + (s.level - minLevel) * 14 }}
              onClick={() => {
                onGo(s.index)
                setMenu(null)
              }}
            >
              <span className="dot" />
              <span className="label">{s.title}</span>
              {s.levelName && <span className="lvl">{s.levelName}</span>}
            </button>
          ))}
        </div>
      )}
    </section>
  )
}
