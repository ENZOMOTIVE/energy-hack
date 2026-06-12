import { useEffect, useRef, useState } from 'react'
import { fetchEpisode, type DataSource } from '../api'
import type { Trace } from '../types'
import ActionCards from './ActionCards'
import EuroCounter from './EuroCounter'
import ThreeCurveChart from './ThreeCurveChart'

export default function Replay({
  scenario,
  agent,
  data,
  onBack,
}: {
  scenario: string
  agent: string
  data: DataSource
  onBack: () => void
}) {
  const [trace, setTrace] = useState<Trace | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [playhead, setPlayhead] = useState(0)
  const [playing, setPlaying] = useState(false)
  const timer = useRef<number | null>(null)

  useEffect(() => {
    setTrace(null)
    setPlayhead(0)
    setPlaying(false)
    fetchEpisode(scenario, agent, data)
      .then(setTrace)
      .catch((e) => setError(String(e)))
  }, [scenario, agent, data])

  useEffect(() => {
    if (playing) {
      timer.current = window.setInterval(() => {
        setPlayhead((p) => {
          if (p >= 95) {
            setPlaying(false)
            return 95
          }
          return p + 1
        })
      }, 250) // 4 steps per second
    }
    return () => {
      if (timer.current) window.clearInterval(timer.current)
    }
  }, [playing])

  if (error) return <div className="loading">Failed to load episode: {error}</div>
  if (!trace) return <div className="loading">Loading episode...</div>

  const step = trace.steps[playhead]
  return (
    <div>
      <div className="replay-head">
        <button onClick={onBack}>&larr; leaderboard</button>
        <h2 style={{ margin: 0 }}>
          {scenario} / {agent}
        </h2>
        <span style={{ color: '#8b949e' }}>
          score {Math.round(trace.totals.score * 100)}%
          {trace.totals.brain ? ` | brain: ${trace.totals.brain}` : ''}
        </span>
      </div>
      <ThreeCurveChart steps={trace.steps} playhead={playhead} showEclipse={scenario === 'S3'} />
      <div className="transport">
        <button onClick={() => setPlaying(!playing)}>{playing ? 'pause' : 'play'}</button>
        <span className="clock">{step.time.slice(11, 16)}</span>
        <input
          type="range"
          min={0}
          max={95}
          value={playhead}
          onChange={(e) => {
            setPlaying(false)
            setPlayhead(Number(e.target.value))
          }}
        />
      </div>
      <EuroCounter step={step} />
      <ActionCards actions={trace.actions} steps={trace.steps} playhead={playhead} />
    </div>
  )
}
