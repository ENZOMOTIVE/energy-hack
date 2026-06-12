import { useState } from 'react'
import Arena from './components/Arena'
import Leaderboard from './components/Leaderboard'
import Replay from './components/Replay'

type View =
  | { kind: 'board' }
  | { kind: 'replay'; scenario: string; agent: string }
  | { kind: 'arena' }

export default function App() {
  const [view, setView] = useState<View>({ kind: 'board' })
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
      </h1>
      {view.kind === 'board' && (
        <Leaderboard onOpen={(scenario, agent) => setView({ kind: 'replay', scenario, agent })} />
      )}
      {view.kind === 'replay' && (
        <Replay
          scenario={view.scenario}
          agent={view.agent}
          onBack={() => setView({ kind: 'board' })}
        />
      )}
      {view.kind === 'arena' && <Arena onBack={() => setView({ kind: 'board' })} />}
    </div>
  )
}
