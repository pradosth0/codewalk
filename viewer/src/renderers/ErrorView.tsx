import type { ErrorDisplay } from '../types'

export function ErrorView({ d }: { d: ErrorDisplay }) {
  return (
    <div className="error-view">
      <div className="error-message">{d.message}</div>
      {d.names.length > 0 && (
        <div className="muted small">
          names available in this frame: {d.names.map((n) => <code key={n}>{n}</code>).reduce<React.ReactNode[]>((acc, el, i) => (i ? [...acc, ', ', el] : [el]), [])}
        </div>
      )}
    </div>
  )
}
