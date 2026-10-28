import type { ArrayDisplay } from '../types'
import { cellClass, formatCell } from './format'

export function ArrayView({ d }: { d: ArrayDisplay }) {
  const shape = d.shape.length ? `(${d.shape.join(', ')})` : '()'
  const sliceNote =
    d.preview_index && d.preview_index.length
      ? `slice [${d.preview_index.join(', ')}, :, :]`
      : d.shape.length === 1
        ? 'first values'
        : 'top-left corner'
  return (
    <div className="array-view">
      <div className="meta muted small">
        {d.library} · {d.dtype} · shape {shape} · {d.size} element{d.size === 1 ? '' : 's'}
        {d.device ? ` · ${d.device}` : ''}
      </div>
      {d.stats && (
        <div className="stats">
          {(['min', 'max', 'mean', 'std'] as const).map((k) => (
            <div key={k} className="stat">
              <span className="stat-label">{k}</span>
              <span className="stat-value">{formatCell(d.stats![k])}</span>
            </div>
          ))}
          {d.stats.nan > 0 && (
            <div className="stat">
              <span className="stat-label">nan</span>
              <span className="stat-value">{d.stats.nan}</span>
            </div>
          )}
        </div>
      )}
      <div className="meta muted small">
        preview · {sliceNote}
        {d.truncated ? ` · ${d.preview_shape[0]} × ${d.preview_shape[1]} of ${d.size}` : ''}
      </div>
      <div className="scroll">
        <table className="data-table preview">
          <tbody>
            {d.preview.map((row, i) => (
              <tr key={i}>
                {row.map((v, j) => (
                  <td key={j} className={cellClass(v)}>
                    {formatCell(v)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
