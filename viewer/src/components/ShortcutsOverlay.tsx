import { useEffect, useRef } from 'react'
import { XIcon } from './icons'

interface Shortcut {
  keys: string[]
  what: string
  levels?: boolean
}

interface Group {
  title: string
  items: Shortcut[]
}

const GROUPS: Group[] = [
  {
    title: 'Navigate',
    items: [
      { keys: ['←', '→'], what: 'previous / next step at this level (also Space, PageUp, PageDown)' },
      { keys: ['↑', '↓'], what: 'up to the summary / down into the details', levels: true },
      { keys: ['1', '2', '3'], what: 'walk at this level of detail', levels: true },
      { keys: ['Home', 'End'], what: 'first / last step' },
    ],
  },
  {
    title: 'Panes',
    items: [
      { keys: ['f'], what: 'maximise the pane under the pointer, or restore' },
      { keys: ['c'], what: 'program output under the code' },
      { keys: ['s'], what: 'show or hide the schema' },
      { keys: ['o'], what: 'outline of the walkthrough' },
      { keys: ['Esc'], what: 'restore a maximised pane, close the outline or a menu' },
    ],
  },
  {
    title: 'View',
    items: [
      { keys: ['t'], what: 'theme: system, light, dark' },
      { keys: ['?'], what: 'this list' },
    ],
  },
]

interface Props {
  hasLevels: boolean
  onClose: () => void
}

const FOCUSABLE = 'button, [href], input, [tabindex]:not([tabindex="-1"])'

export function ShortcutsOverlay({ hasLevels, onClose }: Props) {
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null
    ref.current?.focus()
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.stopPropagation()
        onClose()
      } else if (e.key === 'Tab' && ref.current) {
        // keep the focus inside the dialog
        const items = Array.from(ref.current.querySelectorAll<HTMLElement>(FOCUSABLE))
        if (!items.length) return
        const first = items[0]
        const last = items[items.length - 1]
        if (e.shiftKey && (document.activeElement === first || document.activeElement === ref.current)) {
          e.preventDefault()
          last.focus()
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault()
          first.focus()
        }
      }
    }
    document.addEventListener('keydown', onKey, true)
    return () => {
      document.removeEventListener('keydown', onKey, true)
      previous?.focus?.()
    }
  }, [onClose])

  return (
    <div className="overlay" onClick={onClose}>
      <div className="dialog" role="dialog" aria-modal="true" aria-label="Keyboard shortcuts" tabIndex={-1} ref={ref} onClick={(e) => e.stopPropagation()}>
        <div className="dialog-head">
          <h2>Keyboard shortcuts</h2>
          <button className="btn btn-ghost btn-icon" onClick={onClose} aria-label="Close" title="Close (Esc)">
            <XIcon />
          </button>
        </div>
        <div className="shortcut-groups">
          {GROUPS.map((g) => (
            <div className="shortcut-group" key={g.title}>
              <h3>{g.title}</h3>
              <div className="shortcuts">
                {g.items
                  .filter((s) => hasLevels || !s.levels)
                  .map((s) => (
                    <div className="shortcut" key={s.what} style={{ display: 'contents' }}>
                      <span className="keys">
                        {s.keys.map((k) => (
                          <kbd key={k}>{k}</kbd>
                        ))}
                      </span>
                      <span>{s.what}</span>
                    </div>
                  ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
