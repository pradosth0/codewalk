import type { Step } from './types'

/**
 * Levels of detail (mirrors codewalk/outline.py). Every step has a level; the recorder fills
 * `parent` (the step that summarises it). The viewer walks the sequence at the current
 * step's level: Next/Prev skip deeper steps, Down enters the first detail of the current
 * step, Up jumps to its summary.
 */
export interface Outline {
  levels: number[]
  parent: (number | null)[]
  children: number[][]
  minLevel: number
  maxLevel: number
  names: string[]
}

export function buildOutline(steps: Step[], names: string[] = []): Outline {
  const levels = steps.map((s) => Math.max(1, Math.floor(s.level ?? 1)))
  const byId = new Map(steps.map((s, i) => [s.id, i] as const))
  const parent = steps.map((s) => {
    const p = s.parent != null ? byId.get(s.parent) : undefined
    return p === undefined ? null : p
  })
  const children: number[][] = steps.map(() => [])
  parent.forEach((p, i) => {
    if (p !== null) children[p].push(i)
  })
  const minLevel = levels.length ? Math.min(...levels) : 1
  const maxLevel = levels.length ? Math.max(...levels) : 1
  return { levels, parent, children, minLevel, maxLevel, names }
}

/** The level the reader is walking at: the detail setting, or deeper when the current step is deeper. */
export function effectiveLevel(o: Outline, pos: number, detail: number): number {
  const own = pos >= 0 && pos < o.levels.length ? o.levels[pos] : o.minLevel
  return Math.max(detail, own)
}

/** Next step at or above `level` after `pos` (-1 = intro); -1 when there is none. */
export function nextAt(o: Outline, pos: number, level: number): number {
  for (let j = pos + 1; j < o.levels.length; j++) if (o.levels[j] <= level) return j
  return -1
}

/** Previous step at or above `level` before `pos`; -1 when there is none (the intro, if any). */
export function prevAt(o: Outline, pos: number, level: number): number {
  for (let j = pos - 1; j >= 0; j--) if (o.levels[j] <= level) return j
  return -1
}

/** First detail of the step at `pos`; -1 when it has none. */
export function firstChild(o: Outline, pos: number): number {
  if (pos < 0 || pos >= o.children.length) return -1
  const kids = o.children[pos]
  return kids.length ? kids[0] : -1
}

/** The step summarising `pos`; -1 when it is a root. */
export function parentOf(o: Outline, pos: number): number {
  if (pos < 0 || pos >= o.parent.length) return -1
  return o.parent[pos] ?? -1
}

/** Titles of the summaries above `pos`, outermost first. */
export function breadcrumb(o: Outline, steps: Step[], pos: number): string[] {
  const out: string[] = []
  let p = parentOf(o, pos)
  let guard = 0
  while (p >= 0 && guard++ < 32) {
    out.unshift(steps[p].title)
    p = parentOf(o, p)
  }
  return out
}

/** Position of `pos` among the steps visible at `level`, and how many there are. */
export function positionAt(o: Outline, pos: number, level: number): { index: number; count: number } {
  let count = 0
  let index = 0
  o.levels.forEach((l, i) => {
    if (l <= level) {
      count++
      if (i <= pos) index = count
    }
  })
  return { index, count }
}

export function levelName(o: Outline, level: number): string {
  const name = o.names[level - 1]
  return name ? name : `level ${level}`
}
