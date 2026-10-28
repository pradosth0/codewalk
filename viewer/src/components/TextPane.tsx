import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

interface Props {
  text: string
  title: string
  intro: boolean
}

export function TextPane({ text, title, intro }: Props) {
  return (
    <section className="pane text">
      <div className="pane-header">
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
