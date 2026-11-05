import { ChevronLeft, ChevronRight } from './icons'

interface Props {
  canPrev: boolean
  canNext: boolean
  onPrev: () => void
  onNext: () => void
  /** Indices of the key steps, their titles, the current segment and whether the reader is on its key step. */
  keys: number[]
  titles: string[]
  segment: number
  atKey: boolean
  onJump: (index: number) => void
}

export function Footer({ canPrev, canNext, onPrev, onNext, keys, titles, segment, atKey, onJump }: Props) {
  const showRail = keys.length > 1 && keys.length <= 40
  return (
    <footer className="footer">
      <button className="btn" onClick={onPrev} disabled={!canPrev} title="Previous step at this level (←)">
        <ChevronLeft />
        Prev
      </button>
      <div className="rail" aria-label="Key steps">
        {showRail &&
          keys.map((k, i) => {
            const cls = i < segment ? 'done' : i === segment ? (atKey ? 'current' : 'partial') : ''
            return (
              <button
                key={k}
                className={`rail-dot ${cls}`}
                onClick={() => onJump(k)}
                title={`${i + 1}. ${titles[k]}`}
                aria-label={`Go to ${titles[k]}`}
                aria-current={i === segment && atKey ? 'step' : undefined}
              />
            )
          })}
      </div>
      <button className="btn btn-primary" onClick={onNext} disabled={!canNext} title="Next step at this level (→)">
        Next
        <ChevronRight />
      </button>
    </footer>
  )
}
