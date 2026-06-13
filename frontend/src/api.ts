import type { Results, Trace } from './types'

const API = (import.meta as any).env?.VITE_API_URL ?? 'http://localhost:8000'

export type DataSource = 'synthetic' | 'real'

export async function fetchResults(data: DataSource = 'synthetic'): Promise<Results> {
  const r = await fetch(`${API}/results?data=${data}`)
  if (!r.ok) throw new Error(`results: ${r.status}`)
  return r.json()
}

export async function fetchEpisode(
  scenario: string,
  agent: string,
  data: DataSource = 'synthetic',
): Promise<Trace> {
  const r = await fetch(`${API}/episodes/${scenario}/${agent}?data=${data}`)
  if (!r.ok) throw new Error(`episode: ${r.status}`)
  return r.json()
}


export interface ChaosFault {
  park: string
  step: number
  magnitude?: number
}
export interface ChaosClouds {
  park: string
  start_step: number
  end_step: number
  depth?: number
}
export interface HumanAction {
  k: number
  type: 'trade' | 'dispatch_crew'
  park: string
  delta_mw?: number
  hours?: number
}

export interface SimRequest {
  scenario: string
  agent: string
  seed?: number
  data?: DataSource
  faults?: ChaosFault[]
  clouds?: ChaosClouds[]
  human_actions?: HumanAction[]
}

export async function simulate(req: SimRequest): Promise<Trace> {
  const r = await fetch(`${API}/simulate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  })
  if (!r.ok) throw new Error(`simulate: ${r.status}`)
  return r.json()
}
