import { Fragment } from 'react'
import type { ChainNode } from '../chain'
import { CheckIcon, DatabaseIcon } from './icons'

interface Props {
  nodes: ChainNode[]
  active: string[]
  done: string[]
  onNodeClick: (id: string, anchor: Element) => void
  nodeTip: (id: string) => string | null
}

/** A linear schema as a row of stages: outlined ahead, muted and ticked behind, the
 *  current one filled with the accent. */
export function Stepper({ nodes, active, done, onNodeClick, nodeTip }: Props) {
  const stateOf = (id: string) => (active.includes(id) ? 'active' : done.includes(id) ? 'done' : 'todo')
  return (
    <div className="schema stepper" data-settled="true" role="list" aria-label="Schema">
      {nodes.map((n, i) => {
        const state = stateOf(n.id)
        const prev = i > 0 ? stateOf(nodes[i - 1].id) : null
        const passed = prev !== null && prev !== 'todo' && state !== 'todo'
        return (
          <Fragment key={n.id}>
            {i > 0 && (
              <span className={`stepper-link ${passed ? 'passed' : ''}`} aria-hidden="true">
                <span className="line" />
                <span className="head" />
              </span>
            )}
            <button
              className={`stepper-node shape-${n.shape} state-${state}`}
              role="listitem"
              aria-current={state === 'active' ? 'step' : undefined}
              title={nodeTip(n.id) ?? n.label}
              onClick={(e) => onNodeClick(n.id, e.currentTarget)}
            >
              {state === 'done' && (
                <span className="badge" aria-label="visited">
                  <CheckIcon />
                </span>
              )}
              {n.shape === 'cylinder' && <DatabaseIcon />}
              <span className="label">{n.label}</span>
            </button>
          </Fragment>
        )
      })}
    </div>
  )
}
