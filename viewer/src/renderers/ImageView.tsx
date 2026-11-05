import { useEffect, useState } from 'react'
import type { ImageDisplay } from '../types'

export function ImageView({ d }: { d: ImageDisplay }) {
  const src = `data:${d.mime};base64,${d.data}`
  const [open, setOpen] = useState(false)

  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.stopPropagation()
        setOpen(false)
      }
    }
    document.addEventListener('keydown', onKey, true)
    return () => document.removeEventListener('keydown', onKey, true)
  }, [open])

  return (
    <div className="image-view">
      <button className="image-card" onClick={() => setOpen(true)} title="Click to enlarge">
        <img src={src} alt={d.type} />
      </button>
      {d.width && d.height ? (
        <div className="meta">
          {d.width} × {d.height} px
        </div>
      ) : null}
      {open && (
        <div className="lightbox" onClick={() => setOpen(false)} role="dialog" aria-label="Enlarged figure">
          <img src={src} alt={d.type} />
        </div>
      )}
    </div>
  )
}
