import React from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import { loadRecording } from './data'
import { pretokenize } from './highlight'
import './styles/index.css'

const root = createRoot(document.getElementById('root')!)

loadRecording()
  .then((recording) => {
    document.title = recording.title
    root.render(
      <React.StrictMode>
        <App recording={recording} />
      </React.StrictMode>,
    )
    // Colour every code window once, in the background, so no step ever shows plain text.
    void pretokenize(recording.steps.flatMap((s) => (s.code ? [s.code.source] : [])))
  })
  .catch((e: unknown) => {
    root.render(<pre className="fatal">Could not load the recording: {String(e)}</pre>)
  })
