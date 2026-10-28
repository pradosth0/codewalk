import type { TableDisplay } from '../types'
import { cellClass, formatCell } from './format'

export function TableView({ d }: { d: TableDisplay }) {
  const shown = d.truncated ? ` · showing ${d.rows.length} × ${d.columns.length}` : ''
  return (
    <div className="table-view">
      <div className="meta muted small">
        {d.shape[0]} rows × {d.shape[1]} columns{shown}
      </div>
      <div className="scroll">
        <table className="data-table">
          <thead>
            <tr>
              <th className="idx">{d.index_name ?? ''}</th>
              {d.columns.map((c, i) => (
                <th key={i}>
                  {c}
                  <span className="dtype">{d.dtypes[c] ?? ''}</span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {d.rows.map((row, i) => (
              <tr key={i}>
                <th className="idx">{formatCell(d.index[i])}</th>
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
