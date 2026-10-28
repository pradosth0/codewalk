// Mirrors the steps.json payload written by codewalk/recorder.py (spec section 6).

export interface TableDisplay {
  kind: 'table'
  columns: string[]
  index: (string | number | boolean | null)[]
  index_name: string | null
  rows: unknown[][]
  shape: [number, number]
  dtypes: Record<string, string>
  truncated: boolean
  type: string
}

export interface ArrayStats {
  min: number | string | null
  max: number | string | null
  mean: number | string | null
  std: number | string | null
  nan: number
}

export interface ArrayDisplay {
  kind: 'array'
  library: string
  dtype: string
  shape: number[]
  size: number
  stats: ArrayStats | null
  preview: unknown[][]
  preview_shape: [number, number]
  preview_index: number[] | null
  truncated: boolean
  type: string
  device?: string
}

export interface ImageDisplay {
  kind: 'image'
  mime: string
  data: string
  width: number | null
  height: number | null
  type: string
}

export interface HtmlDisplay {
  kind: 'html'
  html: string
  type: string
}

export interface JsonDisplay {
  kind: 'json'
  value: unknown
  type: string
}

export interface TextDisplay {
  kind: 'text'
  text: string
  truncated: boolean
  type: string
  note?: string
  over_limit?: boolean
}

export interface ErrorDisplay {
  kind: 'error'
  message: string
  names: string[]
}

export type Display =
  | TableDisplay
  | ArrayDisplay
  | ImageDisplay
  | HtmlDisplay
  | JsonDisplay
  | TextDisplay
  | ErrorDisplay

export interface ObjectEntry {
  name: string
  expr: string
  display: Display
}

export interface Location {
  file: string
  line: number
  paused_line: number
  function: string
  mode: 'before' | 'after' | 'return' | 'crash' | string
  hit: number
  elapsed: number
}

export interface Code {
  file: string
  start: number
  end: number
  current: number | null
  focus: [number, number][]
  source: string
}

export interface Step {
  id: string
  spec_id: string | null
  index: number
  label: string
  kind: 'step' | 'crash'
  title: string
  location: Location | null
  highlight: string[]
  code: Code | null
  objects: ObjectEntry[]
  text: string
  console: string
  traceback?: string
}

export interface Recording {
  version: number
  title: string
  description: string
  entry: string
  recorded_at: string
  python: string
  backend: string
  duration: number
  schema: { kind: string; source: string; nodes: string[] }
  warnings: string[]
  steps: Step[]
}
