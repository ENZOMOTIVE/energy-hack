import type { StepRecord } from '../types'

export default function EuroCounter({ step }: { step: StepRecord }) {
  const saved = step.cum_cost_floor_eur - step.cum_cost_eur
  return (
    <div className="counters">
      <div className="counter">
        <div className="label">lost so far (this agent)</div>
        <div className="value">{Math.round(step.cum_cost_eur).toLocaleString()} EUR</div>
      </div>
      <div className="counter">
        <div className="label">lost doing nothing (ghost)</div>
        <div className="value">{Math.round(step.cum_cost_floor_eur).toLocaleString()} EUR</div>
      </div>
      <div className="counter">
        <div className="label">protected by acting</div>
        <div className={`value ${saved >= 0 ? 'saved' : ''}`}>
          {Math.round(saved).toLocaleString()} EUR
        </div>
      </div>
    </div>
  )
}
