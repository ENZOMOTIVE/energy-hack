import type { Trace } from '../types'
import ThreeCurveChart from './ThreeCurveChart'

export default function ArenaPane({
  trace,
  playhead,
  accent,
  label,
  scenario,
}: {
  trace: Trace | null
  playhead: number
  accent: 'red' | 'blue'
  label: string
  scenario: string
}) {
  if (!trace) {
    return (
      <div className={`pane ${accent}`}>
        <div className="pane-title">{label}</div>
        <div className="loading">simulating...</div>
      </div>
    )
  }
  const step = trace.steps[playhead]
  const saved = step.cum_cost_floor_eur - step.cum_cost_eur
  const lastAction = [...trace.actions].reverse().find((a) => a.k <= playhead)
  const wastedTrucks = trace.actions.filter((a) => a.false_dispatch && a.k <= playhead).length

  return (
    <div className={`pane ${accent}`}>
      <div className="pane-title">
        {label}
        {trace.totals.brain ? <span className="sub"> ({trace.totals.brain})</span> : null}
      </div>
      <ThreeCurveChart steps={trace.steps} playhead={playhead} showEclipse={scenario === 'S3'} height={210} compact />
      <div className="pane-score">
        <div>
          <div className="label">lost</div>
          <div className="big">{Math.round(step.cum_cost_eur).toLocaleString()} EUR</div>
        </div>
        <div>
          <div className="label">vs doing nothing</div>
          <div className={`big ${saved >= 0 ? 'saved' : 'burned'}`}>
            {saved >= 0 ? '+' : ''}
            {Math.round(saved).toLocaleString()}
          </div>
        </div>
        {wastedTrucks > 0 && <div className="trucks">{wastedTrucks} wasted truck roll{wastedTrucks > 1 ? 's' : ''}</div>}
      </div>
      {lastAction ? (
        <div className={`card ${lastAction.type === 'dispatch_crew' ? 'crew' : ''} ${lastAction.false_dispatch ? 'false' : ''}`}>
          <div className="head">
            [{trace.steps[lastAction.k]?.time.slice(11, 16)}]{' '}
            {lastAction.type === 'trade'
              ? `TRADE ${lastAction.park} ${lastAction.delta_mw} MW / ${lastAction.hours} h`
              : `CREW to ${lastAction.park}`}
            {lastAction.false_dispatch && <span className="badge">wasted truck roll</span>}
          </div>
          {lastAction.reason && <div className="reason">{lastAction.reason}</div>}
        </div>
      ) : (
        <div className="card idle">no actions yet</div>
      )}
    </div>
  )
}
