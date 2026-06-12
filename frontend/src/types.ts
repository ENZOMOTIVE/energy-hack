// Mirrors the trace JSON schema from DEVPLAN section 4.5. Do not drift.

export interface ActionEntry {
  k: number
  type: 'trade' | 'dispatch_crew'
  park: string
  delta_mw: number
  hours: number
  start_step: number | null
  reason: string
  false_dispatch: boolean
}

export interface StepRecord {
  k: number
  time: string
  forecast_mw: Record<string, number>
  twin_mw: Record<string, number>
  actual_mw: Record<string, number>
  schedule_mw: Record<string, number>
  da_price: number
  cum_cost_eur: number
  cum_cost_floor_eur: number
  action: ActionEntry | null
}

export interface Trace {
  scenario: string
  agent: string
  seed: number
  parks: string[]
  steps: StepRecord[]
  actions: ActionEntry[]
  totals: {
    cost_eur: number
    floor_eur: number
    oracle_eur: number
    score: number
    false_dispatches: number
    steps_to_first_action: number
    first_action_step: number
    brain?: string
  }
}

export interface ResultRow {
  scenario: string
  agent: string
  score: number
  cost_eur: number
  floor_eur: number
  oracle_eur: number
  false_dispatches: number
  steps_to_first_action: number
  brain?: string
  day?: string
  mc?: { mean: number; p10: number; n: number }
}

export interface Results {
  seed: number
  results: ResultRow[]
}
