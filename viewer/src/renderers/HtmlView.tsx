import DOMPurify from 'dompurify'
import { useMemo } from 'react'
import type { HtmlDisplay } from '../types'

export function HtmlView({ d }: { d: HtmlDisplay }) {
  const clean = useMemo(() => DOMPurify.sanitize(d.html, { USE_PROFILES: { html: true, svg: true } }), [d.html])
  return <div className="html-view" dangerouslySetInnerHTML={{ __html: clean }} />
}
