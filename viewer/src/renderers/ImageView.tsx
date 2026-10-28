import type { ImageDisplay } from '../types'

export function ImageView({ d }: { d: ImageDisplay }) {
  const src = `data:${d.mime};base64,${d.data}`
  return (
    <div className="image-view">
      <img src={src} alt={d.type} />
      {d.width && d.height ? (
        <div className="meta muted small">
          {d.width} × {d.height} px
        </div>
      ) : null}
    </div>
  )
}
