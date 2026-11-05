/** Node labels from a Mermaid flowchart: `load[Load]`, `raw[(data/raw.csv)]`, `a("x")`...
 *  Falls back to the id. Good enough for tooltips, the outline and the intro. */
const NODE =
  /(?:^|[\s;])([A-Za-z0-9_][A-Za-z0-9_-]*)\s*(\[\(|\(\(|\[\[|\(\[|\{\{|\[|\(|\{|>)\s*"?([^"\]\)\}]+?)"?\s*(\)\]|\)\)|\]\]|\]\)|\}\}|\]|\)|\})/g

export function schemaLabels(source: string, nodes: string[]): Map<string, string> {
  const labels = new Map<string, string>()
  for (const m of source.matchAll(NODE)) {
    const [, id, , label] = m
    if (!labels.has(id)) labels.set(id, label.replace(/`/g, '').trim())
  }
  for (const id of nodes) if (!labels.has(id)) labels.set(id, id)
  return labels
}
