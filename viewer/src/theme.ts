import { useCallback, useEffect, useState } from 'react'
import { usePref } from './prefs'

export type ThemePref = 'system' | 'light' | 'dark'
export type Theme = 'light' | 'dark'

const query = '(prefers-color-scheme: dark)'

/** The theme preference (system / light / dark, persisted) and the resolved theme, which
 *  is written to `data-theme` on <html>. index.html sets the attribute before paint. */
export function useTheme(): { pref: ThemePref; theme: Theme; setPref: (p: ThemePref) => void; cycle: () => void } {
  const [pref, setPref] = usePref<ThemePref>('theme', 'system')
  const [systemDark, setSystemDark] = useState(() => window.matchMedia(query).matches)
  useEffect(() => {
    const mq = window.matchMedia(query)
    const onChange = (e: MediaQueryListEvent) => setSystemDark(e.matches)
    mq.addEventListener('change', onChange)
    return () => mq.removeEventListener('change', onChange)
  }, [])
  const theme: Theme = pref === 'system' ? (systemDark ? 'dark' : 'light') : pref
  useEffect(() => {
    document.documentElement.dataset.theme = theme
  }, [theme])
  const cycle = useCallback(
    () => setPref((p) => (p === 'system' ? 'light' : p === 'light' ? 'dark' : 'system')),
    [setPref],
  )
  return { pref, theme, setPref, cycle }
}
