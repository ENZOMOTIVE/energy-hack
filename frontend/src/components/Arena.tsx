import { useCallback, useEffect, useRef, useState } from 'react'
import { simulate, type ChaosClouds, type ChaosFault, type DataSource, type HumanAction } from '../api'
import type { Trace } from '../types'
import ArenaPane from './ArenaPane'

const CONTESTANTS: Record<string, string> = {
  rules: 'RULE-BASED',
  llm: 'LLM WORKER',
  noop: 'DO NOTHING',
  human: 'YOU (judge)',
}
// Real-brain agents are precomputed only; arena live-sim is mock-only
export const REAL_BRAIN_LABELS: Record<string, string> = {
  deepseek: 'DEEPSEEK',
  claude: 'CLAUDE',
}
const PARKS = ['zaragoza', 'valencia', 'munich']
const SCENARIO_LABELS: Record<string, string> = {
  S1: 'S1 cloud front',
  S2: 'S2 silent fault',
  S3: 'S3 eclipse day',
}

type Side = 'left' | 'right'

export default function Arena({ onBack, data }: { onBack: () => void; data: DataSource }) {
  const [scenario, setScenario] = useState('S3')
  const [fighters, setFighters] = useState<Record<Side, string>>({ left: 'rules', right: 'llm' })
  const [traces, setTraces] = useState<Record<Side, Trace | null>>({ left: null, right: null })
  const [chaosFaults, setChaosFaults] = useState<ChaosFault[]>([])
  const [chaosClouds, setChaosClouds] = useState<ChaosClouds[]>([])
  const [humanActions, setHumanActions] = useState<Record<Side, HumanAction[]>>({ left: [], right: [] })
  const [chaosPark, setChaosPark] = useState('valencia')
  const [playhead, setPlayhead] = useState(0)
  const [playing, setPlaying] = useState(false)
  const timer = useRef<number | null>(null)

  const reload = useCallback(() => {
    ;(['left', 'right'] as Side[]).forEach((side) => {
      simulate({
        scenario,
        agent: fighters[side],
        data,
        faults: chaosFaults,
        clouds: chaosClouds,
        human_actions: fighters[side] === 'human' ? humanActions[side] : [],
      })
        .then((t) => setTraces((prev) => ({ ...prev, [side]: t })))
        .catch(() => setTraces((prev) => ({ ...prev, [side]: null })))
    })
  }, [scenario, fighters, chaosFaults, chaosClouds, humanActions, data])

  useEffect(reload, [reload])

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
      }, 200)
    }
    return () => {
      if (timer.current) window.clearInterval(timer.current)
    }
  }, [playing])

  const resetEpisode = (sc: string) => {
    setScenario(sc)
    setChaosFaults([])
    setChaosClouds([])
    setHumanActions({ left: [], right: [] })
    setPlayhead(0)
    setPlaying(false)
  }

  const faultUsed = (park: string) => chaosFaults.some((f) => f.park === park) || (scenario === 'S2' && park === 'zaragoza')

  const injectFault = () => {
    if (faultUsed(chaosPark) || playhead >= 94) return
    setChaosFaults((prev) => [...prev, { park: chaosPark, step: playhead + 1, magnitude: 0.5 }])
  }

  const injectClouds = () => {
    if (playhead >= 90) return
    setChaosClouds((prev) => [...prev, { park: chaosPark, start_step: playhead + 1, end_step: Math.min(95, playhead + 13), depth: 0.4 }])
  }

  const humanAct = (side: Side, type: 'trade' | 'dispatch_crew') => {
    const trace = traces[side]
    if (!trace) return
    const step = trace.steps[playhead]
    const action: HumanAction =
      type === 'dispatch_crew'
        ? { k: playhead, type, park: chaosPark }
        : {
            k: playhead,
            type,
            park: chaosPark,
            delta_mw: -Math.max(0, +(step.schedule_mw[chaosPark] - step.actual_mw[chaosPark]).toFixed(1)),
            hours: 2,
          }
    if (action.type === 'trade' && (action.delta_mw ?? 0) >= -0.4) return
    setHumanActions((prev) => ({ ...prev, [side]: [...prev[side], action] }))
  }

  const finished = playhead === 95 && traces.left && traces.right
  let banner = null
  if (finished) {
    const l = traces.left!.totals.cost_eur
    const r = traces.right!.totals.cost_eur
    const tie = Math.abs(l - r) < 1
    const winner = l < r ? 'left' : 'right'
    banner = tie ? (
      <div className="winner-banner tie">DRAW</div>
    ) : (
      <div className={`winner-banner ${winner}`}>
        {CONTESTANTS[fighters[winner]]} WINS | saves {Math.round(Math.abs(l - r)).toLocaleString()} EUR over the rival
      </div>
    )
  }

  const sideControls = (side: Side) =>
    fighters[side] === 'human' && (
      <div className="judge-bar">
        <span className="label">your move ({chaosPark}):</span>
        <button onClick={() => humanAct(side, 'trade')}>BUY BACK GAP 2h</button>
        <button onClick={() => humanAct(side, 'dispatch_crew')}>SEND CREW</button>
      </div>
    )

  return (
    <div>
      <div className="replay-head">
        <button onClick={onBack}>&larr; leaderboard</button>
        <h2 style={{ margin: 0 }}>ARENA</h2>
        <select value={scenario} onChange={(e) => resetEpisode(e.target.value)}>
          {Object.entries(SCENARIO_LABELS).map(([k, v]) => (
            <option key={k} value={k}>
              {v}
            </option>
          ))}
        </select>
      </div>

      <div className="vs-row">
        <select
          className="fighter red"
          value={fighters.left}
          onChange={(e) => {
            setFighters((p) => ({ ...p, left: e.target.value }))
            setHumanActions((p) => ({ ...p, left: [] }))
          }}
        >
          {Object.entries(CONTESTANTS).map(([k, v]) => (
            <option key={k} value={k}>
              {v}
            </option>
          ))}
        </select>
        <span className="vs">VS</span>
        <select
          className="fighter blue"
          value={fighters.right}
          onChange={(e) => {
            setFighters((p) => ({ ...p, right: e.target.value }))
            setHumanActions((p) => ({ ...p, right: [] }))
          }}
        >
          {Object.entries(CONTESTANTS).map(([k, v]) => (
            <option key={k} value={k}>
              {v}
            </option>
          ))}
        </select>
      </div>

      {banner}

      <div className="arena-grid">
        <div>
          <ArenaPane trace={traces.left} playhead={playhead} accent="red" label={CONTESTANTS[fighters.left]} scenario={scenario} />
          {sideControls('left')}
        </div>
        <div>
          <ArenaPane trace={traces.right} playhead={playhead} accent="blue" label={CONTESTANTS[fighters.right]} scenario={scenario} />
          {sideControls('right')}
        </div>
      </div>

      <div className="transport">
        <button onClick={() => setPlaying(!playing)}>{playing ? 'pause' : 'play'}</button>
        <span className="clock">{traces.left?.steps[playhead]?.time.slice(11, 16) ?? '--:--'}</span>
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
        <button onClick={() => resetEpisode(scenario)}>reset</button>
      </div>

      <div className="chaos-bar">
        <span className="label">CHAOS:</span>
        <select value={chaosPark} onChange={(e) => setChaosPark(e.target.value)}>
          {PARKS.map((p) => (
            <option key={p} value={p}>
              {p}
            </option>
          ))}
        </select>
        <button className="chaos" onClick={injectFault} disabled={faultUsed(chaosPark)}>
          BREAK AN INVERTER NOW
        </button>
        <button className="chaos" onClick={injectClouds}>
          CLOUD FRONT NOW +3h
        </button>
        <span className="sub">
          both fighters face the same chaos; the day re-simulates instantly
        </span>
      </div>
    </div>
  )
}
