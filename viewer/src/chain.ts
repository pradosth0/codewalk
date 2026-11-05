/** A linear `flowchart LR` (what `schema=[...]` produces, and many hand-written schemas)
 *  is drawn as an HTML stepper instead of a Mermaid SVG. Anything richer stays Mermaid. */

export type Shape = 'rect' | 'round' | 'stadium' | 'cylinder' | 'circle' | 'diamond' | 'subroutine' | 'hexagon' | 'other'

export interface ChainNode {
  id: string
  label: string
  shape: Shape
}

const OPENERS: [string, string, Shape][] = [
  ['([', '])', 'stadium'],
  ['[(', ')]', 'cylinder'],
  ['((', '))', 'circle'],
  ['[[', ']]', 'subroutine'],
  ['{{', '}}', 'hexagon'],
  ['[', ']', 'rect'],
  ['(', ')', 'round'],
  ['{', '}', 'diamond'],
  ['>', ']', 'other'],
]

const ID = /^[A-Za-z0-9_][A-Za-z0-9_-]*/

/** One node reference: `id` or `id[label]`; returns the node and the rest of the text. */
function readNode(text: string): { node: { id: string; label: string | null; shape: Shape }; rest: string } | null {
  const m = ID.exec(text)
  if (!m) return null
  const id = m[0]
  let rest = text.slice(id.length)
  for (const [open, close, shape] of OPENERS) {
    if (rest.startsWith(open)) {
      const end = rest.indexOf(close, open.length)
      if (end < 0) return null
      let label = rest.slice(open.length, end).trim()
      if (label.startsWith('"') && label.endsWith('"') && label.length >= 2) label = label.slice(1, -1)
      rest = rest.slice(end + close.length)
      return { node: { id, label: label.replace(/`/g, ''), shape }, rest }
    }
  }
  return { node: { id, label: null, shape: 'rect' }, rest }
}

export function parseChain(source: string): ChainNode[] | null {
  const lines = source
    .split(/\n|;/)
    .map((l) => l.trim())
    .filter((l) => l && !l.startsWith('%%'))
  if (!lines.length || !/^(flowchart|graph)\s+LR$/i.test(lines[0])) return null
  const nodes = new Map<string, ChainNode>()
  const edges: [string, string][] = []
  const declare = (id: string, label: string | null, shape: Shape) => {
    const known = nodes.get(id)
    if (!known) nodes.set(id, { id, label: label ?? id, shape })
    else if (label !== null) {
      known.label = label
      known.shape = shape
    }
  }
  for (const line of lines.slice(1)) {
    let rest = line
    let prev: string | null = null
    while (rest.length) {
      const r = readNode(rest)
      if (!r) return null
      declare(r.node.id, r.node.label, r.node.shape)
      if (prev !== null) edges.push([prev, r.node.id])
      prev = r.node.id
      rest = r.rest.trim()
      if (!rest) break
      if (!rest.startsWith('-->')) return null // labelled, dotted or thick edges, `&`, `:::`, styles...
      rest = rest.slice(3).trim()
      if (!rest) return null
    }
  }
  if (nodes.size === 0) return null
  const next = new Map<string, string>()
  const indeg = new Map<string, number>()
  for (const [a, b] of edges) {
    if (next.has(a) && next.get(a) !== b) return null
    next.set(a, b)
    indeg.set(b, (indeg.get(b) ?? 0) + 1)
    if ((indeg.get(b) ?? 0) > 1) return null
  }
  const starts = [...nodes.keys()].filter((id) => !indeg.has(id))
  if (starts.length !== 1) return null
  const order: ChainNode[] = []
  let cur: string | undefined = starts[0]
  const seen = new Set<string>()
  while (cur !== undefined && !seen.has(cur)) {
    seen.add(cur)
    order.push(nodes.get(cur)!)
    cur = next.get(cur)
  }
  return order.length === nodes.size ? order : null
}
