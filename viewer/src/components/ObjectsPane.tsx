import type { ComponentType, KeyboardEvent } from 'react'
import type { Display, ObjectEntry } from '../types'
import { Renderer } from '../renderers'
import { copyText } from '../renderers/copy'
import { CopyButton } from './CopyButton'
import { BracesIcon, CodeIcon, GridIcon, ImageIcon, MaximizeIcon, MinimizeIcon, TableIcon, TextIcon, WarnIcon } from './icons'

interface Props {
  stepId: string
  objects: ObjectEntry[]
  /** The tab the reader chose (kept by name across steps); null means the first one. */
  selected: string | null
  onSelect: (name: string) => void
  /** A tab to draw attention to, while the reader hovers its name in the explanation. */
  hint: string | null
  maximized: boolean
  onMaximize: () => void
}

const KIND_ICON: Record<Display['kind'], ComponentType> = {
  table: TableIcon,
  array: GridIcon,
  image: ImageIcon,
  html: CodeIcon,
  json: BracesIcon,
  text: TextIcon,
  error: WarnIcon,
}

const KIND_NAME: Record<Display['kind'], string> = {
  table: 'table',
  array: 'array',
  image: 'figure',
  html: 'HTML',
  json: 'JSON',
  text: 'text',
  error: 'error',
}

/** Which tab is open for a step: the chosen name when the step has it, else the first. */
export function currentObject(objects: ObjectEntry[], selected: string | null): ObjectEntry | null {
  if (selected) {
    const hit = objects.find((o) => o.name === selected)
    if (hit) return hit
  }
  return objects[0] ?? null
}

export function ObjectsPane({ stepId, objects, selected, onSelect, hint, maximized, onMaximize }: Props) {
  const obj = currentObject(objects, selected)
  const copy = obj ? copyText(obj.display) : null
  const panelId = `objects-${stepId.replace(/[^A-Za-z0-9_-]/g, '_')}`

  // ARIA tabs: ← → move between tabs when one has the focus (and do not change the step).
  const onTabKey = (e: KeyboardEvent<HTMLDivElement>) => {
    if (e.key !== 'ArrowLeft' && e.key !== 'ArrowRight' && e.key !== 'Home' && e.key !== 'End') return
    if (!obj || objects.length === 0) return
    const i = objects.findIndex((o) => o.name === obj.name)
    const j =
      e.key === 'Home' ? 0 : e.key === 'End' ? objects.length - 1 : (i + (e.key === 'ArrowRight' ? 1 : objects.length - 1)) % objects.length
    e.preventDefault()
    e.stopPropagation()
    onSelect(objects[j].name)
    const tabs = e.currentTarget.querySelectorAll<HTMLButtonElement>('[role="tab"]')
    tabs[j]?.focus()
  }

  return (
    <section className="pane objects" data-pane="objects">
      <div className="tabs pane-header" role="tablist" aria-label="Captured objects" onDoubleClick={onMaximize} onKeyDown={onTabKey}>
        {objects.map((o) => {
          const Icon = KIND_ICON[o.display.kind] ?? TextIcon
          const active = obj !== null && o.name === obj.name
          return (
            <button
              key={o.name}
              role="tab"
              aria-selected={active}
              aria-controls={panelId}
              tabIndex={active ? 0 : -1}
              className={`tab ${active ? 'active' : ''} ${hint === o.name ? 'hint' : ''}`}
              onClick={() => onSelect(o.name)}
              title={`${o.expr || o.name} · ${KIND_NAME[o.display.kind] ?? o.display.kind}`}
            >
              <Icon />
              {o.name}
            </button>
          )
        })}
        {objects.length === 0 && <span className="faint">No objects captured at this step</span>}
        <span className="grow" />
        <button
          className={`btn btn-ghost btn-icon pane-max ${maximized ? 'on' : ''}`}
          onClick={onMaximize}
          title={maximized ? 'Restore the layout (Esc)' : 'Maximise this pane (double-click the header)'}
          aria-label={maximized ? 'Restore the layout' : 'Maximise this pane'}
        >
          {maximized ? <MinimizeIcon /> : <MaximizeIcon />}
        </button>
      </div>
      <div className="object-body" id={panelId} role="tabpanel" aria-label={obj ? obj.name : undefined} key={`${stepId}:${obj?.name ?? ""}`}>
        {obj && (
          <>
            <div className="expr">
              <span className="grow">
                {obj.expr && <code>{obj.expr}</code>}
                {'type' in obj.display && obj.display.type ? <span> · {obj.display.type}</span> : null}
              </span>
              {copy !== null && <CopyButton text={copy} title={`Copy ${obj.name} as text`} />}
            </div>
            <Renderer display={obj.display} />
          </>
        )}
      </div>
    </section>
  )
}
