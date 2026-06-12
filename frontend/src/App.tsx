import { useState } from 'react'
import Leaderboard from './components/Leaderboard'
import Replay from './components/Replay'

type View = { kind: 'board' } | { kind: 'replay'; scenario: string; agent: string }

export default function App() {
  const [view, setView] = useState<View>({ kind: 'board' })
  return (
    <div>
      <h1>
        GAUNTLET
        <span className="sub">the proving ground for solar asset-management agents</span>
      </h1>
      {view.kind === 'board' ? (
        <Leaderboard onOpen={(scenario, agent) => setView({ kind: 'replay', scenario, agent })} />
      ) : (
        <Replay
          scenario={view.scenario}
          agent={view.agent}
          onBack={() => setView({ kind: 'board' })}
        />
      )}
    </div>
  )
}
