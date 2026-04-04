import { useEffect, useRef, useState } from 'react'
import { Activity, AlertTriangle, Database, Radio } from 'lucide-react'
import { useAlerts } from '../context/AlertsContext'
import { useSources } from '../context/SourcesContext'
import { useUI } from '../context/UIContext'
import MetricCard from '../components/MetricCard'
import MapView from '../components/MapView'
import { SignalBadge } from '../components/SignalBadge'
import { getSignalConfig, getSeverityConfig, formatTime, truncate, confidenceColor, getAlertText } from '../lib/utils'

// ── Crisis Index ──────────────────────────────────────────────────────────────
function CrisisIndex({ alerts }) {
  const high = alerts.filter(a => a.severity === 'high').length
  const med  = alerts.filter(a => a.severity === 'medium').length
  const idx  = Math.min(10, Math.round((high * 1.5 + med * 0.5) / Math.max(1, alerts.length) * 10))
  const color = idx >= 7 ? '#E24B4A' : idx >= 4 ? '#EF9F27' : '#00FF41'

  return (
    <div className="card flex flex-col items-center justify-center text-center relative overflow-hidden" style={{ height: 140 }}>
      <p style={{ fontFamily: 'Fira Code, monospace', fontSize: 9, color: '#444', letterSpacing: '0.12em', marginBottom: 4 }}>CRISIS INDEX</p>
      <p style={{ fontFamily: 'Fira Code, monospace', fontSize: 56, fontWeight: 700, color, lineHeight: 1 }}>
        {idx}
      </p>
      <p style={{ fontFamily: 'Fira Code, monospace', fontSize: 9, color: '#444', marginTop: 2 }}>/ 10</p>
      <div style={{ display: 'flex', gap: 2, marginTop: 8 }}>
        {Array.from({ length: 10 }, (_, i) => (
          <div key={i} style={{ width: 5, height: 10, background: i < idx ? color : '#1a1a1a', border: `1px solid ${i < idx ? color : '#222'}` }} />
        ))}
      </div>
    </div>
  )
}

// ── SVG WorldMap removed — replaced by react-leaflet MapView component ────────
// See src/components/MapView.jsx

// ── Live Terminal Feed ────────────────────────────────────────────────────────
function LiveTerminalFeed({ alerts }) {
  const [paused, setPaused] = useState(false)
  const [snapshot, setSnapshot] = useState(null)
  const containerRef = useRef(null)
  const rows = [...alerts].sort((a, b) =>
    new Date(b.event_time || b.created_at) - new Date(a.event_time || a.created_at)
  ).slice(0, 50)
  const displayRows = snapshot ?? rows

  return (
    <div className="card flex flex-col h-full overflow-hidden">
      <div className="flex items-center justify-between px-4 py-3 border-b border-[#1e2d45]">
        <div className="flex items-center gap-2">
          <span className={`w-2 h-2 rounded-full ${displayRows.length > 0 ? 'bg-green-400 animate-pulse' : 'bg-slate-600'}`} />
          <p className="text-slate-300 text-xs font-mono uppercase tracking-widest">Live Feed</p>
        </div>
        <button
          onClick={() => {
            if (!paused) { setSnapshot([...rows]); setPaused(true) }
            else { setSnapshot(null); setPaused(false) }
          }}
          className="text-slate-500 hover:text-slate-300 text-xs font-mono transition-colors"
          disabled={displayRows.length === 0}
        >
          {paused ? '▶ RESUME' : '⏸ PAUSE'}
        </button>
      </div>

      <div
        ref={containerRef}
        onMouseEnter={() => { if (rows.length > 0) { setSnapshot([...rows]); setPaused(true) } }}
        onMouseLeave={() => { setSnapshot(null); setPaused(false) }}
        className="flex-1 overflow-y-auto px-0 flex flex-col"
      >
        {displayRows.length === 0 ? (
          <div className="flex flex-col items-center justify-center flex-1 gap-3 py-8">
            <div style={{
              width: 44, height: 44, borderRadius: '50%',
              background: 'rgba(100,116,139,0.08)',
              border: '1px solid rgba(100,116,139,0.15)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#475569" strokeWidth="1.5">
                <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
              </svg>
            </div>
            <p className="text-slate-600 text-xs font-mono text-center">No signals yet</p>
            <p className="text-slate-700 text-[10px] font-mono text-center">Feed will populate on next sync</p>
          </div>
        ) : (
          displayRows.map((alert, i) => {
            const sc = getSignalConfig(alert.signal_type)
            const conf = alert.confidence ?? 0
            const confColor = confidenceColor(conf)
            return (
              <div
                key={alert.id || i}
                className="flex items-start gap-2 px-4 py-2 border-b border-white/5 hover:bg-white/5 cursor-default transition-colors animate-slide-in-top"
                style={{ animationDelay: `${i * 20}ms` }}
              >
                <span className="text-slate-600 text-[10px] font-mono shrink-0 mt-0.5 w-14">
                  {formatTime(alert.event_time || alert.created_at)}
                </span>
                <span className={`shrink-0 text-[9px] font-bold font-mono px-1.5 py-0.5 rounded ${sc.bg} ${sc.text} border ${sc.border}`}>
                  {sc.label.toUpperCase()}
                </span>
                <span className="text-slate-300 text-[11px] font-mono flex-1 truncate">
                  {truncate(getAlertText(alert), 55)}
                </span>
                <span className="text-[10px] font-mono font-bold shrink-0" style={{ color: confColor }}>
                  {Math.round(conf * 100)}%
                </span>
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}

// ── Command Center Page ───────────────────────────────────────────────────────
export default function CommandCenter() {
  const { alerts } = useAlerts()
  const { sources, onlineCount } = useSources()
  const { openDrawer } = useUI()

  const highCount = alerts.filter(a => a.severity === 'high').length

  return (
    <div className="h-full flex flex-col p-3 gap-3 min-h-0">
      {/* Top bar */}
      <div className="flex items-center justify-between shrink-0">
        <div>
          <h1 style={{ fontFamily: 'Fira Code, monospace', fontSize: 13, fontWeight: 700, color: '#d8d8d8', letterSpacing: '0.08em' }}>COMMAND CENTER</h1>
          <p style={{ fontFamily: 'Fira Code, monospace', fontSize: 9, color: '#444', marginTop: 2 }}>REAL-TIME SUPPLY CHAIN CRISIS MONITOR</p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontFamily: 'Fira Code, monospace', fontSize: 9, color: '#00FF41' }}>
          <span style={{ width: 5, height: 5, background: '#00FF41', animation: 'termBlink 1.4s step-end infinite' }} />
          LIVE
        </div>
      </div>

      {/* Metric cards */}
      <div className="grid grid-cols-3 gap-2 shrink-0">
        <MetricCard icon={Radio}         label="Total Signals"  value={alerts.length}  color="#378ADD" subtitle="past 72h" />
        <MetricCard icon={AlertTriangle} label="High Alerts"    value={highCount}       color="#E24B4A" subtitle="active" />
        <MetricCard icon={Database}      label="Sources Online" value={onlineCount}     color="#1D9E75" subtitle={`/ ${sources.length} total`} />
      </div>

      {/* Main 3-zone grid */}
      <div className="flex-1 grid grid-cols-12 gap-4 min-h-0 overflow-hidden">
        {/* Left zone */}
        <div className="col-span-3 flex flex-col gap-4 min-h-0">
          <CrisisIndex alerts={alerts} />
          <div className="flex-1 card p-4 min-h-0 overflow-hidden flex flex-col">
            <p className="text-slate-400 text-xs uppercase tracking-widest mb-3">Recent Alerts</p>
            {alerts.length === 0 ? (
              <div className="flex flex-col items-center justify-center flex-1 gap-2">
                <div style={{
                  width: 40, height: 40, borderRadius: '50%',
                  background: 'rgba(226,75,74,0.06)',
                  border: '1px solid rgba(226,75,74,0.15)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                }}>
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#7f1d1d" strokeWidth="1.5">
                    <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
                    <line x1="12" y1="9" x2="12" y2="13"/>
                    <line x1="12" y1="17" x2="12.01" y2="17"/>
                  </svg>
                </div>
                <p className="text-slate-600 text-[11px] font-mono text-center">No alerts</p>
                <p className="text-slate-700 text-[10px] font-mono text-center">System nominal</p>
              </div>
            ) : (
              <div className="space-y-2 overflow-y-auto flex-1 pr-1">
                {alerts.slice(0, 8).map((a, i) => {
                  const sev = getSeverityConfig(a.severity)
                  return (
                    <button key={a.id || i} onClick={() => openDrawer(a)}
                      className="w-full text-left flex items-start gap-2 p-2 rounded-lg hover:bg-white/5 transition-colors">
                      <span className="w-1.5 h-1.5 rounded-full mt-1.5 shrink-0" style={{ backgroundColor: sev.color }} />
                      <div className="min-w-0">
                        <p className="text-slate-300 text-xs font-mono truncate">
                          {truncate(getAlertText(a), 45)}
                        </p>
                        <p className="text-slate-600 text-[10px] mt-0.5">{a.commodity} · {a.source}</p>
                      </div>
                    </button>
                  )
                })}
              </div>
            )}
          </div>
        </div>

        {/* Center zone — Leaflet MapView */}
        <div className="col-span-6 min-h-0">
          <MapView />
        </div>

        {/* Right zone — Live terminal */}
        <div className="col-span-3 min-h-0">
          <LiveTerminalFeed alerts={alerts} />
        </div>
      </div>
    </div>
  )
}
