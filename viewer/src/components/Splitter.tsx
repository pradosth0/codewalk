import { useState, type KeyboardEvent as ReactKeyboardEvent, type MouseEvent as ReactMouseEvent } from 'react'

interface Props {
  direction: 'horizontal' | 'vertical'
  /** The current fraction, for keyboard resizing; omit to disable the keys. */
  value?: number | null
  onDrag: (fraction: number) => void
  onReset?: () => void
}

/** A drag handle between two tracks; reports the new fraction of the parent's size.
 *  Double-click resets (back to the automatic size where there is one). */
export function Splitter({ direction, value, onDrag, onReset }: Props) {
  const [dragging, setDragging] = useState(false)
  const onMouseDown = (e: ReactMouseEvent<HTMLDivElement>) => {
    const parent = e.currentTarget.parentElement
    if (!parent) return
    const rect = parent.getBoundingClientRect()
    const move = (ev: MouseEvent) => {
      const f =
        direction === 'horizontal' ? (ev.clientX - rect.left) / rect.width : (ev.clientY - rect.top) / rect.height
      onDrag(Math.min(0.85, Math.max(0.15, f)))
    }
    const up = () => {
      document.removeEventListener('mousemove', move)
      document.removeEventListener('mouseup', up)
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
      setDragging(false)
    }
    document.addEventListener('mousemove', move)
    document.addEventListener('mouseup', up)
    document.body.style.cursor = direction === 'horizontal' ? 'col-resize' : 'row-resize'
    document.body.style.userSelect = 'none'
    setDragging(true)
    e.preventDefault()
  }
  // With the focus on the handle, the arrow keys resize in 2% steps (and do not change the step).
  const onKeyDown = (e: ReactKeyboardEvent<HTMLDivElement>) => {
    const less = direction === 'horizontal' ? 'ArrowLeft' : 'ArrowUp'
    const more = direction === 'horizontal' ? 'ArrowRight' : 'ArrowDown'
    if (e.key !== less && e.key !== more && e.key !== 'Home') return
    e.preventDefault()
    e.stopPropagation()
    if (e.key === 'Home') {
      onReset?.()
      return
    }
    const current = value ?? (direction === 'horizontal' ? 0.55 : 0.4)
    onDrag(Math.min(0.85, Math.max(0.15, current + (e.key === more ? 0.02 : -0.02))))
  }
  return (
    <div
      className={`splitter ${direction} ${dragging ? 'dragging' : ''}`}
      onMouseDown={onMouseDown}
      onDoubleClick={onReset}
      onKeyDown={onKeyDown}
      title={onReset ? 'Drag to resize · double-click to reset' : 'Drag to resize'}
      role="separator"
      aria-label={direction === 'horizontal' ? 'Resize the code and the objects' : 'Resize the explanation and the objects'}
      aria-orientation={direction === 'horizontal' ? 'vertical' : 'horizontal'}
      aria-valuenow={value != null ? Math.round(value * 100) : undefined}
      tabIndex={0}
    />
  )
}
