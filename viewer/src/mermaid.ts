import mermaid from 'mermaid'

let initializedDark: boolean | null = null
let counter = 0

function init(dark: boolean): void {
  if (initializedDark === dark) return
  mermaid.initialize({
    startOnLoad: false,
    theme: dark ? 'dark' : 'neutral',
    securityLevel: 'strict',
    fontFamily: 'ui-sans-serif, system-ui, -apple-system, sans-serif',
    flowchart: { htmlLabels: true, curve: 'basis', padding: 8 },
  })
  initializedDark = dark
}

const STYLES = {
  light: {
    active: 'fill:#2563eb,stroke:#1e40af,color:#ffffff,stroke-width:2px',
    done: 'fill:#dbeafe,stroke:#93c5fd,color:#1e3a8a',
  },
  dark: {
    active: 'fill:#2563eb,stroke:#93c5fd,color:#ffffff,stroke-width:2px',
    done: 'fill:#1e3a5f,stroke:#3b82f6,color:#dbeafe',
  },
}

async function render(definition: string): Promise<string> {
  const id = `cw-schema-${++counter}`
  try {
    const { svg } = await mermaid.render(id, definition)
    return svg
  } finally {
    document.getElementById('d' + id)?.remove()
    document.getElementById(id)?.remove()
  }
}

export interface SchemaRender {
  svg: string
  error?: string
}

/** Render the schema with the current node(s) highlighted and earlier ones marked as done. */
export async function renderSchema(
  source: string,
  active: string[],
  done: string[],
  dark: boolean,
): Promise<SchemaRender> {
  init(dark)
  const styles = dark ? STYLES.dark : STYLES.light
  const lines = [source.trimEnd(), `classDef cw_active ${styles.active};`, `classDef cw_done ${styles.done};`]
  if (done.length) lines.push(`class ${done.join(',')} cw_done;`)
  if (active.length) lines.push(`class ${active.join(',')} cw_active;`)
  try {
    return { svg: await render(lines.join('\n')) }
  } catch (e) {
    try {
      return { svg: await render(source), error: `could not apply highlights: ${String(e)}` }
    } catch (e2) {
      return { svg: '', error: String(e2) }
    }
  }
}
