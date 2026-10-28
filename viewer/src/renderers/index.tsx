import type { Display } from '../types'
import { TableView } from './TableView'
import { ArrayView } from './ArrayView'
import { ImageView } from './ImageView'
import { HtmlView } from './HtmlView'
import { JsonView } from './JsonView'
import { TextView } from './TextView'
import { ErrorView } from './ErrorView'

export function Renderer({ display }: { display: Display }) {
  switch (display.kind) {
    case 'table':
      return <TableView d={display} />
    case 'array':
      return <ArrayView d={display} />
    case 'image':
      return <ImageView d={display} />
    case 'html':
      return <HtmlView d={display} />
    case 'json':
      return <JsonView d={display} />
    case 'text':
      return <TextView d={display} />
    case 'error':
      return <ErrorView d={display} />
    default:
      return <pre className="text-view">{JSON.stringify(display, null, 2)}</pre>
  }
}
