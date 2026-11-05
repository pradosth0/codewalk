import type { Recording } from '../types'
import type { ThemePref } from '../theme'
import { Popover } from './Popover'
import { InfoIcon, KeyboardIcon, ListIcon, MonitorIcon, MoonIcon, SunIcon, WarnIcon } from './icons'

interface Props {
  recording: Recording
  levels: number
  outlineOpen: boolean
  onToggleOutline: () => void
  themePref: ThemePref
  onCycleTheme: () => void
  progress: number
  hasLevels: boolean
  onHelp: () => void
}

function when(iso: string): string {
  const d = new Date(iso)
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString()
}

const THEME_ICON = { system: MonitorIcon, light: SunIcon, dark: MoonIcon }

export function TopBar({ recording, levels, outlineOpen, onToggleOutline, themePref, onCycleTheme, progress, hasLevels, onHelp }: Props) {
  const n = recording.warnings.length
  const ThemeIcon = THEME_ICON[themePref]
  const nextTheme = themePref === 'system' ? 'light' : themePref === 'light' ? 'dark' : 'system'
  return (
    <header className="topbar">
      <button
        className={`btn btn-ghost ${outlineOpen ? 'active' : ''}`}
        onClick={onToggleOutline}
        title="Outline of the walkthrough (o)"
        aria-pressed={outlineOpen}
      >
        <ListIcon />
        <span className="btn-label">Outline</span>
      </button>
      <h1 title={recording.title}>{recording.title}</h1>
      {n > 0 && (
        <Popover title={`${n} recording warning${n > 1 ? 's' : ''}`} icon={<WarnIcon />} label={`${n} warning${n > 1 ? 's' : ''}`} className="warn">
          <h3>Recording warnings</h3>
          <ul>
            {recording.warnings.map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
        </Popover>
      )}
      <Popover title="About this recording" icon={<InfoIcon />}>
        <h3>Recording</h3>
        <dl>
          <dt>Entry</dt>
          <dd>{recording.entry}</dd>
          <dt>Python</dt>
          <dd>{recording.python}</dd>
          <dt>Backend</dt>
          <dd>{recording.backend}</dd>
          <dt>Recorded</dt>
          <dd>{when(recording.recorded_at)}</dd>
          <dt>Run time</dt>
          <dd>{recording.duration.toFixed(2)} s</dd>
          <dt>Steps</dt>
          <dd>
            {recording.steps.length}
            {hasLevels ? ` in ${levels} levels of detail` : ''}
          </dd>
        </dl>
      </Popover>
      <button className="btn btn-ghost btn-icon" onClick={onHelp} title="Keyboard shortcuts (?)" aria-label="Keyboard shortcuts">
        <KeyboardIcon />
      </button>
      <button
        className="btn btn-ghost btn-icon"
        onClick={onCycleTheme}
        title={`Theme: ${themePref} · click for ${nextTheme} (t)`}
        aria-label={`Theme: ${themePref}. Switch to ${nextTheme}`}
      >
        <ThemeIcon />
      </button>
      <div className="progress" aria-hidden="true">
        <div className="progress-fill" style={{ width: `${Math.round(progress * 1000) / 10}%` }} />
      </div>
    </header>
  )
}
