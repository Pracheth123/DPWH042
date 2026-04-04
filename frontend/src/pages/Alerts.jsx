import { useMemo, useState } from 'react'
import { AlertTriangle, TrendingUp, Gauge } from 'lucide-react'
import { useAlerts } from '../context/AlertsContext'
import { useUI } from '../context/UIContext'
import MetricCard from '../components/MetricCard'
import { SignalBadge, SeverityBadge } from '../components/SignalBadge'
import ConfidenceGauge from '../components/ConfidenceGauge'
import { getSeverityConfig, relativeTime, truncate, getSourceIcon, getAlertText } from '../lib/utils'

// ── 24h Timeline ──────────────────────────────────────────────────────────────
function Timeline({ alerts }) {
  const [tooltip, setTooltip] = useState(null)
  const now = Date.now()
  const MS_24H = 86_400_000

  const blocks = alerts.filter(a => {
    const t = new Date(a.event_time || a.created_at).getTime()
    return now - t < MS_24H
  }).map(a => {
    const t = new Date(a.event_time || a.created_at).getTime()
    const pct = ((MS_24H - (now - t)) / MS_24H) * 100
    return { ...a, pct }
  })

  const sev = getSeverityConfig

  return (
    <div className="card p-5">
      <p className="text-slate-400 text-xs uppercase tracking-widest mb-4">24-Hour Timeline</p>
      <div className="relative h-16 bg-[#0a0f1a] rounded-lg overflow-hidden border border-[#1e2d45]">
        {/* Hour grid */}
        {Array.from({ length: 24 }, (_, i) => (
          <div key={i} className="absolute top-0 bottom-0 border-l border-[#1e2d45]/50"
            style={{ left: `${(i / 24) * 100}%` }}>
            <span className="absolute bottom-1 left-1 text-slate-700 text-[9px]">{i}h</span>
          </div>
        ))}

        {/* Alert blocks */}
        {blocks.map((alert, i) => {
          const c = sev(alert.severity)
          return (
            <div
              key={alert.id || i}
              className="absolute top-2 bottom-2 w-1.5 rounded-full cursor-pointer hover:w-3 transition-all"
              style={{
                left: `${alert.pct}%`,
                backgroundColor: c.color,
                boxShadow: `0 0 6px ${c.color}80`,
              }}
              onMouseEnter={() => setTooltip({ alert, left: alert.pct })}
              onMouseLeave={() => setTooltip(null)}
            />
          )
        })}

        {/* Tooltip */}
        {tooltip && (
          <div
            className="absolute bottom-full mb-2 bg-[#1a2235] border border-[#1e2d45] rounded-lg px-3 py-2 text-xs z-10 pointer-events-none min-w-40"
            style={{ left: `${Math.min(tooltip.left, 80)}%` }}
          >
            <p className="text-white font-mono mb-1">{truncate(getAlertText(tooltip.alert), 50)}</p>
            <p className="text-slate-400">{tooltip.alert.commodity} · {tooltip.alert.severity}</p>
          </div>
        )}
      </div>
    </div>
  )
}

// ── Alerts Page ───────────────────────────────────────────────────────────────
export default function Alerts() {
  const { alerts, loading } = useAlerts()
  const { openDrawer } = useUI()

  const high   = alerts.filter(a => a.severity === 'high')
  const medium = alerts.filter(a => a.severity === 'medium')
  const avgConf = alerts.length
    ? (alerts.reduce((s, a) => s + (a.confidence ?? 0), 0) / alerts.length)
    : 0

  const ranked = useMemo(() =>
    [...alerts].sort((a, b) => (b.confidence ?? 0) - (a.confidence ?? 0)).slice(0, 30),
    [alerts]
  )

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-white font-bold text-xl tracking-tight">Alerts</h1>
        <p className="text-slate-500 text-sm mt-0.5">{alerts.length} total · {high.length} critical</p>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-3 gap-4">
        <MetricCard icon={AlertTriangle} label="High Severity"     value={high.length}              color="#E24B4A" />
        <MetricCard icon={TrendingUp}    label="Medium Severity"   value={medium.length}            color="#EF9F27" />
        <MetricCard icon={Gauge}         label="Avg Confidence"    value={`${Math.round(avgConf * 100)}%`} color="#7F77DD" />
      </div>

      {/* Timeline */}
      <Timeline alerts={alerts} />

      {/* Ranked list */}
      <div className="card overflow-hidden">
        <div className="px-5 py-4 border-b border-[#1e2d45]">
          <p className="text-slate-300 font-semibold text-sm">Ranked by Confidence</p>
        </div>
        <div className="divide-y divide-[#1e2d45]">
          {loading && !ranked.length ? (
            <p className="text-center py-8 text-slate-600">Loading…</p>
          ) : ranked.map((alert, i) => (
            <div key={alert.id || i}
              className="flex items-center gap-4 px-5 py-4 hover:bg-white/[0.02] transition-colors cursor-pointer"
              onClick={() => openDrawer(alert)}
            >
              {/* Rank */}
              <span className="text-slate-600 font-mono text-xs w-6 shrink-0">#{i + 1}</span>

              {/* Gauge */}
              <ConfidenceGauge value={alert.confidence ?? 0} size={52} />

              {/* Info */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <SeverityBadge severity={alert.severity} />
                  <SignalBadge type={alert.signal_type} />
                  {alert.commodity && (
                    <span className="text-slate-500 text-xs">{alert.commodity}</span>
                  )}
                </div>
                <p className="text-slate-300 text-xs font-mono truncate">
                  {truncate(getAlertText(alert), 80)}
                </p>
              </div>

              {/* Source + time */}
              <div className="text-right shrink-0">
                <p className="text-slate-400 text-xs">{getSourceIcon(alert.source)} {alert.source}</p>
                <p className="text-slate-600 text-[10px] mt-0.5">{relativeTime(alert.event_time || alert.created_at)}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
