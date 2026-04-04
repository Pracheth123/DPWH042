import { useState, useMemo } from 'react'
import {
  ResponsiveContainer,
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  BarChart, Bar, Cell,
  AreaChart, Area,
} from 'recharts'
import { useAlerts } from '../context/AlertsContext'
import { getSignalConfig } from '../lib/utils'

const RANGES = [
  { label: '1h',  ms: 3_600_000 },
  { label: '24h', ms: 86_400_000 },
  { label: '7d',  ms: 7 * 86_400_000 },
]

const SIGNAL_TYPES = ['shortage_signal', 'price_hike', 'urgency_sale', 'neutral']
const COLORS = {
  shortage_signal: '#E24B4A',
  price_hike:      '#EF9F27',
  urgency_sale:    '#7F77DD',
  neutral:         '#378ADD',
}

// Custom dark tooltip
function DarkTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-[#1a2235] border border-[#1e2d45] rounded-xl px-4 py-3 shadow-2xl">
      <p className="text-slate-400 text-xs mb-2">{label}</p>
      {payload.map(p => (
        <p key={p.name} className="text-xs font-mono" style={{ color: p.color }}>
          {p.name}: {p.value}
        </p>
      ))}
    </div>
  )
}

export default function Analytics() {
  const { alerts } = useAlerts()
  const [range, setRange] = useState(1)  // index into RANGES

  const { ms: rangeMs, label: rangeLabel } = RANGES[range]
  const cutoff = Date.now() - rangeMs

  const inRange = useMemo(() =>
    alerts.filter(a => new Date(a.event_time || a.created_at).getTime() >= cutoff),
    [alerts, cutoff]
  )

  // ── Line chart: signal volume per bucket per signal_type ─────────────────────
  const lineData = useMemo(() => {
    const buckets = range === 0 ? 12 : range === 1 ? 24 : 28
    const bucketMs = rangeMs / buckets
    return Array.from({ length: buckets }, (_, i) => {
      const bStart = cutoff + i * bucketMs
      const bEnd   = bStart + bucketMs
      const label  = range === 2
        ? new Date(bStart).toLocaleDateString('en', { weekday: 'short' })
        : `${new Date(bStart).getHours()}:00`
      const row = { t: label }
      SIGNAL_TYPES.forEach(type => {
        row[type] = inRange.filter(a => {
          const t = new Date(a.event_time || a.created_at).getTime()
          return t >= bStart && t < bEnd && a.signal_type === type
        }).length
      })
      return row
    })
  }, [inRange, cutoff, rangeMs, range])

  // ── Bar chart: signals per commodity ─────────────────────────────────────────
  const commodityData = useMemo(() => {
    const map = {}
    inRange.forEach(a => {
      const c = a.commodity || 'unknown'
      map[c] = (map[c] || 0) + 1
    })
    return Object.entries(map)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 12)
      .map(([name, value]) => ({ name, value }))
  }, [inRange])

  // ── Histogram: confidence distribution ───────────────────────────────────────
  const histData = useMemo(() => {
    const buckets = 10
    const bins = Array.from({ length: buckets }, (_, i) => ({
      range: `${i * 10}-${(i + 1) * 10}%`,
      count: 0,
    }))
    inRange.forEach(a => {
      const c = a.confidence ?? 0
      const idx = Math.min(9, Math.floor(c * buckets))
      bins[idx].count++
    })
    return bins
  }, [inRange])

  const axisStyle = { fill: '#64748b', fontSize: 11 }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-white font-bold text-xl tracking-tight">Analytics</h1>
          <p className="text-slate-500 text-sm mt-0.5">{inRange.length} signals in range</p>
        </div>
        {/* Range switcher */}
        <div className="flex gap-1.5 bg-[#1a2235] border border-[#1e2d45] rounded-xl p-1">
          {RANGES.map((r, i) => (
            <button
              key={r.label}
              onClick={() => setRange(i)}
              className={`px-4 py-1.5 rounded-lg text-xs font-bold transition-all ${
                range === i
                  ? 'bg-red-500/20 text-red-400 border border-red-500/30'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              {r.label}
            </button>
          ))}
        </div>
      </div>

      {/* Line chart — volume by signal type */}
      <div className="card p-6">
        <p className="text-slate-300 font-semibold text-sm mb-5">Signal Volume Over Time</p>
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={lineData} margin={{ top: 5, right: 10, left: -20, bottom: 5 }}>
            <CartesianGrid stroke="#1e2d45" strokeDasharray="4 4" />
            <XAxis dataKey="t" tick={axisStyle} axisLine={false} tickLine={false} interval="preserveStartEnd" />
            <YAxis tick={axisStyle} axisLine={false} tickLine={false} />
            <Tooltip content={<DarkTooltip />} />
            <Legend
              formatter={(val) => (
                <span style={{ color: COLORS[val], fontSize: 11 }}>
                  {getSignalConfig(val).label}
                </span>
              )}
            />
            {SIGNAL_TYPES.map(type => (
              <Line
                key={type}
                type="monotone"
                dataKey={type}
                name={type}
                stroke={COLORS[type]}
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 4, fill: COLORS[type] }}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="grid grid-cols-2 gap-6">
        {/* Horizontal bar — commodity */}
        <div className="card p-6">
          <p className="text-slate-300 font-semibold text-sm mb-5">Signals by Commodity</p>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart
              data={commodityData}
              layout="vertical"
              margin={{ top: 0, right: 10, left: 10, bottom: 0 }}
            >
              <CartesianGrid stroke="#1e2d45" strokeDasharray="4 4" horizontal={false} />
              <XAxis type="number" tick={axisStyle} axisLine={false} tickLine={false} />
              <YAxis type="category" dataKey="name" tick={{ ...axisStyle, fontSize: 10 }} axisLine={false} tickLine={false} width={80} />
              <Tooltip content={<DarkTooltip />} />
              <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                {commodityData.map((_, i) => (
                  <Cell key={i} fill={`hsl(${210 + i * 15}, 70%, 55%)`} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Histogram — confidence */}
        <div className="card p-6">
          <p className="text-slate-300 font-semibold text-sm mb-5">Confidence Distribution</p>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={histData} margin={{ top: 0, right: 10, left: -20, bottom: 0 }}>
              <CartesianGrid stroke="#1e2d45" strokeDasharray="4 4" />
              <XAxis dataKey="range" tick={{ ...axisStyle, fontSize: 10 }} axisLine={false} tickLine={false} />
              <YAxis tick={axisStyle} axisLine={false} tickLine={false} />
              <Tooltip content={<DarkTooltip />} />
              <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                {histData.map((d, i) => {
                  const pct = (i + 1) / 10
                  const color = pct >= 0.75 ? '#E24B4A' : pct >= 0.5 ? '#EF9F27' : '#378ADD'
                  return <Cell key={i} fill={color} />
                })}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  )
}
