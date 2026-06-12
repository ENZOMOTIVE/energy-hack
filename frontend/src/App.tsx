import { useState } from 'react'
import type { DataSource } from './api'
import Arena from './components/Arena'
import Leaderboard from './components/Leaderboard'
import Replay from './components/Replay'

type View =
  | { kind: 'board' }
  | { kind: 'replay'; scenario: string; agent: string }
  | { kind: 'arena' }

export default function App() {
  const [view, setView] = useState<View>({ kind: 'board' })
  const [data, setData] = useState<DataSource>('synthetic')
  return (
    <div>
      <h1>
        GAUNTLET
        <span className="sub">the proving ground for solar asset-management agents</span>
        {view.kind === 'board' && (
          <button className="enter-arena" onClick={() => setView({ kind: 'arena' })}>
            ENTER ARENA
          </button>
        )}
        <span className="seg">
          {(['synthetic', 'real'] as DataSource[]).map((d) => (
            <button
              key={d}
              className={`seg-btn ${data === d ? 'active' : ''}`}
              onClick={() => setData(d)}
            >
              {d === 'real' ? 'REAL DATA' : 'SYNTHETIC'}
            </button>
          ))}
        </span>
      </h1>
      {view.kind === 'board' && (
        <Leaderboard
          data={data}
          onOpen={(scenario, agent) => setView({ kind: 'replay', scenario, agent })}
        />
      )}
      {view.kind === 'replay' && (
        <Replay
          scenario={view.scenario}
          agent={view.agent}
          data={data}
          onBack={() => setView({ kind: 'board' })}
        />
      )}
      {view.kind === 'arena' && <Arena data={data} onBack={() => setView({ kind: 'board' })} />}
    </div>
  )
}
