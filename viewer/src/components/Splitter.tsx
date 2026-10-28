import type { MouseEvent as ReactMouseEvent } from 'react'

interface Props {
  direction: 'horizontal' | 'vertical'
  onDrag: (fraction: number) => void
}

/** A drag handle between two grid tracks; reports the new fraction of the parent's size. */
export function Splitter({ direction, onDrag }: Props) {
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
    }
    document.addEventListener('mousemove', move)
    document.addEventListener('mouseup', up)
    document.body.style.cursor = direction === 'horizontal' ? 'col-resize' : 'row-resize'
    document.body.style.userSelect = 'none'
    e.preventDefault()
  }
  return <div className={`splitter ${direction}`} onMouseDown={onMouseDown} />
}
