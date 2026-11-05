import type { Display } from '../types'
import { formatCell } from './format'

/** The plain-text form of a display for the clipboard; null when there is none worth copying. */
export function copyText(d: Display): string | null {
  switch (d.kind) {
    case 'json':
      return JSON.stringify(d.value, null, 2)
    case 'text':
      return d.text
    case 'table': {
      const head = [d.index_name ?? '', ...d.columns]
      const rows = d.rows.map((r, i) => [formatCell(d.index[i]), ...r.map(formatCell)])
      return [head, ...rows].map((r) => r.join('\t')).join('\n')
    }
    case 'array':
      return d.preview.map((r) => r.map(formatCell).join('\t')).join('\n')
    default:
      return null
  }
}

export async function writeClipboard(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text)
    return true
  } catch {
    try {
      const ta = document.createElement('textarea')
      ta.value = text
      ta.setAttribute('readonly', '')
      ta.style.position = 'fixed'
      ta.style.opacity = '0'
      document.body.appendChild(ta)
      ta.select()
      const ok = document.execCommand('copy')
      ta.remove()
      return ok
    } catch {
      return false
    }
  }
}
