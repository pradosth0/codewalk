import type { ReactNode } from 'react'
import { MaximizeIcon, MinimizeIcon } from './icons'

interface Props {
  children: ReactNode
  className?: string
  maximized?: boolean
  onMaximize?: () => void
}

/** The strip above a pane; double-click (or the corner button) maximises the pane. */
export function PaneHeader({ children, className, maximized, onMaximize }: Props) {
  return (
    <div className={`pane-header ${className ?? ''}`} onDoubleClick={onMaximize}>
      {children}
      {onMaximize && (
        <button
          className={`btn btn-ghost btn-icon pane-max ${maximized ? 'on' : ''}`}
          onClick={onMaximize}
          title={maximized ? 'Restore the layout (Esc)' : 'Maximise this pane (double-click the header)'}
          aria-label={maximized ? 'Restore the layout' : 'Maximise this pane'}
        >
          {maximized ? <MinimizeIcon /> : <MaximizeIcon />}
        </button>
      )}
    </div>
  )
}
