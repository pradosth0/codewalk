import { useEffect, useRef, useState } from 'react'
import { writeClipboard } from '../renderers/copy'
import { CheckIcon, CopyIcon } from './icons'

interface Props {
  text: string
  title: string
}

export function CopyButton({ text, title }: Props) {
  const [done, setDone] = useState(false)
  const timer = useRef<number | undefined>(undefined)
  useEffect(() => () => window.clearTimeout(timer.current), [])
  const onClick = async () => {
    if (await writeClipboard(text)) {
      setDone(true)
      window.clearTimeout(timer.current)
      timer.current = window.setTimeout(() => setDone(false), 1500)
    }
  }
  return (
    <button className={`btn btn-ghost copy-btn ${done ? 'done' : ''}`} onClick={onClick} title={title}>
      {done ? <CheckIcon /> : <CopyIcon />}
      {done ? 'Copied' : 'Copy'}
    </button>
  )
}
