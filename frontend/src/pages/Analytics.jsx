import { useState, useMemo } from 'react'
import {
  ResponsiveContainer,
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  BarChart, Bar, Cell,
} from 'recharts'
import { useAlerts } from '../context/AlertsContext'

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
const SIGNAL_LABELS = {
  shortage_signal: 'Shortage',
  price_hike:      'Price Hike',
  urgency_sale:    'Urgency Sale',
  neutral:         'Neutral',
}

// ── Demo seed data: shown when no real signals exist in range ────────────────
// Gives the chart a realistic look for demo/hackathon even before live data arrives.
const DEMO_LINE_DATA = [
  { t: '0:00',  shortage_signal: 0, price_hike: 1, urgency_sale: 0, neutral: 2 },
  { t: '1:00',  shortage_signal: 1, price_hike: 0, urgency_sale: 1, neutral: 3 },
  { t: '2:00',  shortage_signal: 0, price_hike: 2, urgency_sale: 0, neutral: 1 },
  { t: '3:00',  shortage_signal: 2, price_hike: 1, urgency_sale: 2, neutral: 2 },
  { t: '4:00',  shortage_signal: 1, price_hike: 3, urgency_sale: 1, neutral: 4 },
  { t: '5:00',  shortage_signal: 3, price_hike: 2, urgency_sale: 3, neutral: 2 },
  { t: '6:00',  shortage_signal: 4, price_hike: 4, urgency_sale: 2, neutral: 5 },
  { t: '7:00',  shortage_signal: 2, price_hike: 5, urgency_sale: 4, neutral: 3 },
  { t: '8:00',  shortage_signal: 5, price_hike: 3, urgency_sale: 3, neutral: 6 },
  { t: '9:00',  shortage_signal: 3, price_hike: 6, urgency_sale: 5, neutral: 4 },
  { t:'10:00',  shortage_signal: 6, price_hike: 4, urgency_sale: 4, neutral: 7 },
  { t:'11:00',  shortage_signal: 4, price_hike: 7, urgency_sale: 6, neutral: 5 },
  { t:'12:00',  shortage_signal: 7, price_hike: 5, urgency_sale: 5, neutral: 8 },
  { t:'13:00',  shortage_signal: 5, price_hike: 8, urgency_sale: 7, neutral: 6 },
  { t:'14:00',  shortage_signal: 8, price_hike: 6, urgency_sale: 6, neutral: 9 },
  { t:'15:00',  shortage_signal: 6, price_hike: 9, urgency_sale: 8, neutral: 7 },
  { t:'16:00',  shortage_signal: 9, price_hike: 7, urgency_sale: 7, neutral:10 },
  { t:'17:00',  shortage_signal: 7, price_hike:10, urgency_sale: 9, neutral: 8 },
  { t:'18:00',  shortage_signal:10, price_hike: 8, urgency_sale:10, neutral:11 },
  { t:'19:00',  shortage_signal: 8, price_hike:11, urgency_sale: 8, neutral: 9 },
  { t:'20:00',  shortage_signal:11, price_hike: 9, urgency_sale:11, neutral:12 },
  { t:'21:00',  shortage_signal: 9, price_hike:12, urgency_sale: 9, neutral:10 },
  { t:'22:00',  shortage_signal:12, price_hike:10, urgency_sale:12, neutral:13 },
  { t:'23:00',  shortage_signal:10, price_hike:13, urgency_sale:10, neutral:11 },
]

const DEMO_COMMODITY_DATA = [
  { name: 'wheat',       value: 23 },
  { name: 'fuel',        value: 19 },
  { name: 'rice',        value: 15 },
  { name: 'shipping',    value: 12 },
  { name: 'steel',       value: 9  },
  { name: 'edible_oil',  value: 7  },
  { name: 'sugar',       value: 5  },
  { name: 'fertilizer',  value: 4  },
]

const DEMO_HIST_DATA = [
  { range: '0-10%',  count: 3  },
  { range: '10-20%', count: 7  },
  { range: '20-30%', count: 12 },
  { range: '30-40%', count: 19 },
  { range: '40-50%', count: 24 },
  { range: '50-60%', count: 18 },
  { range: '60-70%', count: 14 },
  { range: '70-80%', count: 9  },
  { range: '80-90%', count: 5  },
  { range:'90-100%', count: 2  },
]

// ── Custom dark tooltip ────────────────────────────────────────────────────────
function DarkTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  return (
    <div style={{
      background: '#1a2235',
      border: '1px solid #1e2d45',
      borderRadius: 10,
      padding: '10px 14px',
      boxShadow: '0 8px 32px rgba(0,0,0,0.6)',
    }}>
      <p style={{ color: '#64748b', fontSize: 11, marginBottom: 8, fontFamily: 'monospace' }}>{label}</p>
      {payload.map(p => (
        <div key={p.name} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
          <span style={{ width: 8, height: 8, borderRadius: '50%', backgroundColor: p.color, flexShrink: 0 }} />
          <span style={{ color: '#94a3b8', fontSize: 11 }}>
            {SIGNAL_LABELS[p.name] || p.name}:
          </span>
          <span style={{ color: p.color, fontWeight: 700, fontSize: 12, fontFamily: 'monospace' }}>
            {p.value}
          </span>
        </div>
      ))}
    </div>
  )
}

function BarTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  return (
    <div style={{
      background: '#1a2235', border: '1px solid #1e2d45',
      borderRadius: 10, padding: '10px 14px',
      boxShadow: '0 8px 32px rgba(0,0,0,0.6)',
    }}>
      <p style={{ color: '#94a3b8', fontSize: 11, marginBottom: 4 }}>{label}</p>
      <p style={{ color: payload[0]?.fill || '#378ADD', fontWeight: 700, fontSize: 13, fontFamily: 'monospace' }}>
        {payload[0]?.value} signals
      </p>
    </div>
  )
}

// ── Chart wrapper: gives ResponsiveContainer a real pixel height ───────────────
// This is the correct recharts pattern. ResponsiveContainer reads the
// rendered height of its immediate parent, NOT minHeight or flex sizing.
function ChartBox({ height = 260, children }) {
  return (
    <div style={{ width: '100%', height }}>
      <ResponsiveContainer width="100%" height="100%">
        {children}
      </ResponsiveContainer>
    </div>
  )
}

// ── Main Analytics page ───────────────────────────────────────────────────────
export default function Analytics() {
  const { alerts } = useAlerts()
  const [range, setRange] = useState(1)

  const { ms: rangeMs } = RANGES[range]
  const cutoff = Date.now() - rangeMs

  const inRange = useMemo(() =>
    alerts.filter(a => new Date(a.event_time || a.created_at).getTime() >= cutoff),
    [alerts, cutoff]
  )

  // ── Volume Over Time (line chart) ──────────────────────────────────────────
  const lineData = useMemo(() => {
    const buckets = range === 0 ? 12 : range === 1 ? 24 : 28
    const bucketMs = rangeMs / buckets
    const rows = Array.from({ length: buckets }, (_, i) => {
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
    // If all values are 0 (no data yet), use demo data so chart is always visible
    const hasAnyData = rows.some(r => SIGNAL_TYPES.some(t => r[t] > 0))
    return hasAnyData ? rows : DEMO_LINE_DATA
  }, [inRange, cutoff, rangeMs, range])

  const isLineDemo = !inRange.length || !lineData.some(r => SIGNAL_TYPES.some(t => r[t] > 0))

  // ── Signals by Commodity (bar chart) ──────────────────────────────────────
  const commodityData = useMemo(() => {
    const map = {}
    inRange.forEach(a => {
      const c = a.commodity || 'unknown'
      map[c] = (map[c] || 0) + 1
    })
    const real = Object.entries(map).sort((a, b) => b[1] - a[1]).slice(0, 12)
      .map(([name, value]) => ({ name, value }))
    return real.length ? real : DEMO_COMMODITY_DATA
  }, [inRange])

  // ── Confidence Distribution (histogram) ───────────────────────────────────
  const histData = useMemo(() => {
    const bins = Array.from({ length: 10 }, (_, i) => ({
      range: `${i * 10}-${(i + 1) * 10}%`,
      count: 0,
    }))
    inRange.forEach(a => {
      const c = a.confidence ?? 0
      const idx = Math.min(9, Math.floor(c * 10))
      bins[idx].count++
    })
    const hasData = bins.some(b => b.count > 0)
    return hasData ? bins : DEMO_HIST_DATA
  }, [inRange])

  const axisStyle = { fill: '#475569', fontSize: 11 }

  return (
    <div className="h-full overflow-y-auto p-6 space-y-6">

      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-white font-bold text-xl tracking-tight">Analytics</h1>
          <p className="text-slate-500 text-sm mt-0.5">
            {inRange.length} live signals in range
            {isLineDemo && <span className="text-amber-500/70 ml-2 text-xs font-mono">(showing demo data — awaiting live feed)</span>}
          </p>
        </div>
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

      {/* ── Signal Volume Over Time ─────────────────────────────────────────── */}
      <div className="card p-6">
        <p className="text-slate-300 font-semibold text-sm mb-5">Signal Volume Over Time</p>
        {/* ChartBox gives ResponsiveContainer a real pixel height to measure */}
        <ChartBox height={260}>
          <LineChart data={lineData} margin={{ top: 5, right: 16, left: -10, bottom: 5 }}>
            <CartesianGrid stroke="#1e2d45" strokeDasharray="4 4" vertical={false} />
            <XAxis
              dataKey="t"
              tick={axisStyle}
              axisLine={false}
              tickLine={false}
              interval="preserveStartEnd"
            />
            <YAxis
              tick={axisStyle}
              axisLine={false}
              tickLine={false}
              allowDecimals={false}
            />
            <Tooltip content={<DarkTooltip />} />
            <Legend
              iconType="circle"
              iconSize={8}
              formatter={(val) => (
                <span style={{ color: COLORS[val] ?? '#94a3b8', fontSize: 11, fontFamily: 'monospace' }}>
                  {SIGNAL_LABELS[val] ?? val}
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
                activeDot={{ r: 4, fill: COLORS[type], stroke: '#0a0f1a', strokeWidth: 2 }}
              />
            ))}
          </LineChart>
        </ChartBox>
      </div>

      <div className="grid grid-cols-2 gap-6">

        {/* ── Signals by Commodity ─────────────────────────────────────────── */}
        <div className="card p-6">
          <p className="text-slate-300 font-semibold text-sm mb-5">Signals by Commodity</p>
          <ChartBox height={260}>
            <BarChart
              data={commodityData}
              layout="vertical"
              margin={{ top: 0, right: 16, left: 8, bottom: 0 }}
            >
              <CartesianGrid stroke="#1e2d45" strokeDasharray="4 4" horizontal={false} />
              <XAxis type="number" tick={axisStyle} axisLine={false} tickLine={false} allowDecimals={false} />
              <YAxis
                type="category"
                dataKey="name"
                tick={{ ...axisStyle, fontSize: 10 }}
                axisLine={false}
                tickLine={false}
                width={80}
              />
              <Tooltip content={<BarTooltip />} />
              <Bar dataKey="value" radius={[0, 4, 4, 0]} maxBarSize={18}>
                {commodityData.map((_, i) => (
                  <Cell key={i} fill={`hsl(${210 + i * 18}, 65%, 55%)`} />
                ))}
              </Bar>
            </BarChart>
          </ChartBox>
        </div>

        {/* ── Confidence Distribution ──────────────────────────────────────── */}
        <div className="card p-6">
          <p className="text-slate-300 font-semibold text-sm mb-5">Confidence Distribution</p>
          <ChartBox height={260}>
            <BarChart data={histData} margin={{ top: 0, right: 16, left: -12, bottom: 0 }}>
              <CartesianGrid stroke="#1e2d45" strokeDasharray="4 4" vertical={false} />
              <XAxis
                dataKey="range"
                tick={{ ...axisStyle, fontSize: 10 }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis tick={axisStyle} axisLine={false} tickLine={false} allowDecimals={false} />
              <Tooltip content={<BarTooltip />} />
              <Bar dataKey="count" radius={[4, 4, 0, 0]} maxBarSize={32}>
                {histData.map((_, i) => {
                  const pct = (i + 1) / 10
                  const color = pct >= 0.75 ? '#E24B4A' : pct >= 0.5 ? '#EF9F27' : '#378ADD'
                  return <Cell key={i} fill={color} />
                })}
              </Bar>
            </BarChart>
          </ChartBox>
        </div>

      </div>
    </div>
  )
}
