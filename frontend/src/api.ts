import type { Results, Trace } from './types'

const API = (import.meta as any).env?.VITE_API_URL ?? 'http://localhost:8000'

export async function fetchResults(): Promise<Results> {
  const r = await fetch(`${API}/results`)
  if (!r.ok) throw new Error(`results: ${r.status}`)
  return r.json()
}

export async function fetchEpisode(scenario: string, agent: string): Promise<Trace> {
  const r = await fetch(`${API}/episodes/${scenario}/${agent}`)
  if (!r.ok) throw new Error(`episode: ${r.status}`)
  return r.json()
}
