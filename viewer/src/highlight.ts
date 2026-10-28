import { createHighlighterCore, type HighlighterCore } from 'shiki/core'
import { createJavaScriptRegexEngine } from 'shiki/engine/javascript'

export interface Token {
  content: string
  style: Record<string, string>
}

let highlighter: Promise<HighlighterCore> | null = null

function getHighlighter(): Promise<HighlighterCore> {
  if (!highlighter) {
    highlighter = createHighlighterCore({
      themes: [import('@shikijs/themes/github-light'), import('@shikijs/themes/github-dark')],
      langs: [import('@shikijs/langs/python')],
      engine: createJavaScriptRegexEngine({ forgiving: true }),
    })
  }
  return highlighter
}

function normalizeStyle(style: unknown): Record<string, string> {
  if (!style) return {}
  if (typeof style === 'string') {
    const out: Record<string, string> = {}
    for (const part of style.split(';')) {
      const i = part.indexOf(':')
      if (i > 0) out[part.slice(0, i).trim()] = part.slice(i + 1).trim()
    }
    return out
  }
  return style as Record<string, string>
}

/** Tokenize Python source into lines of styled tokens (light and dark colours as CSS variables). */
export async function tokenize(source: string): Promise<Token[][]> {
  const hl = await getHighlighter()
  const { tokens } = hl.codeToTokens(source, {
    lang: 'python',
    themes: { light: 'github-light', dark: 'github-dark' },
    defaultColor: false,
  })
  return tokens.map((line) => line.map((t) => ({ content: t.content, style: normalizeStyle(t.htmlStyle) })))
}
