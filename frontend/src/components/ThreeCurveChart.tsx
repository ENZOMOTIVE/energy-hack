import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ReferenceArea,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { StepRecord } from '../types'

function hhmm(iso: string): string {
  return iso.slice(11, 16)
}

export default function ThreeCurveChart({
  steps,
  playhead,
  showEclipse = false,
}: {
  steps: StepRecord[]
  playhead: number
  showEclipse?: boolean
}) {
  const sum = (rec: Record<string, number>) =>
    Object.values(rec).reduce((a, b) => a + b, 0)

  const data = steps.map((s) => ({
    time: hhmm(s.time),
    forecast: s.k <= playhead ? +sum(s.forecast_mw).toFixed(1) : null,
    weatherExpected: s.k <= playhead ? +sum(s.twin_mw).toFixed(1) : null,
    actual: s.k <= playhead ? +sum(s.actual_mw).toFixed(1) : null,
    schedule: s.k <= playhead ? +sum(s.schedule_mw).toFixed(1) : null,
    price: s.da_price,
  }))

  return (
    <ResponsiveContainer width="100%" height={320}>
      <LineChart data={data} margin={{ top: 6, right: 8, bottom: 0, left: 0 }}>
        <CartesianGrid stroke="#21262d" />
        <XAxis dataKey="time" interval={11} stroke="#8b949e" fontSize={12} />
        <YAxis
          stroke="#8b949e"
          fontSize={12}
          label={{ value: 'MW', angle: -90, position: 'insideLeft', fill: '#8b949e' }}
        />
        <YAxis
          yAxisId="price"
          orientation="right"
          stroke="#544"
          fontSize={11}
          domain={[0, 400]}
          hide
        />
        <Tooltip
          contentStyle={{ background: '#161b22', border: '1px solid #30363d' }}
          labelStyle={{ color: '#e6edf3' }}
        />
        <Legend />
        {showEclipse && (
          <ReferenceArea
            x1="19:15"
            x2="21:15"
            fill="#d29922"
            fillOpacity={0.08}
            stroke="#d29922"
            strokeOpacity={0.3}
            label={{ value: 'eclipse 19:20-21:10', position: 'insideTop', fill: '#d29922', fontSize: 12 }}
          />
        )}
        <Line
          yAxisId="price"
          dataKey="price"
          name="DA price (EUR/MWh)"
          stroke="#6e4046"
          dot={false}
          strokeWidth={1}
        />
        <Line
          dataKey="forecast"
          name="expected from forecast"
          stroke="#8b949e"
          strokeDasharray="6 4"
          dot={false}
          strokeWidth={1.5}
          isAnimationActive={false}
        />
        <Line
          dataKey="schedule"
          name="scheduled (after trades)"
          stroke="#3fb950"
          type="stepAfter"
          dot={false}
          strokeWidth={1.5}
          isAnimationActive={false}
        />
        <Line
          dataKey="weatherExpected"
          name="expected from actual weather"
          stroke="#d29922"
          dot={false}
          strokeWidth={1.5}
          isAnimationActive={false}
        />
        <Line
          dataKey="actual"
          name="actual production"
          stroke="#388bfd"
          dot={false}
          strokeWidth={2.5}
          isAnimationActive={false}
        />
      </LineChart>
    </ResponsiveContainer>
  )
}
