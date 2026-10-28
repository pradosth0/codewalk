/** Compact, readable rendering of a scalar cell. */
export function formatCell(v: unknown): string {
  if (v === null || v === undefined) return 'null'
  if (typeof v === 'number') return formatNumber(v)
  if (typeof v === 'boolean') return v ? 'True' : 'False'
  if (typeof v === 'string') return v
  return JSON.stringify(v)
}

export function formatNumber(v: number): string {
  if (Number.isInteger(v)) return String(v)
  const s = String(v)
  if (s.length <= 10) return s
  return Number(v.toPrecision(6)).toString()
}

export function cellClass(v: unknown): string {
  if (v === null || v === undefined) return 'cell null'
  if (typeof v === 'number') return 'cell num'
  if (typeof v === 'boolean') return 'cell bool'
  return 'cell'
}
