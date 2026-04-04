import { useState, useMemo } from 'react'
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer, ReferenceLine,
} from 'recharts'
import {
  AlertTriangle, TrendingDown, TrendingUp, Shield,
  DollarSign, Package, Navigation, Zap, ChevronDown, ChevronUp,
  ArrowRight, Clock, MapPin, BarChart2,
} from 'lucide-react'

// ─────────────────────────────────────────────────────────────────────────────
// ANOMALY SCENARIOS
// Each scenario has its own 14-day projection dataset and mitigation strategy.
// ─────────────────────────────────────────────────────────────────────────────
const SCENARIOS = [
  {
    id: 'singapore_port',
    label: 'Critical Port Delay — Singapore',
    severity: 'critical',
    icon: Navigation,
    accentColor: '#E24B4A',
    glowColor: 'rgba(226,75,74,0.18)',
    borderColor: 'rgba(226,75,74,0.35)',
    detected: '2 hours ago',
    location: 'Singapore Strait',
    commodity: 'Electronics / Semiconductors',
    description:
      'GhostGrid detected a 6-day port congestion event at Singapore PSA Terminal. ' +
      '23 container vessels are anchored, freight rates up 38%. ' +
      'Your inbound semiconductor shipment (3 containers, est. value $1.2M) is affected.',
    action: {
      title: 'GhostGrid Recommended Mitigation',
      steps: [
        'Reroute 2 of 3 containers via Port Klang (ETA recovers by 4 days)',
        'Secure local buffer stock from Singapore Free Trade Zone',
        'Activate spot-freight contract with secondary carrier',
        'Notify downstream partners of 72-hour adjusted ETA',
      ],
      savings: '$42,000',
      timeToAct: '18 hours',
      successRate: 87,
    },
    // 14-day sales projection (Day 1–3: pre-anomaly, Day 4+: diverge)
    data: [
      { name: 'D1',  unmitigated: 95000,  mitigated: 95000  },
      { name: 'D2',  unmitigated: 98000,  mitigated: 98000  },
      { name: 'D3',  unmitigated: 97000,  mitigated: 97000  },
      { name: 'D4',  unmitigated: 91000,  mitigated: 95000  },
      { name: 'D5',  unmitigated: 78000,  mitigated: 93000  },
      { name: 'D6',  unmitigated: 54000,  mitigated: 91000  },
      { name: 'D7',  unmitigated: 31000,  mitigated: 89000  },
      { name: 'D8',  unmitigated: 18000,  mitigated: 88000  },
      { name: 'D9',  unmitigated: 12000,  mitigated: 90000  },
      { name: 'D10', unmitigated: 9000,   mitigated: 92000  },
      { name: 'D11', unmitigated: 14000,  mitigated: 94000  },
      { name: 'D12', unmitigated: 29000,  mitigated: 96000  },
      { name: 'D13', unmitigated: 48000,  mitigated: 97000  },
      { name: 'D14', unmitigated: 71000,  mitigated: 98000  },
    ],
    totalLoss: '$431,000',
    totalSaved: '$389,000',
  },
  {
    id: 'karachi_wheat',
    label: 'Wheat Shortage — Karachi Mills',
    severity: 'high',
    icon: Package,
    accentColor: '#EF9F27',
    glowColor: 'rgba(239,159,39,0.18)',
    borderColor: 'rgba(239,159,39,0.35)',
    detected: '34 minutes ago',
    location: 'Karachi, Pakistan',
    commodity: 'Wheat / Flour (Atta)',
    description:
      'GhostGrid NLP detected 127 Telegram messages and 34 news articles ' +
      'reporting critical flour shortages across Karachi wholesale markets. ' +
      'Government price controls expected within 48h. Your bakery supply chain is at risk.',
    action: {
      title: 'GhostGrid Recommended Mitigation',
      steps: [
        'Pre-purchase 60-day wheat inventory at current market price immediately',
        'Lock in forward contracts with 2 alternative mills in Lahore',
        'File for government buffer-stock allocation (window closes in 48h)',
        'Raise retail price by 4% now to protect margin before controls kick in',
      ],
      savings: '$28,500',
      timeToAct: '48 hours',
      successRate: 92,
    },
    data: [
      { name: 'D1',  unmitigated: 42000,  mitigated: 42000  },
      { name: 'D2',  unmitigated: 44000,  mitigated: 44000  },
      { name: 'D3',  unmitigated: 43000,  mitigated: 43000  },
      { name: 'D4',  unmitigated: 40000,  mitigated: 43500  },
      { name: 'D5',  unmitigated: 34000,  mitigated: 44000  },
      { name: 'D6',  unmitigated: 24000,  mitigated: 43000  },
      { name: 'D7',  unmitigated: 14000,  mitigated: 42000  },
      { name: 'D8',  unmitigated: 8000,   mitigated: 41500  },
      { name: 'D9',  unmitigated: 6000,   mitigated: 42000  },
      { name: 'D10', unmitigated: 8000,   mitigated: 43000  },
      { name: 'D11', unmitigated: 14000,  mitigated: 44000  },
      { name: 'D12', unmitigated: 24000,  mitigated: 44500  },
      { name: 'D13', unmitigated: 35000,  mitigated: 45000  },
      { name: 'D14', unmitigated: 41000,  mitigated: 45500  },
    ],
    totalLoss: '$198,000',
    totalSaved: '$170,000',
  },
  {
    id: 'dubai_fuel',
    label: 'Fuel Price Spike — Dubai',
    severity: 'medium',
    icon: TrendingUp,
    accentColor: '#7F77DD',
    glowColor: 'rgba(127,119,221,0.18)',
    borderColor: 'rgba(127,119,221,0.35)',
    detected: '3 hours ago',
    location: 'Dubai, UAE',
    commodity: 'Diesel / LPG',
    description:
      'GhostGrid detected correlated signals: refinery output drop + 45% diesel price ' +
      'spike across Dubai wholesale. Social media in Roman Urdu confirms independent ' +
      'trucker strikes. Your logistics cost per km is projected to rise 31% within 5 days.',
    action: {
      title: 'GhostGrid Recommended Mitigation',
      steps: [
        'Hedge 30-day diesel needs via ENOC forward contract today',
        'Consolidate shipments to reduce total km by 22% this week',
        'Negotiate temporary fuel surcharge clause with 3 key customers',
        'Activate electric-vehicle fleet (where available) for last-mile delivery',
      ],
      savings: '$19,200',
      timeToAct: '5 days',
      successRate: 79,
    },
    data: [
      { name: 'D1',  unmitigated: 67000,  mitigated: 67000  },
      { name: 'D2',  unmitigated: 68000,  mitigated: 68000  },
      { name: 'D3',  unmitigated: 67500,  mitigated: 67500  },
      { name: 'D4',  unmitigated: 65000,  mitigated: 67500  },
      { name: 'D5',  unmitigated: 60000,  mitigated: 67000  },
      { name: 'D6',  unmitigated: 53000,  mitigated: 66500  },
      { name: 'D7',  unmitigated: 46000,  mitigated: 66000  },
      { name: 'D8',  unmitigated: 41000,  mitigated: 66000  },
      { name: 'D9',  unmitigated: 39000,  mitigated: 66500  },
      { name: 'D10', unmitigated: 42000,  mitigated: 67000  },
      { name: 'D11', unmitigated: 49000,  mitigated: 67500  },
      { name: 'D12', unmitigated: 57000,  mitigated: 68000  },
      { name: 'D13', unmitigated: 63000,  mitigated: 68000  },
      { name: 'D14', unmitigated: 67000,  mitigated: 68500  },
    ],
    totalLoss: '$142,500',
    totalSaved: '$123,000',
  },
]

// ─────────────────────────────────────────────────────────────────────────────
// SEVERITY CONFIG
// ─────────────────────────────────────────────────────────────────────────────
const SEVERITY_LABEL = {
  critical: { label: 'CRITICAL', bg: 'rgba(226,75,74,0.15)', text: '#E24B4A', border: 'rgba(226,75,74,0.35)' },
  high:     { label: 'HIGH',     bg: 'rgba(239,159,39,0.15)', text: '#EF9F27', border: 'rgba(239,159,39,0.35)' },
  medium:   { label: 'MEDIUM',   bg: 'rgba(127,119,221,0.15)', text: '#7F77DD', border: 'rgba(127,119,221,0.35)' },
}

// ─────────────────────────────────────────────────────────────────────────────
// CUSTOM TOOLTIP
// ─────────────────────────────────────────────────────────────────────────────
function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  const fmt = (v) => `$${Number(v).toLocaleString()}`
  return (
    <div style={{
      background: '#1a2235',
      border: '1px solid #1e2d45',
      borderRadius: 10,
      padding: '10px 14px',
      boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
      minWidth: 180,
    }}>
      <p style={{ color: '#94a3b8', fontSize: 11, marginBottom: 8, fontFamily: 'monospace', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
        {label}
      </p>
      {payload.map((p, i) => (
        <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
          <span style={{ width: 8, height: 8, borderRadius: '50%', backgroundColor: p.color, flexShrink: 0 }} />
          <span style={{ color: '#94a3b8', fontSize: 11 }}>
            {p.name === 'mitigated_sales' ? 'With GhostGrid' : 'Without GhostGrid'}:
          </span>
          <span style={{ color: p.color, fontWeight: 700, fontSize: 12, fontFamily: 'monospace' }}>
            {fmt(p.value)}
          </span>
        </div>
      ))}
      {payload.length === 2 && (
        <div style={{ marginTop: 8, paddingTop: 8, borderTop: '1px solid #1e2d45', color: '#1D9E75', fontSize: 11, fontFamily: 'monospace' }}>
          Saved: {fmt(payload[1].value - payload[0].value)}
        </div>
      )}
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// MAIN COMPONENT
// ─────────────────────────────────────────────────────────────────────────────
export default function TraderSimulator() {
  const [activeScenario, setActiveScenario] = useState(SCENARIOS[0])
  const [mitigationApplied, setMitigationApplied] = useState(false)
  const [stepsExpanded, setStepsExpanded] = useState(true)

  const s = activeScenario
  const sev = SEVERITY_LABEL[s.severity]
  const Icon = s.icon

  // Compute totals from data
  const { totalUnmitigated, totalMitigated } = useMemo(() => {
    const u = s.data.reduce((acc, d) => acc + d.unmitigated, 0)
    const m = s.data.reduce((acc, d) => acc + d.mitigated, 0)
    return { totalUnmitigated: u, totalMitigated: m }
  }, [s])

  const pctSaved = Math.round(((totalMitigated - totalUnmitigated) / totalMitigated) * 100)

  return (
    <div className="h-full flex flex-col p-6 gap-5 overflow-y-auto">

      {/* ── Header ── */}
      <div className="flex items-start justify-between shrink-0">
        <div>
          <h1 className="text-white font-bold text-xl tracking-tight flex items-center gap-2">
            <Zap size={20} className="text-red-400" />
            AI Impact & Mitigation Simulator
          </h1>
          <p className="text-slate-500 text-sm mt-0.5">
            Visualise the financial impact of acting on GhostGrid signals vs. ignoring them
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs font-mono px-3 py-1.5 rounded-full"
          style={{ background: 'rgba(29,158,117,0.12)', color: '#1D9E75', border: '1px solid rgba(29,158,117,0.25)' }}>
          <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
          LIVE SIMULATION
        </div>
      </div>

      {/* ── Scenario Selector ── */}
      <div className="grid grid-cols-3 gap-3 shrink-0">
        {SCENARIOS.map((sc) => {
          const ScIcon = sc.icon
          const isActive = sc.id === activeScenario.id
          return (
            <button
              key={sc.id}
              onClick={() => { setActiveScenario(sc); setMitigationApplied(false) }}
              className="text-left p-4 rounded-xl transition-all duration-200"
              style={{
                background: isActive ? sc.glowColor : 'rgba(26,34,53,0.8)',
                border: `1px solid ${isActive ? sc.borderColor : '#1e2d45'}`,
                boxShadow: isActive ? `0 0 24px ${sc.glowColor}` : 'none',
              }}
            >
              <div className="flex items-center gap-2 mb-1.5">
                <ScIcon size={15} style={{ color: sc.accentColor }} />
                <span className="text-[10px] font-mono uppercase tracking-widest"
                  style={{ color: SEVERITY_LABEL[sc.severity].text }}>
                  {SEVERITY_LABEL[sc.severity].label}
                </span>
              </div>
              <p className="text-xs font-semibold text-slate-200 leading-snug">{sc.label}</p>
              <p className="text-[10px] text-slate-500 mt-1 font-mono flex items-center gap-1">
                <Clock size={9} /> {sc.detected}
              </p>
            </button>
          )
        })}
      </div>

      {/* ── Main 2-column grid ── */}
      <div className="flex-1 grid grid-cols-12 gap-4 min-h-0">

        {/* ── Left column: Anomaly + Action cards ── */}
        <div className="col-span-4 flex flex-col gap-4">

          {/* Active Anomaly Card */}
          <div className="card p-5" style={{
            border: `1px solid ${s.borderColor}`,
            boxShadow: `0 0 32px ${s.glowColor}`,
          }}>
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <div style={{
                  width: 32, height: 32, borderRadius: 8,
                  background: s.glowColor,
                  border: `1px solid ${s.borderColor}`,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                }}>
                  <Icon size={16} style={{ color: s.accentColor }} />
                </div>
                <p className="text-xs font-bold text-slate-200 uppercase tracking-wider">
                  Active Anomaly
                </p>
              </div>
              <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded"
                style={{ background: sev.bg, color: sev.text, border: `1px solid ${sev.border}` }}>
                {sev.label}
              </span>
            </div>

            <p className="font-bold text-white text-sm mb-2">{s.label}</p>

            <div className="space-y-1.5 mb-3">
              <div className="flex items-center gap-2 text-[11px] text-slate-400">
                <MapPin size={11} style={{ color: s.accentColor }} />
                <span>{s.location}</span>
              </div>
              <div className="flex items-center gap-2 text-[11px] text-slate-400">
                <Package size={11} style={{ color: s.accentColor }} />
                <span>{s.commodity}</span>
              </div>
              <div className="flex items-center gap-2 text-[11px] text-slate-400">
                <Clock size={11} style={{ color: s.accentColor }} />
                <span>Detected {s.detected}</span>
              </div>
            </div>

            <p className="text-[11px] text-slate-400 leading-relaxed border-t border-[#1e2d45] pt-3">
              {s.description}
            </p>

            {/* Projected loss warning */}
            <div className="mt-3 p-3 rounded-lg"
              style={{ background: 'rgba(226,75,74,0.07)', border: '1px solid rgba(226,75,74,0.2)' }}>
              <div className="flex items-center gap-2">
                <TrendingDown size={14} className="text-red-400" />
                <span className="text-[11px] text-red-400 font-mono font-bold">
                  Projected 14-day loss if ignored:
                </span>
              </div>
              <p className="text-red-400 font-bold text-lg font-mono mt-1">{s.totalLoss}</p>
            </div>
          </div>

          {/* GhostGrid Action Card */}
          <div className="card p-5 flex-1"
            style={{ border: '1px solid rgba(29,158,117,0.3)', boxShadow: '0 0 24px rgba(29,158,117,0.08)' }}>
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <div style={{
                  width: 32, height: 32, borderRadius: 8,
                  background: 'rgba(29,158,117,0.12)',
                  border: '1px solid rgba(29,158,117,0.3)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                }}>
                  <Shield size={16} className="text-green-400" />
                </div>
                <p className="text-xs font-bold text-slate-200 uppercase tracking-wider">
                  AI Recommendation
                </p>
              </div>
              <button
                onClick={() => setStepsExpanded(x => !x)}
                className="text-slate-500 hover:text-slate-300 transition-colors">
                {stepsExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
              </button>
            </div>

            {stepsExpanded && (
              <div className="space-y-2 mb-4">
                {s.action.steps.map((step, i) => (
                  <div key={i} className="flex items-start gap-2">
                    <span className="shrink-0 w-4 h-4 rounded-full text-[9px] font-bold flex items-center justify-center mt-0.5"
                      style={{ background: 'rgba(29,158,117,0.2)', color: '#1D9E75', border: '1px solid rgba(29,158,117,0.35)' }}>
                      {i + 1}
                    </span>
                    <p className="text-[11px] text-slate-300 leading-relaxed">{step}</p>
                  </div>
                ))}
              </div>
            )}

            {/* Metrics row */}
            <div className="grid grid-cols-3 gap-2 border-t border-[#1e2d45] pt-3">
              <div className="text-center">
                <p className="text-[9px] text-slate-500 uppercase tracking-wider mb-0.5">Est. Savings</p>
                <p className="text-green-400 font-bold font-mono text-sm">{s.action.savings}</p>
              </div>
              <div className="text-center border-x border-[#1e2d45]">
                <p className="text-[9px] text-slate-500 uppercase tracking-wider mb-0.5">Act Within</p>
                <p className="text-amber-400 font-bold font-mono text-sm">{s.action.timeToAct}</p>
              </div>
              <div className="text-center">
                <p className="text-[9px] text-slate-500 uppercase tracking-wider mb-0.5">Success Rate</p>
                <p className="text-blue-400 font-bold font-mono text-sm">{s.action.successRate}%</p>
              </div>
            </div>

            {/* Apply mitigation button */}
            <button
              onClick={() => setMitigationApplied(x => !x)}
              className="w-full mt-4 py-2.5 rounded-xl text-sm font-bold tracking-wide transition-all duration-300 flex items-center justify-center gap-2"
              style={mitigationApplied ? {
                background: 'rgba(29,158,117,0.2)',
                border: '1px solid rgba(29,158,117,0.5)',
                color: '#1D9E75',
                boxShadow: '0 0 20px rgba(29,158,117,0.2)',
              } : {
                background: 'linear-gradient(135deg, #1D9E75, #15805e)',
                border: '1px solid rgba(29,158,117,0.5)',
                color: 'white',
                boxShadow: '0 4px 16px rgba(29,158,117,0.3)',
              }}
            >
              {mitigationApplied ? (
                <><Shield size={15} /> Mitigation Active — showing saved scenario</>
              ) : (
                <><Zap size={15} /> Apply Mitigation & See Impact</>
              )}
            </button>
          </div>
        </div>

        {/* ── Right column: Chart + Summary ── */}
        <div className="col-span-8 flex flex-col gap-4">

          {/* Chart card */}
          <div className="card p-5 flex-1">
            <div className="flex items-center justify-between mb-4">
              <div>
                <p className="text-slate-200 font-semibold text-sm">14-Day Revenue Projection</p>
                <p className="text-slate-500 text-xs mt-0.5 font-mono">
                  Anomaly detected at Day 3 &nbsp;·&nbsp; Impact diverges from Day 4
                </p>
              </div>
              <BarChart2 size={16} className="text-slate-500" />
            </div>

            <ResponsiveContainer width="100%" height={280}>
              <AreaChart data={s.data} margin={{ top: 10, right: 10, left: 10, bottom: 0 }}>
                <defs>
                  <linearGradient id="gradRed" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%"  stopColor="#E24B4A" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#E24B4A" stopOpacity={0.02} />
                  </linearGradient>
                  <linearGradient id="gradGreen" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%"  stopColor="#1D9E75" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#1D9E75" stopOpacity={0.02} />
                  </linearGradient>
                </defs>

                <CartesianGrid strokeDasharray="3 3" stroke="#1e2d45" vertical={false} />

                <XAxis
                  dataKey="name"
                  tick={{ fill: '#475569', fontSize: 11, fontFamily: 'monospace' }}
                  axisLine={{ stroke: '#1e2d45' }}
                  tickLine={false}
                />
                <YAxis
                  tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`}
                  tick={{ fill: '#475569', fontSize: 11, fontFamily: 'monospace' }}
                  axisLine={false}
                  tickLine={false}
                  width={52}
                />

                <Tooltip content={<CustomTooltip />} />

                <Legend
                  formatter={(value) =>
                    value === 'mitigated_sales'
                      ? <span style={{ color: '#1D9E75', fontSize: 12, fontFamily: 'monospace' }}>With GhostGrid</span>
                      : <span style={{ color: '#E24B4A', fontSize: 12, fontFamily: 'monospace' }}>Without GhostGrid</span>
                  }
                  iconType="circle"
                  iconSize={8}
                />

                {/* Anomaly onset marker */}
                <ReferenceLine x="D3" stroke="#EF9F27" strokeDasharray="4 4" strokeWidth={1.5}
                  label={{ value: 'Anomaly', fill: '#EF9F27', fontSize: 10, fontFamily: 'monospace', dy: -6 }} />

                <Area
                  type="monotone"
                  dataKey="unmitigated"
                  name="unmitigated_sales"
                  stroke="#E24B4A"
                  strokeWidth={2}
                  fill="url(#gradRed)"
                  dot={false}
                  activeDot={{ r: 5, fill: '#E24B4A', stroke: '#0a0f1a', strokeWidth: 2 }}
                />
                <Area
                  type="monotone"
                  dataKey="mitigated"
                  name="mitigated_sales"
                  stroke="#1D9E75"
                  strokeWidth={2.5}
                  fill="url(#gradGreen)"
                  dot={false}
                  activeDot={{ r: 5, fill: '#1D9E75', stroke: '#0a0f1a', strokeWidth: 2 }}
                  strokeDasharray={mitigationApplied ? '0' : '6 3'}
                  opacity={mitigationApplied ? 1 : 0.5}
                />
              </AreaChart>
            </ResponsiveContainer>

            {!mitigationApplied && (
              <p className="text-center text-[11px] text-slate-600 font-mono mt-2">
                ↑ Green line is dashed until you apply mitigation above
              </p>
            )}
          </div>

          {/* Summary stat cards */}
          <div className="grid grid-cols-3 gap-3 shrink-0">
            <div className="card p-4" style={{ border: '1px solid rgba(226,75,74,0.2)' }}>
              <div className="flex items-center gap-2 mb-2">
                <TrendingDown size={14} className="text-red-400" />
                <p className="text-[10px] text-slate-500 uppercase tracking-wider">Revenue Without GhostGrid</p>
              </div>
              <p className="text-red-400 font-bold font-mono text-xl">
                ${(totalUnmitigated / 1000).toFixed(0)}k
              </p>
              <p className="text-slate-600 text-[10px] font-mono mt-1">14-day total projection</p>
            </div>

            <div className="card p-4" style={{ border: '1px solid rgba(29,158,117,0.2)' }}>
              <div className="flex items-center gap-2 mb-2">
                <TrendingUp size={14} className="text-green-400" />
                <p className="text-[10px] text-slate-500 uppercase tracking-wider">Revenue With GhostGrid</p>
              </div>
              <p className="text-green-400 font-bold font-mono text-xl">
                ${(totalMitigated / 1000).toFixed(0)}k
              </p>
              <p className="text-slate-600 text-[10px] font-mono mt-1">14-day total projection</p>
            </div>

            <div className="card p-4" style={{ border: '1px solid rgba(55,138,221,0.2)' }}>
              <div className="flex items-center gap-2 mb-2">
                <DollarSign size={14} className="text-blue-400" />
                <p className="text-[10px] text-slate-500 uppercase tracking-wider">Total Recoverable</p>
              </div>
              <p className="text-blue-400 font-bold font-mono text-xl">
                ${((totalMitigated - totalUnmitigated) / 1000).toFixed(0)}k
              </p>
              <div className="flex items-center gap-1 mt-1">
                <div className="flex-1 h-1 rounded-full bg-[#1e2d45]">
                  <div className="h-1 rounded-full bg-blue-400 transition-all duration-500"
                    style={{ width: `${pctSaved}%` }} />
                </div>
                <span className="text-blue-400 text-[10px] font-mono font-bold">{pctSaved}%</span>
              </div>
            </div>
          </div>

          {/* CTA banner */}
          <div className="card p-4 shrink-0 flex items-center justify-between"
            style={{ background: 'linear-gradient(135deg, rgba(226,75,74,0.06), rgba(127,119,221,0.06))', border: '1px solid rgba(226,75,74,0.15)' }}>
            <div>
              <p className="text-white font-semibold text-sm">GhostGrid detected this anomaly {s.detected}</p>
              <p className="text-slate-500 text-xs mt-0.5">
                Act within <span className="text-amber-400 font-mono font-bold">{s.action.timeToAct}</span> to preserve {s.action.savings} in projected revenue
              </p>
            </div>
            <button className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-bold text-white transition-all"
              style={{ background: 'linear-gradient(135deg, #E24B4A, #7F77DD)', boxShadow: '0 4px 16px rgba(226,75,74,0.3)' }}>
              View Full Alert <ArrowRight size={14} />
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
