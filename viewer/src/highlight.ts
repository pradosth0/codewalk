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

// Every code window is tokenised once; the cache lets the code pane render coloured
// code synchronously for any window seen before (or pre-tokenised at load).
const cache = new Map<string, Token[][]>()
const pending = new Map<string, Promise<Token[][]>>()

/** Tokens for `source` if they are already computed. */
export function cachedTokens(source: string): Token[][] | null {
  return cache.get(source) ?? null
}

/** Tokenize Python source into lines of styled tokens (light and dark colours as CSS variables). */
export function tokenize(source: string): Promise<Token[][]> {
  const hit = cache.get(source)
  if (hit) return Promise.resolve(hit)
  let p = pending.get(source)
  if (!p) {
    p = getHighlighter().then((hl) => {
      const { tokens } = hl.codeToTokens(source, {
        lang: 'python',
        themes: { light: 'github-light', dark: 'github-dark' },
        defaultColor: false,
      })
      const lines = tokens.map((line) => line.map((t) => ({ content: t.content, style: normalizeStyle(t.htmlStyle) })))
      cache.set(source, lines)
      pending.delete(source)
      return lines
    })
    pending.set(source, p)
  }
  return p
}

/** Tokenise every window of a recording in the background, one after the other. */
export async function pretokenize(sources: Iterable<string>): Promise<void> {
  for (const s of new Set(sources)) {
    try {
      await tokenize(s)
    } catch {
      /* a window that fails to tokenise is shown as plain text */
    }
  }
}
