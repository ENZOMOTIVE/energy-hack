import type { Results, Trace } from './types'

// Same-origin (relative) in the production build served by FastAPI; explicit
// localhost:8000 in dev so the Vite server on :5173 reaches the API on :8000.
const env = (import.meta as any).env
const API = env?.VITE_API_URL ?? (env?.PROD ? '' : 'http://localhost:8000')

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

// ---- intelligent test-case generator ----

export interface AgentKpis {
  mean: number
  pass_rate: number
  p10: number
}
export interface BatteryCase {
  name: string
  label: string
  category: string
  stake: number
  floor: number
  oracle: number
  fitness: number
  agents: Record<string, AgentKpis>
}
export interface AgentReport extends AgentKpis {
  hardest: { name: string; label: string; mean: number }
}
export interface WorkerInfo {
  id: string
  label: string
  kind: string
}
export interface Battery {
  mode: string
  seed: number
  mc_n: number
  k: number
  contestants: string[]
  workers: WorkerInfo[]
  cases: BatteryCase[]
  report: Record<string, AgentReport>
  persona_single_run?: boolean
}

export function reportCsvUrl(mode: string): string {
  return `${API}/report/battery/${mode}.csv`
}
export function reportPdfUrl(mode: string): string {
  return `${API}/report/battery/${mode}.pdf`
}

export async function fetchBatteryModes(): Promise<string[]> {
  const r = await fetch(`${API}/batteries`)
  if (!r.ok) throw new Error(`batteries: ${r.status}`)
  return (await r.json()).modes
}

export async function fetchBattery(mode: string): Promise<Battery> {
  const r = await fetch(`${API}/battery/${mode}`)
  if (!r.ok) throw new Error(`battery: ${r.status}`)
  return r.json()
}
