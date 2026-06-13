import { useEffect, useState } from 'react'
import { fetchBattery, fetchBatteryModes, type Battery, type BatteryCase } from '../api'

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
const AGENT_LABELS: Record<string, string> = {
  noop: 'Do nothing',
  rules: 'Rule-based',
  llm: 'LLM worker',
}
const ACCENT: Record<string, string> = { noop: '#8b949e', rules: '#f85149', llm: '#3fb950' }

function pct(x: number): string {
  return `${Math.round(x * 100)}%`
}
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
            intelligently generated bad days, scored by tail risk
          </span>
        </h2>
      </div>

      <p style={{ color: '#8b949e', maxWidth: 820 }}>
        Anyone can run an agent on one scripted bad day. Gauntlet generates a battery of them: a
        seeded evolutionary search over a space of weather busts, silent faults, eclipse overlays and
        price regimes, keeping the days with the most recoverable money at stake that best separate a
        good agent from a bad one. Each survivor is Monte-Carlo'd; the score that matters is the
        worst case, not the average.
      </p>

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

      {error && <div className="loading">Backend unreachable: {error}. Run `make battery`.</div>}
      {!error && !battery && <div className="loading">Generating battery...</div>}

      {battery && (
        <>
          <p style={{ color: '#8b949e', fontStyle: 'italic', marginTop: 8 }}>
            {MODE_BLURB[mode]} {battery.k} days, each averaged over {battery.mc_n} Monte-Carlo
            variations.
          </p>

          <Report battery={battery} />
          <CaseGrid battery={battery} />
        </>
      )}
    </div>
  )
}

function Report({ battery }: { battery: Battery }) {
  const agents = battery.contestants
  return (
    <div className="cert">
      <div className="cert-title">CERTIFICATION REPORT</div>
      <div className="cert-grid">
        <div className="cert-head">agent</div>
        <div className="cert-head">pass-rate (score ≥ 50%)</div>
        <div className="cert-head">worst-case P10</div>
        <div className="cert-head">mean</div>
        <div className="cert-head">hardest day it faced</div>
        {agents.map((a) => {
          const r = battery.report[a]
          return (
            <div className="cert-row" key={a} style={{ display: 'contents' }}>
              <div className="cert-agent" style={{ color: ACCENT[a] }}>
                {AGENT_LABELS[a] ?? a}
              </div>
              <div className="cert-bar-cell">
                <div className="cert-bar-track">
                  <div
                    className="cert-bar-fill"
                    style={{ width: pct(r.pass_rate), background: ACCENT[a] }}
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

function CaseGrid({ battery }: { battery: Battery }) {
  return (
    <>
      <div className="cert-title" style={{ marginTop: 22 }}>
        THE BATTERY · {battery.k} GENERATED DAYS (hardest first)
      </div>
      <div className="case-grid">
        {battery.cases.map((c) => (
          <CaseCard key={c.name} c={c} contestants={battery.contestants} />
        ))}
      </div>
    </>
  )
}

function CaseCard({ c, contestants }: { c: BatteryCase; contestants: string[] }) {
  const competent = contestants.filter((a) => a !== 'noop')
  return (
    <div className="case-card">
      <div className="case-name">{c.name}</div>
      <div className="case-label">{c.label}</div>
      <div className="case-stake">{Math.round(c.stake).toLocaleString()} EUR recoverable</div>
      <div className="case-agents">
        {competent.map((a) => {
          const s = c.agents[a].mean
          return (
            <div className="case-chip" key={a}>
              <span className="case-chip-name">{AGENT_LABELS[a] ?? a}</span>
              <span className="case-chip-score" style={{ color: scoreColor(s) }}>
                {pct(s)}
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
