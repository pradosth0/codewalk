import { TerminalIcon, XIcon } from './icons'

interface Props {
  text: string
  onClose: () => void
}

/** Program output captured since the previous step, docked under the code. */
export function ConsoleDrawer({ text, onClose }: Props) {
  return (
    <div className="console-drawer">
      <div className="pane-header">
        <span className="label grow">
          <TerminalIcon />
          Program output since the previous step
        </span>
        <button className="btn btn-ghost btn-icon" onClick={onClose} title="Hide the output (c)" aria-label="Hide the output">
          <XIcon />
        </button>
      </div>
      <pre className="console">{text || '(no program output since the previous step)'}</pre>
    </div>
  )
}
