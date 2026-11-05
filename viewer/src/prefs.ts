import { useCallback, useState } from 'react'

/** Viewer preferences in localStorage, keyed `codewalk.<name>`; every access is guarded
 *  because file:// pages and private windows may refuse storage. */
const PREFIX = 'codewalk.'

export function readPref<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(PREFIX + key)
    return raw === null ? fallback : (JSON.parse(raw) as T)
  } catch {
    return fallback
  }
}

export function writePref(key: string, value: unknown): void {
  try {
    localStorage.setItem(PREFIX + key, JSON.stringify(value))
  } catch {
    /* storage unavailable: the preference lives for this page only */
  }
}

type Updater<T> = T | ((prev: T) => T)

export function usePref<T>(key: string, fallback: T): [T, (v: Updater<T>) => void] {
  const [value, setValue] = useState<T>(() => readPref(key, fallback))
  const set = useCallback(
    (v: Updater<T>) =>
      setValue((prev) => {
        const next = typeof v === 'function' ? (v as (p: T) => T)(prev) : v
        writePref(key, next)
        return next
      }),
    [key],
  )
  return [value, set]
}
