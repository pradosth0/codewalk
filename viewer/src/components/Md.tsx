import { useMemo } from 'react'
import Markdown, { type Components } from 'react-markdown'
import remarkGfm from 'remark-gfm'

/** Links inline code to the objects pane: `name` becomes a chip that opens that tab. */
export interface ObjectRefs {
  names: Set<string>
  onSelect: (name: string) => void
  onHover: (name: string | null) => void
}

/** Markdown with GFM; links open in a new tab. */
export function Md({ children, refs }: { children: string; refs?: ObjectRefs }) {
  const components = useMemo<Components>(
    () => ({
      a: ({ node: _node, ...props }) => <a {...props} target="_blank" rel="noreferrer" />,
      code: ({ node: _node, className, children, ...props }) => {
        const text = typeof children === 'string' ? children : ''
        if (refs && !className && text && !text.includes('\n') && refs.names.has(text)) {
          return (
            <button
              type="button"
              className="obj-ref"
              title={`Open the ${text} tab`}
              onClick={() => refs.onSelect(text)}
              onMouseEnter={() => refs.onHover(text)}
              onMouseLeave={() => refs.onHover(null)}
              onFocus={() => refs.onHover(text)}
              onBlur={() => refs.onHover(null)}
            >
              <code>{text}</code>
            </button>
          )
        }
        return (
          <code className={className} {...props}>
            {children}
          </code>
        )
      },
    }),
    [refs],
  )
  return (
    <Markdown remarkPlugins={[remarkGfm]} components={components}>
      {children}
    </Markdown>
  )
}
