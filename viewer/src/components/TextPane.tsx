import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

interface Props {
  text: string
  title: string
  intro: boolean
  crumbs?: string[]
}

export function TextPane({ text, title, intro, crumbs = [] }: Props) {
  return (
    <section className="pane text">
      <div className="pane-header">
        {crumbs.length > 0 && (
          <span className="crumbs muted small" title="The steps that summarise this one">
            {crumbs.map((c, i) => (
              <span key={i}>
                {c} <span className="crumb-sep">›</span>{' '}
              </span>
            ))}
          </span>
        )}
        <span className="file">{intro ? 'Introduction' : title}</span>
      </div>
      <div className="markdown">
        {text.trim() ? (
          <Markdown
            remarkPlugins={[remarkGfm]}
            components={{
              a: ({ node: _node, ...props }) => <a {...props} target="_blank" rel="noreferrer" />,
            }}
          >
            {text}
          </Markdown>
        ) : (
          <span className="muted">no explanation for this step</span>
        )}
      </div>
    </section>
  )
}
