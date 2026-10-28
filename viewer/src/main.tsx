import React from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import { loadRecording } from './data'
import './styles.css'

const root = createRoot(document.getElementById('root')!)

loadRecording()
  .then((recording) => {
    document.title = recording.title
    root.render(
      <React.StrictMode>
        <App recording={recording} />
      </React.StrictMode>,
    )
  })
  .catch((e: unknown) => {
    root.render(<pre className="fatal">Could not load the recording: {String(e)}</pre>)
  })
