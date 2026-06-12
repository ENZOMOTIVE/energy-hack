import { useEffect, useState } from 'react'
import { fetchResults, type DataSource } from '../api'
import type { ResultRow } from '../types'

const SCENARIO_LABELS: Record<string, string> = {
  S1: 'S1 Cloud front bust',
  S2: 'S2 Silent fault',
  S3: 'S3 Eclipse day',
}
const AGENT_LABELS: Record<string, string> = {
  noop: 'Do nothing',
  rules: 'Rule-based',
  llm: 'LLM worker (mock)',
  deepseek: 'DeepSeek chat',
  claude: 'Claude Sonnet',
}
const AGENT_ORDER = ['noop', 'rules', 'llm', 'deepseek', 'claude']
const SCENARIO_ORDER = ['S1', 'S2', 'S3']

function scoreClass(s: number): string {
  if (s >= 0.5) return 'good'
  if (s > 0.15) return 'mid'
  return 'bad'
}

export default function Leaderboard({
  onOpen,
  data,
}: {
  onOpen: (sc: string, ag: string) => void
  data: DataSource
}) {
  const [rows, setRows] = useState<ResultRow[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setRows(null)
    setError(null)
    fetchResults(data)
      .then((r) => setRows(r.results))
      .catch((e) => setError(String(e)))
  }, [data])

  if (error) return <div className="loading">Backend unreachable: {error}. Run `make demo`.</div>
  if (!rows) return <div className="loading">Loading leaderboard...</div>

  const days = [...new Set(rows.map((r) => r.day).filter(Boolean))]
  const presentAgents = AGENT_ORDER.filter((ag) => rows.some((r) => r.agent === ag))

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
        {r.mc && (
          <div className="cost">
            {r.mc.n} bad days: mean {Math.round(r.mc.mean * 100)}% | P10{' '}
            {Math.round(r.mc.p10 * 100)}%
          </div>
        )}
        {r.brain && (
          <div className="cost" style={{ color: '#58a6ff', fontSize: 11 }}>
            {r.brain}
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
        {data === 'real' && days.length > 0 && (
          <>
            {' '}
            Real days: {days.join(' and ')} (Open-Meteo day-ahead forecasts vs archive, SMARD DE-LU
            prices; S1 is a forecast bust that really happened).
          </>
        )}
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
          {presentAgents.map((ag) => (
            <tr key={ag}>
              <th>{AGENT_LABELS[ag] ?? ag}</th>
              {SCENARIO_ORDER.map((sc) => cell(sc, ag))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
