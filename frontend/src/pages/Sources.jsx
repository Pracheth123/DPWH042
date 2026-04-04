import { useMemo } from 'react'
import { Clock, TrendingUp, Wifi, WifiOff } from 'lucide-react'
import { useSources } from '../context/SourcesContext'
import { useAlerts } from '../context/AlertsContext'
import { getSourceIcon, relativeTime, formatDateTime } from '../lib/utils'
import { ResponsiveContainer, AreaChart, Area } from 'recharts'

const SOURCE_LIST = [
  { key: 'telegram',     name: 'Telegram',      icon: '✈' },
  { key: 'whatsapp',     name: 'WhatsApp',      icon: '💬' },
  { key: 'olx',          name: 'OLX',           icon: '🏷' },
  { key: 'news',         name: 'News',          icon: '📰' },
  { key: 'forum',        name: 'Forum',         icon: '💬' },
  { key: 'shipping',     name: 'Shipping',      icon: '🚢' },
  { key: 'rss',          name: 'RSS',           icon: '📡' },
  { key: 'commodity_api',name: 'Commodity API', icon: '📊' },
]

// Mini sparkline from alert counts (last 8 hours)
function Sparkline({ data }) {
  return (
    <ResponsiveContainer width="100%" height={36}>
      <AreaChart data={data} margin={{ top: 2, right: 0, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id="sparkGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#378ADD" stopOpacity={0.4} />
            <stop offset="95%" stopColor="#378ADD" stopOpacity={0} />
          </linearGradient>
        </defs>
        <Area type="monotone" dataKey="v" stroke="#378ADD" strokeWidth={1.5}
          fill="url(#sparkGrad)" dot={false} />
      </AreaChart>
    </ResponsiveContainer>
  )
}

export default function Sources() {
  const { sources } = useSources()
  const { alerts } = useAlerts()

  const sourcesWithStats = useMemo(() => {
    return SOURCE_LIST.map(s => {
      const src = sources.find(x => x.source === s.key)
      const related = alerts.filter(a => a.source === s.key)
      const lastSeen = src?.last_seen ?? (related[0]?.event_time || related[0]?.created_at)
      const age = lastSeen ? Date.now() - new Date(lastSeen).getTime() : Infinity
      const status = age < 3600000 ? 'online' : age < 86400000 ? 'stale' : 'offline'

      // Hourly activity (last 8h)
      const sparkData = Array.from({ length: 8 }, (_, i) => {
        const hourStart = Date.now() - (8 - i) * 3600000
        const hourEnd   = hourStart + 3600000
        const v = related.filter(a => {
          const t = new Date(a.event_time || a.created_at).getTime()
          return t >= hourStart && t < hourEnd
        }).length
        return { v }
      })

      return { ...s, status, lastSeen, count: related.length, sparkData }
    })
  }, [sources, alerts])

  const recentEvents = useMemo(() =>
    [...alerts]
      .sort((a, b) => new Date(b.event_time || b.created_at) - new Date(a.event_time || a.created_at))
      .slice(0, 20),
    [alerts]
  )

  const statusColor = (s) => s === 'online' ? '#1D9E75' : s === 'stale' ? '#EF9F27' : '#E24B4A'

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-white font-bold text-xl tracking-tight">Sources</h1>
        <p className="text-slate-500 text-sm mt-0.5">Monitor health across all data feeds</p>
      </div>

      {/* Source cards grid */}
      <div className="grid grid-cols-4 gap-4">
        {sourcesWithStats.map(s => (
          <div key={s.key} className="card p-4 flex flex-col gap-3 hover:border-white/10 transition-colors">
            {/* Header */}
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-2">
                <span className="text-xl">{s.icon}</span>
                <div>
                  <p className="text-white text-sm font-semibold">{s.name}</p>
                  <p className="text-slate-500 text-[10px] uppercase tracking-widest">{s.key}</p>
                </div>
              </div>
              <div className="flex items-center gap-1.5">
                <div className="w-2 h-2 rounded-full animate-pulse" style={{ backgroundColor: statusColor(s.status) }} />
                {s.status === 'online' ? (
                  <Wifi size={12} style={{ color: statusColor(s.status) }} />
                ) : (
                  <WifiOff size={12} style={{ color: statusColor(s.status) }} />
                )}
              </div>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-2 gap-2">
              <div>
                <p className="text-slate-500 text-[10px] uppercase tracking-widest">Signals</p>
                <p className="text-white font-bold font-mono text-lg">{s.count}</p>
              </div>
              <div>
                <p className="text-slate-500 text-[10px] uppercase tracking-widest">Last Seen</p>
                <p className="text-slate-300 text-xs">{relativeTime(s.lastSeen)}</p>
              </div>
            </div>

            {/* Sparkline */}
            <div>
              <p className="text-slate-600 text-[10px] mb-1">8h activity</p>
              <Sparkline data={s.sparkData} />
            </div>
          </div>
        ))}
      </div>

      {/* Ingest log */}
      <div className="card overflow-hidden">
        <div className="px-5 py-4 border-b border-[#1e2d45] flex items-center gap-2">
          <Clock size={14} className="text-slate-400" />
          <p className="text-slate-300 font-semibold text-sm">Recent Ingest Events</p>
          <span className="text-slate-600 text-xs">last 20</span>
        </div>
        <div className="divide-y divide-[#1e2d45]">
          {recentEvents.map((a, i) => (
            <div key={a.id || i} className="flex items-center gap-4 px-5 py-2.5 hover:bg-white/[0.02] transition-colors">
              <span className="text-slate-600 text-xs font-mono w-36 shrink-0">
                {formatDateTime(a.event_time || a.created_at)}
              </span>
              <span className="text-slate-400 text-sm shrink-0">{getSourceIcon(a.source)} {a.source}</span>
              <span className="text-slate-300 text-xs font-mono flex-1 truncate">
                {a.normalized_text || a.raw_text || '—'}
              </span>
              <span className="text-slate-500 text-xs shrink-0">{a.severity}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
