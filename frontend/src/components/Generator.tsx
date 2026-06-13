import { useEffect, useState } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from 'recharts'
import {
  fetchBattery,
  fetchBatteryModes,
  reportCsvUrl,
  reportPdfUrl,
  type Battery,
  type BatteryCase,
  type WorkerInfo,
} from '../api'

const MODE_LABELS: Record<string, string> = {
  discrimination: 'DISCRIMINATION',
  adversarial_rules: 'ADVERSARIAL vs RULES',
  adversarial_llm: 'ADVERSARIAL vs LLM',
}
const MODE_BLURB: Record<string, string> = {
  discrimination:
    'Agent-agnostic: the search hunts days that put real money at stake AND separate a competent agent from a naive one. The certification suite.',
  adversarial_rules:
    'The same search pointed at the rule-based agent: it mines the exact days that break it. Watch its pass-rate collapse versus the discrimination battery.',
  adversarial_llm:
    'The search pointed at the LLM worker: the days that beat even the smart agent. These are where you would harden it next.',
}
const WORKER_COLOR: Record<string, string> = {
  noop: '#8b949e',
  rules: '#f85149',
  llm: '#3fb950',
  claude: '#cc785c',
  'ds-cautious': '#58a6ff',
  'ds-balanced': '#a371f7',
  'ds-aggressive': '#d29922',
}
const SHORT: Record<string, string> = {
  rules: 'Rules',
  llm: 'Mock',
  claude: 'Claude',
  'ds-cautious': 'Cautious',
  'ds-balanced': 'Balanced',
  'ds-aggressive': 'Aggressive',
}
const CATEGORY_ORDER = ['FAULT', 'WEATHER', 'ECLIPSE', 'COMBO']

const color = (id: string) => WORKER_COLOR[id] ?? '#888'
const pct = (x: number) => `${Math.round(x * 100)}%`
function scoreColor(s: number): string {
  if (s >= 0.5) return '#3fb950'
  if (s > 0.15) return '#d29922'
  return '#f85149'
}

export default function Generator({ onBack }: { onBack: () => void }) {
  const [modes, setModes] = useState<string[]>([])
  const [mode, setMode] = useState<string>('discrimination')
  const [battery, setBattery] = useState<Battery | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchBatteryModes()
      .then((m) => setModes(m.length ? m : ['discrimination']))
      .catch((e) => setError(String(e)))
  }, [])

  useEffect(() => {
    setBattery(null)
    setError(null)
    fetchBattery(mode)
      .then(setBattery)
      .catch((e) => setError(String(e)))
  }, [mode])

  return (
    <div>
      <div className="replay-head">
        <button onClick={onBack}>← leaderboard</button>
        <h2 style={{ margin: 0 }}>
          Test Lab
          <span className="sub" style={{ marginLeft: 10 }}>
            intelligently generated bad days, several workers compared by tail risk
          </span>
        </h2>
      </div>

      <p style={{ color: '#8b949e', maxWidth: 820 }}>
        Anyone can run an agent on one scripted bad day. Gauntlet generates a battery of them: a
        seeded evolutionary search over weather busts, silent faults, eclipse overlays and price
        regimes, keeping the days with the most recoverable money at stake that best separate a good
        agent from a bad one. Then it pits several workers against the same battery and scores them
        on the worst case, not the average.
      </p>

      <div className="gen-toolbar">
        <div className="gen-modes">
          {modes.map((m) => (
            <button
              key={m}
              className={`seg-btn ${mode === m ? 'active' : ''}`}
              onClick={() => setMode(m)}
            >
              {MODE_LABELS[m] ?? m}
            </button>
          ))}
        </div>
        {battery && (
          <div className="dl-row">
            <a className="dl-btn pdf" href={reportPdfUrl(mode)}>
              ↓ PDF report
            </a>
            <a className="dl-btn" href={reportCsvUrl(mode)}>
              ↓ CSV
            </a>
          </div>
        )}
      </div>

      {error && <div className="loading">Backend unreachable: {error}. Run `make battery`.</div>}
      {!error && !battery && <div className="loading">Loading battery...</div>}

      {battery && (
        <>
          <p style={{ color: '#8b949e', fontStyle: 'italic', marginTop: 8 }}>
            {MODE_BLURB[mode]} {battery.k} days; deterministic workers averaged over {battery.mc_n}{' '}
            Monte-Carlo variations
            {battery.persona_single_run ? ', real models (Claude, DeepSeek) one run per day (API-bound)' : ''}.
          </p>

          <Report battery={battery} />
          <Comparison battery={battery} />
          <CaseGrid battery={battery} />
        </>
      )}
    </div>
  )
}

function Report({ battery }: { battery: Battery }) {
  return (
    <div className="cert">
      <div className="cert-title">CERTIFICATION REPORT</div>
      <div className="cert-grid">
        <div className="cert-head">worker</div>
        <div className="cert-head">pass-rate (score ≥ 50%)</div>
        <div className="cert-head">worst-case P10</div>
        <div className="cert-head">mean</div>
        <div className="cert-head">hardest day it faced</div>
        {battery.workers.map((w) => {
          const r = battery.report[w.id]
          if (!r) return null
          return (
            <div key={w.id} style={{ display: 'contents' }}>
              <div className="cert-agent" style={{ color: color(w.id) }}>
                {w.label}
                {(w.kind === 'persona' || w.kind === 'claude') && (
                  <span className="cert-tag">1 run</span>
                )}
              </div>
              <div className="cert-bar-cell">
                <div className="cert-bar-track">
                  <div
                    className="cert-bar-fill"
                    style={{ width: pct(r.pass_rate), background: color(w.id) }}
                  />
                </div>
                <span className="cert-bar-num">{pct(r.pass_rate)}</span>
              </div>
              <div className="cert-num" style={{ color: scoreColor(r.p10) }}>
                {pct(r.p10)}
              </div>
              <div className="cert-num">{pct(r.mean)}</div>
              <div className="cert-hardest">
                {r.hardest.label} <span className="cert-hardest-score">({pct(r.hardest.mean)})</span>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

function Comparison({ battery }: { battery: Battery }) {
  const cats = CATEGORY_ORDER.filter((cat) => battery.cases.some((c) => c.category === cat))
  const barData = cats.map((cat) => {
    const row: Record<string, number | string> = { category: cat }
    const inCat = battery.cases.filter((c) => c.category === cat)
    for (const w of battery.workers) {
      const vals = inCat.map((c) => (c.agents[w.id]?.mean ?? 0) * 100)
      row[w.id] = vals.length ? Math.round(vals.reduce((a, b) => a + b, 0) / vals.length) : 0
    }
    return row
  })

  return (
    <div className="compare">
      <div className="cert-title" style={{ marginTop: 22 }}>
        WORKER COMPARISON
      </div>
      <div className="compare-grid">
        <div className="chart-card">
          <div className="chart-title">Recovery by failure mode</div>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={barData} margin={{ top: 8, right: 8, bottom: 4, left: -18 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#21262d" />
              <XAxis dataKey="category" tick={{ fill: '#8b949e', fontSize: 12 }} />
              <YAxis domain={[0, 100]} tick={{ fill: '#8b949e', fontSize: 11 }} unit="%" />
              <Tooltip
                contentStyle={{ background: '#0d1117', border: '1px solid #30363d' }}
                formatter={(v: number, id: string) => [
                  `${v}%`,
                  battery.workers.find((w) => w.id === id)?.label ?? id,
                ]}
              />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              {battery.workers.map((w) => (
                <Bar key={w.id} dataKey={w.id} name={w.label} fill={color(w.id)} />
              ))}
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="chart-card">
          <div className="chart-title">Risk vs return</div>
          <ResponsiveContainer width="100%" height={260}>
            <ScatterChart margin={{ top: 8, right: 12, bottom: 18, left: -8 }}>
              <CartesianGrid stroke="#21262d" />
              <XAxis
                type="number"
                dataKey="x"
                domain={[0, 100]}
                name="pass-rate"
                unit="%"
                tick={{ fill: '#8b949e', fontSize: 11 }}
                label={{ value: 'pass-rate (reward)', position: 'bottom', fill: '#8b949e', fontSize: 11 }}
              />
              <YAxis
                type="number"
                dataKey="y"
                name="P10"
                unit="%"
                tick={{ fill: '#8b949e', fontSize: 11 }}
                label={{ value: 'P10 (tail safety)', angle: -90, position: 'insideLeft', fill: '#8b949e', fontSize: 11 }}
              />
              <ZAxis range={[120, 120]} />
              <Tooltip
                cursor={{ strokeDasharray: '3 3' }}
                contentStyle={{ background: '#0d1117', border: '1px solid #30363d' }}
                formatter={(v: number) => `${v}%`}
              />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              {battery.workers.map((w) => {
                const r = battery.report[w.id]
                if (!r) return null
                return (
                  <Scatter
                    key={w.id}
                    name={w.label}
                    fill={color(w.id)}
                    data={[{ x: Math.round(r.pass_rate * 100), y: Math.round(r.p10 * 100) }]}
                  />
                )
              })}
            </ScatterChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  )
}

function CaseGrid({ battery }: { battery: Battery }) {
  const competent = battery.workers.filter((w) => w.kind !== 'baseline')
  return (
    <>
      <div className="cert-title" style={{ marginTop: 22 }}>
        THE BATTERY · {battery.k} GENERATED DAYS (hardest first)
      </div>
      <div className="case-grid">
        {battery.cases.map((c) => (
          <CaseCard key={c.name} c={c} workers={competent} />
        ))}
      </div>
    </>
  )
}

function CaseCard({ c, workers }: { c: BatteryCase; workers: WorkerInfo[] }) {
  return (
    <div className="case-card">
      <div className="case-name">
        {c.name} <span className="case-cat">{c.category}</span>
      </div>
      <div className="case-label">{c.label}</div>
      <div className="case-stake">{Math.round(c.stake).toLocaleString()} EUR recoverable</div>
      <div className="case-agents">
        {workers.map((w) => {
          const a = c.agents[w.id]
          if (!a) return null
          return (
            <div className="case-chip" key={w.id} title={w.label}>
              <span className="case-chip-name" style={{ color: color(w.id) }}>
                {SHORT[w.id] ?? w.label}
              </span>
              <span className="case-chip-score" style={{ color: scoreColor(a.mean) }}>
                {pct(a.mean)}
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
