import mermaid from 'mermaid'

/* Mermaid is themed from the design tokens (tokens.css) and rendered once per recording
   and theme; node states (current, visited) are applied to the SVG afterwards, see
   SchemaPane. The hex values mirror tokens.css because Mermaid cannot read CSS variables. */
const THEME = {
  light: { node: '#ffffff', cluster: '#f7f8fa', fg: '#1b1f24', border: '#c8cdd4', line: '#687078' },
  dark: { node: '#1b1f28', cluster: '#151821', fg: '#e6e8eb', border: '#3a4150', line: '#7d8794' },
}

const FONT = 'ui-sans-serif, system-ui, -apple-system, sans-serif'

let initializedDark: boolean | null = null
let counter = 0

function init(dark: boolean): void {
  if (initializedDark === dark) return
  const t = dark ? THEME.dark : THEME.light
  mermaid.initialize({
    startOnLoad: false,
    theme: 'base',
    securityLevel: 'strict',
    fontFamily: FONT,
    themeVariables: {
      fontFamily: FONT,
      fontSize: '14px',
      background: 'transparent',
      primaryColor: t.node,
      primaryTextColor: t.fg,
      primaryBorderColor: t.border,
      secondaryColor: t.cluster,
      secondaryTextColor: t.fg,
      secondaryBorderColor: t.border,
      tertiaryColor: t.cluster,
      tertiaryTextColor: t.fg,
      tertiaryBorderColor: t.border,
      lineColor: t.line,
      textColor: t.fg,
      nodeTextColor: t.fg,
      titleColor: t.fg,
      clusterBkg: t.cluster,
      clusterBorder: t.border,
      edgeLabelBackground: t.cluster,
    },
    flowchart: { htmlLabels: true, curve: 'basis', padding: 8, nodeSpacing: 36, rankSpacing: 40 },
  })
  initializedDark = dark
}

export interface SchemaRender {
  svg: string
  error?: string
}

/** Render the schema as it was written; states are applied to the DOM afterwards. */
export async function renderSchema(source: string, dark: boolean): Promise<SchemaRender> {
  init(dark)
  const id = `cw-schema-${++counter}`
  try {
    const { svg } = await mermaid.render(id, source)
    return { svg }
  } catch (e) {
    return { svg: '', error: String(e) }
  } finally {
    document.getElementById('d' + id)?.remove()
    document.getElementById(id)?.remove()
  }
}
