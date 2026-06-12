import { useEffect, useState } from 'react'
import { fetchResults } from '../api'
import type { ResultRow } from '../types'

const SCENARIO_LABELS: Record<string, string> = {
  S1: 'S1 Cloud front bust',
  S2: 'S2 Silent fault',
  S3: 'S3 Eclipse day',
}
const AGENT_LABELS: Record<string, string> = {
  noop: 'Do nothing',
  rules: 'Rule-based',
  llm: 'LLM worker',
}
const AGENT_ORDER = ['noop', 'rules', 'llm']
const SCENARIO_ORDER = ['S1', 'S2', 'S3']

function scoreClass(s: number): string {
  if (s >= 0.5) return 'good'
  if (s > 0.15) return 'mid'
  return 'bad'
}

export default function Leaderboard({ onOpen }: { onOpen: (sc: string, ag: string) => void }) {
  const [rows, setRows] = useState<ResultRow[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchResults()
      .then((r) => setRows(r.results))
      .catch((e) => setError(String(e)))
  }, [])

  if (error) return <div className="loading">Backend unreachable: {error}. Run `make demo`.</div>
  if (!rows) return <div className="loading">Loading leaderboard...</div>

  const cell = (sc: string, ag: string) => {
    const r = rows.find((x) => x.scenario === sc && x.agent === ag)
    if (!r) return <td key={sc} />
    return (
      <td key={sc} className="cell" onClick={() => onOpen(sc, ag)} title="click to replay">
        <div className={`score ${scoreClass(r.score)}`}>{Math.round(r.score * 100)}%</div>
        <div className="cost">{Math.round(r.cost_eur).toLocaleString()} EUR lost</div>
        {r.false_dispatches > 0 && (
          <div className="flag">
            {r.false_dispatches} wasted truck roll{r.false_dispatches > 1 ? 's' : ''}
          </div>
        )}
      </td>
    )
  }

  return (
    <div>
      <p style={{ color: '#8b949e' }}>
        Recoverable losses recovered, per agent per bad day. Every score is bracketed between a
        perfect-foresight oracle (100%) and doing nothing (0%). Click a cell to replay the episode.
      </p>
      <table className="board">
        <thead>
          <tr>
            <th>agent \ scenario</th>
            {SCENARIO_ORDER.map((sc) => (
              <th key={sc}>{SCENARIO_LABELS[sc]}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {AGENT_ORDER.map((ag) => (
            <tr key={ag}>
              <th>{AGENT_LABELS[ag]}</th>
              {SCENARIO_ORDER.map((sc) => cell(sc, ag))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
