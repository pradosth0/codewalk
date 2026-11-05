import type { Recording } from './types'

/** The recording is embedded by codewalk/build.py; in `vite dev` it comes from fixtures/steps.json. */
export async function loadRecording(): Promise<Recording> {
  const el = document.getElementById('codewalk-data')
  const raw = el?.textContent?.trim() ?? ''
  if (raw && !raw.startsWith('__CODEWALK')) {
    return JSON.parse(raw) as Recording
  }
  // `?fixture=name` picks another file from fixtures/ (dev only).
  const name = new URLSearchParams(window.location.search).get('fixture') || 'steps'
  const res = await fetch(`/fixtures/${name}.json`)
  if (!res.ok) {
    throw new Error(`no embedded recording, and fixtures/${name}.json returned ${res.status}`)
  }
  return (await res.json()) as Recording
}
