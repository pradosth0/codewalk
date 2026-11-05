import { useMemo } from 'react'
import { Md, type ObjectRefs } from './Md'
import { PaneHeader } from './PaneHeader'

interface Props {
  stepId: string
  text: string
  objectNames: string[]
  onSelectObject: (name: string) => void
  onHoverObject: (name: string | null) => void
  maximized: boolean
  onMaximize: () => void
}

export function TextPane({ stepId, text, objectNames, onSelectObject, onHoverObject, maximized, onMaximize }: Props) {
  const refs = useMemo<ObjectRefs>(
    () => ({ names: new Set(objectNames), onSelect: onSelectObject, onHover: onHoverObject }),
    [objectNames, onSelectObject, onHoverObject],
  )
  return (
    <section className="pane text" data-pane="text">
      <PaneHeader maximized={maximized} onMaximize={onMaximize}>
        <span className="label grow">Explanation</span>
      </PaneHeader>
      <div className="markdown" key={stepId}>
        {text.trim() ? <Md refs={refs}>{text}</Md> : <span className="faint">The author left no explanation for this step.</span>}
      </div>
    </section>
  )
}
