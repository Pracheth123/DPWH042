import { useEffect, useRef, useState } from 'react'
import { Activity, AlertTriangle, Database, Radio } from 'lucide-react'
import { useAlerts } from '../context/AlertsContext'
import { useSources } from '../context/SourcesContext'
import { useUI } from '../context/UIContext'
import MetricCard from '../components/MetricCard'
import { SignalBadge } from '../components/SignalBadge'
import { getSignalConfig, getSeverityConfig, formatTime, truncate, confidenceColor, getAlertText } from '../lib/utils'

// ── Crisis Index ──────────────────────────────────────────────────────────────
function CrisisIndex({ alerts }) {
  const high = alerts.filter(a => a.severity === 'high').length
  const med  = alerts.filter(a => a.severity === 'medium').length
  const idx  = Math.min(10, Math.round((high * 1.5 + med * 0.5) / Math.max(1, alerts.length) * 10))
  const color = idx >= 7 ? '#E24B4A' : idx >= 4 ? '#EF9F27' : '#1D9E75'
  const gradientBg = color.startsWith('#') ? `radial-gradient(circle at 50% 50%, ${color}66, transparent 70%)` : 'none'

  return (
    <div className="card p-6 flex flex-col items-center justify-center text-center h-48 relative overflow-hidden">
      <div className="absolute inset-0 opacity-20"
        style={{ background: gradientBg }} />
      <p className="text-slate-400 text-xs uppercase tracking-widest mb-2">Crisis Index</p>
      <p className="font-bold font-mono text-7xl" style={{ color, textShadow: `0 0 40px ${color}80` }}>
        {idx}
      </p>
      <p className="text-slate-500 text-xs mt-2">/ 10</p>
      <div className="mt-3 flex gap-1">
        {Array.from({ length: 10 }, (_, i) => (
          <div key={i} className="w-1.5 h-3 rounded-sm"
            style={{ backgroundColor: i < idx ? color : 'rgba(255,255,255,0.08)' }} />
        ))}
      </div>
    </div>
  )
}

// ── SVG World Map ─────────────────────────────────────────────────────────────
const LOCATION_COORDS = {
  'mumbai':     [72.8777, 19.0760, 1250.0, 370.0],
  'delhi':      [77.2090, 28.6139, 1225.0, 295.0],
  'hyderabad':  [78.4867, 17.3850, 1240.0, 370.0],
  'karachi':    [67.0099, 24.8607, 1180.0, 330.0],
  'dhaka':      [90.4125, 23.8103, 1310.0, 330.0],
  'nairobi':    [36.8219, -1.2921,  990.0, 430.0],
  'dubai':      [55.2708, 25.2048, 1080.0, 330.0],
  'singapore':  [103.819, 1.3521,  1355.0, 420.0],
  'london':     [-0.1276, 51.5074,  830.0, 210.0],
  'new york':   [-74.006, 40.7128,  550.0, 240.0],
  'shanghai':   [121.474, 31.2304, 1370.0, 270.0],
  'cairo':      [31.2357, 30.0444, 1000.0, 305.0],
  'lahore':     [74.3587, 31.5204, 1195.0, 300.0],
  'islamabad':  [73.0479, 33.6844, 1185.0, 285.0],
  'kolkata':    [88.3639, 22.5726, 1295.0, 345.0],
  'chennai':    [80.2707, 13.0827, 1255.0, 390.0],
  'bangkok':    [100.523, 13.7563, 1330.0, 380.0],
  'jakarta':    [106.845, -6.2088, 1340.0, 430.0],
  'tokyo':      [139.691, 35.6762, 1430.0, 270.0],
  'beijing':    [116.407, 39.9042, 1380.0, 255.0],
  'moscow':     [37.6173, 55.7558, 1060.0, 185.0],
  'istanbul':   [28.9784, 41.0082,  990.0, 235.0],
  'lagos':      [3.3792,   6.5244,  870.0, 430.0],
  'paris':      [2.3522,  48.8566,  840.0, 205.0],
  'global':     [0,       0,        800.0, 450.0],
}

function getCoords(location) {
  if (!location) return null
  const key = location.toLowerCase().trim()
  if (key === 'unknown') return null
  if (key === 'global') return [0, 0, 800.0, 450.0]
  return LOCATION_COORDS[key] || null
}

function WorldMap({ alerts, onNodeClick }) {
  const [tooltip, setTooltip] = useState(null)

  const nodes = alerts.slice(0, 30).reduce((acc, a) => {
    const coords = getCoords(a.location)
    if (!coords) return acc
    const key = (a.location || '').toLowerCase().trim()
    const existing = acc.find(n => n.locationKey === key)
    if (existing) { existing.alerts.push(a) }
    else { acc.push({ location: a.location, locationKey: key, x: coords[2], y: coords[3], alerts: [a] }) }
    return acc
  }, [])

  return (
    <div className="card p-4 h-full relative overflow-hidden">
      <p className="text-slate-400 text-xs uppercase tracking-widest mb-3">Global Signal Map</p>
      <svg viewBox="0 0 1600 900" className="w-full h-full" style={{ filter: 'drop-shadow(0 0 20px rgba(55,138,221,0.15))' }}>
        {/* Ocean background */}
        <rect width="1600" height="900" fill="#0d1929" />

        {/* Continent outlines */}
        <path d="M180,120 L320,100 L420,130 L440,200 L400,280 L350,320 L280,340 L220,300 L180,240 L160,180 Z" fill="#1a2a3a" stroke="#1e3a5a" strokeWidth="1"/>
        <path d="M280,340 L360,330 L400,380 L410,460 L380,560 L340,620 L290,580 L260,500 L250,420 Z" fill="#1a2a3a" stroke="#1e3a5a" strokeWidth="1"/>
        <path d="M740,100 L880,90 L920,130 L900,180 L840,200 L800,180 L760,190 L740,160 Z" fill="#1a2a3a" stroke="#1e3a5a" strokeWidth="1"/>
        <path d="M820,220 L980,210 L1020,280 L1010,400 L980,500 L940,560 L880,540 L840,460 L820,360 L800,280 Z" fill="#1a2a3a" stroke="#1e3a5a" strokeWidth="1"/>
        <path d="M900,80 L1200,70 L1420,100 L1460,180 L1400,260 L1300,280 L1200,260 L1100,280 L1000,260 L920,200 L880,140 Z" fill="#1a2a3a" stroke="#1e3a5a" strokeWidth="1"/>
        <path d="M1280,480 L1440,460 L1500,520 L1480,580 L1400,600 L1300,580 L1260,530 Z" fill="#1a2a3a" stroke="#1e3a5a" strokeWidth="1"/>

        <rect width="1600" height="900" fill="transparent" />
        {[180, 360, 540, 720, 900, 1080, 1260, 1440].map(x => (
          <line key={x} x1={x} y1={0} x2={x} y2={900} stroke="#1e2d45" strokeWidth="0.5" />
        ))}
        {[150, 300, 450, 600, 750].map(y => (
          <line key={y} x1={0} y1={y} x2={1600} y2={y} stroke="#1e2d45" strokeWidth="0.5" />
        ))}
        <line x1="0" y1="450" x2="1600" y2="450" stroke="#1e2d45" strokeWidth="1" strokeDasharray="8,8" />

        {/* Alert nodes */}
        {nodes.map((node) => {
          const topAlert = node.alerts.sort((a, b) =>
            ['high','medium','low'].indexOf(a.severity) - ['high','medium','low'].indexOf(b.severity)
          )[0]
          const sev = getSeverityConfig(topAlert.severity)

          return (
            <g key={node.location}
              className="cursor-pointer"
              onClick={() => onNodeClick(topAlert)}
              onMouseEnter={() => setTooltip({ ...node, topAlert, x: node.x, y: node.y })}
              onMouseLeave={() => setTooltip(null)}
            >
              <circle cx={node.x} cy={node.y} r={18} fill={sev.color} opacity="0.08" />
              <circle cx={node.x} cy={node.y} r={10} fill={sev.color} opacity="0.18">
                <animate attributeName="r" values="10;16;10" dur="2s" repeatCount="indefinite" />
                <animate attributeName="opacity" values="0.18;0.05;0.18" dur="2s" repeatCount="indefinite" />
              </circle>
              <circle cx={node.x} cy={node.y} r={5} fill={sev.color} />
              {node.alerts.length > 1 && (
                <text x={node.x + 7} y={node.y - 7} fill="white" fontSize="10" fontWeight="bold">
                  {node.alerts.length}
                </text>
              )}
            </g>
          )
        })}

        {/* Tooltip */}
        {tooltip && (() => {
          const ttX = tooltip.x > 1400 ? tooltip.x - 150 : tooltip.x + 12
          const ttY = tooltip.y > 820  ? tooltip.y - 60  : tooltip.y - 28
          return (
            <g>
              <rect x={ttX} y={ttY} width={130} height={44} rx="6"
                fill="#1a2235" stroke="#1e2d45" strokeWidth="1" />
              <text x={ttX + 8} y={ttY + 16} fill="white" fontSize="11" fontWeight="bold">
                {tooltip.location}
              </text>
              <text x={ttX + 8} y={ttY + 32} fill="#64748b" fontSize="10">
                {tooltip.alerts.length} signal(s)
              </text>
            </g>
          )
        })()}
      </svg>

      {/* Empty-state overlay rendered in HTML over the SVG */}
      {nodes.length === 0 && (
        <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none" style={{ top: '2rem' }}>
          <div style={{
            width: 56, height: 56, borderRadius: '50%',
            background: 'rgba(55,138,221,0.08)',
            border: '1px solid rgba(55,138,221,0.18)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            marginBottom: 12,
          }}>
            <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#378ADD" strokeWidth="1.5">
              <circle cx="12" cy="12" r="10"/>
              <line x1="2" y1="12" x2="22" y2="12"/>
              <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>
            </svg>
          </div>
          <p style={{ color: '#94a3b8', fontSize: 13, fontWeight: 600, letterSpacing: '0.05em', marginBottom: 4 }}>
            No Active Signals
          </p>
          <p style={{ color: '#334155', fontSize: 11, fontFamily: 'monospace' }}>
            Awaiting data from monitored regions…
          </p>
        </div>
      )}
    </div>
  )
}

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
    <div className="h-full flex flex-col p-6 gap-6 min-h-0">
      {/* Top bar */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-white font-bold text-xl tracking-tight">Command Center</h1>
          <p className="text-slate-500 text-sm mt-0.5">Real-time supply chain crisis monitoring</p>
        </div>
        <div className="flex items-center gap-2 text-xs text-slate-500 font-mono">
          <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
          <span>LIVE</span>
        </div>
      </div>

      {/* Metric cards */}
      <div className="grid grid-cols-3 gap-4 shrink-0">
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

        {/* Center zone — World map */}
        <div className="col-span-6 min-h-0">
          <WorldMap alerts={alerts} onNodeClick={openDrawer} />
        </div>

        {/* Right zone — Live terminal */}
        <div className="col-span-3 min-h-0">
          <LiveTerminalFeed alerts={alerts} />
        </div>
      </div>
    </div>
  )
}
