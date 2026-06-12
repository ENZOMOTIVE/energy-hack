import type { ActionEntry, StepRecord } from '../types'

function timeOf(steps: StepRecord[], k: number): string {
  return steps[k]?.time.slice(11, 16) ?? '?'
}

export default function ActionCards({
  actions,
  steps,
  playhead,
}: {
  actions: ActionEntry[]
  steps: StepRecord[]
  playhead: number
}) {
  const visible = actions.filter((a) => a.k <= playhead).reverse()
  if (visible.length === 0) {
    return <div className="cards" style={{ color: '#8b949e' }}>No actions yet.</div>
  }
  return (
    <div className="cards">
      {visible.map((a, i) => (
        <div
          key={`${a.k}-${i}`}
          className={`card ${a.type === 'dispatch_crew' ? 'crew' : ''} ${a.false_dispatch ? 'false' : ''}`}
        >
          <div className="head">
            [{timeOf(steps, a.k)}]{' '}
            {a.type === 'trade'
              ? `TRADE ${a.park} ${a.delta_mw > 0 ? '+' : ''}${a.delta_mw} MW for ${a.hours} h`
              : `DISPATCH CREW to ${a.park}`}
            {a.false_dispatch && <span className="badge">wasted truck roll</span>}
          </div>
          {a.reason && <div className="reason">{a.reason}</div>}
        </div>
      ))}
    </div>
  )
}
