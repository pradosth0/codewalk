import { useEffect, useRef, useState, type ReactNode } from 'react'

interface Props {
  title: string
  icon: ReactNode
  label?: string
  className?: string
  children: ReactNode
}

/** A toolbar button that opens a small panel under it; closes on Escape or a click outside. */
export function Popover({ title, icon, label, className, children }: Props) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    const onDown = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.stopPropagation()
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', onDown)
    document.addEventListener('keydown', onKey, true)
    return () => {
      document.removeEventListener('mousedown', onDown)
      document.removeEventListener('keydown', onKey, true)
    }
  }, [open])

  return (
    <div className={`popover-wrap ${className ?? ''}`} ref={ref}>
      <button
        className={`btn btn-ghost ${label ? '' : 'btn-icon'} ${open ? 'active' : ''}`}
        title={title}
        aria-label={title}
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
      >
        {icon}
        {label && <span className="btn-label">{label}</span>}
      </button>
      {open && (
        <div className="popover" role="dialog" aria-label={title}>
          {children}
        </div>
      )}
    </div>
  )
}
