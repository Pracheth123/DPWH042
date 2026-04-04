import { useState, useMemo } from 'react'
import { ChevronDown, ChevronUp, Search, Filter } from 'lucide-react'
import { useAlerts } from '../context/AlertsContext'
import { useUI } from '../context/UIContext'
import { SignalBadge, SeverityBadge } from '../components/SignalBadge'
import ConfidenceBar from '../components/ConfidenceBar'
import { formatDateTime, relativeTime, getSourceIcon, truncate, SIGNAL_CONFIG, getAlertText } from '../lib/utils'

const PAGE_SIZE = 25
const SIGNAL_TYPES = ['all', ...Object.keys(SIGNAL_CONFIG).slice(0, 4)]
const SEVERITIES = ['all', 'high', 'medium', 'low']

export default function SignalsFeed() {
  const { alerts, loading } = useAlerts()
  const { openDrawer } = useUI()

  const [typeFilter, setTypeFilter] = useState('all')
  const [sevFilter,  setSevFilter]  = useState('all')
  const [search, setSearch] = useState('')
  const [commodity, setCommodity] = useState('all')
  const [page, setPage] = useState(1)
  const [expandedId, setExpandedId] = useState(null)

  const commodities = useMemo(() => {
    const set = new Set(alerts.map(a => a.commodity).filter(Boolean))
    return ['all', ...Array.from(set).sort()]
  }, [alerts])

  const filtered = useMemo(() => {
    return alerts.filter(a => {
      if (typeFilter !== 'all' && a.signal_type !== typeFilter) return false
      if (sevFilter  !== 'all' && a.severity !== sevFilter)    return false
      if (commodity  !== 'all' && a.commodity !== commodity)   return false
      if (search) {
        const q = search.toLowerCase()
        const haystack = [a.normalized_text, a.raw_text, a.commodity, a.source, a.location].join(' ').toLowerCase()
        if (!haystack.includes(q)) return false
      }
      return true
    })
  }, [alerts, typeFilter, sevFilter, commodity, search])

  const totalPages = Math.ceil(filtered.length / PAGE_SIZE)
  const rows = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-white font-bold text-xl tracking-tight">Signals Feed</h1>
        <p className="text-slate-500 text-sm mt-0.5">{filtered.length} signals matching filters</p>
      </div>

      {/* Filter bar */}
      <div className="card p-4 flex flex-wrap gap-4 items-center">
        {/* Signal type pills */}
        <div className="flex gap-1.5 flex-wrap">
          {SIGNAL_TYPES.map(t => (
            <button
              key={t}
              onClick={() => { setTypeFilter(t); setPage(1) }}
              className={`px-3 py-1 rounded-full text-xs font-bold transition-all ${
                typeFilter === t
                  ? 'bg-red-500/20 text-red-400 border border-red-500/40'
                  : 'bg-white/5 text-slate-400 border border-white/10 hover:border-white/20'
              }`}
            >
              {t === 'all' ? 'ALL' : t.replace('_', ' ').toUpperCase()}
            </button>
          ))}
        </div>

        <div className="flex gap-3 flex-wrap flex-1">
          {/* Severity */}
          <select value={sevFilter} onChange={e => { setSevFilter(e.target.value); setPage(1) }}
            className="bg-[#1a2235] border border-[#1e2d45] text-slate-300 text-xs rounded-lg px-3 py-1.5 outline-none focus:border-blue-500/50">
            {SEVERITIES.map(s => <option key={s} value={s}>{s.toUpperCase()}</option>)}
          </select>

          {/* Commodity */}
          <select value={commodity} onChange={e => { setCommodity(e.target.value); setPage(1) }}
            className="bg-[#1a2235] border border-[#1e2d45] text-slate-300 text-xs rounded-lg px-3 py-1.5 outline-none focus:border-blue-500/50">
            {commodities.map(c => <option key={c} value={c}>{c.toUpperCase()}</option>)}
          </select>

          {/* Search */}
          <div className="relative flex-1 min-w-48">
            <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
            <input
              value={search}
              onChange={e => { setSearch(e.target.value); setPage(1) }}
              placeholder="Search signals…"
              className="w-full bg-[#1a2235] border border-[#1e2d45] text-slate-300 text-xs rounded-lg pl-8 pr-3 py-1.5 outline-none focus:border-blue-500/50 placeholder-slate-600"
            />
          </div>
        </div>
      </div>

      {/* Table */}
      <div className="card overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-[#1e2d45]">
              {['Time', 'Source', 'Commodity', 'Type', 'Signal Text', 'Confidence', 'Severity', ''].map(h => (
                <th key={h} className="text-left text-slate-500 text-xs uppercase tracking-widest px-4 py-3 font-medium">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading && !alerts.length ? (
              <tr><td colSpan={8} className="text-center py-12 text-slate-600">Loading signals…</td></tr>
            ) : rows.length === 0 ? (
              <tr><td colSpan={8} className="text-center py-12 text-slate-600">No signals match filters.</td></tr>
            ) : rows.map(alert => (
              <>
                <tr key={alert.id}
                  className="border-b border-[#1e2d45]/50 hover:bg-white/[0.02] transition-colors">
                  <td className="px-4 py-3 text-slate-500 text-xs font-mono whitespace-nowrap">
                    {formatDateTime(alert.event_time || alert.created_at)}
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-slate-300 text-sm">{getSourceIcon(alert.source)} {alert.source}</span>
                  </td>
                  <td className="px-4 py-3">
                    {alert.commodity ? (
                      <span className="px-2 py-0.5 bg-slate-700/50 text-slate-300 text-xs rounded border border-slate-600/30">
                        {alert.commodity}
                      </span>
                    ) : <span className="text-slate-600">—</span>}
                  </td>
                  <td className="px-4 py-3"><SignalBadge type={alert.signal_type} /></td>
                  <td className="px-4 py-3 max-w-xs">
                    <p className="text-slate-300 text-xs font-mono truncate">
                      {truncate(getAlertText(alert), 65)}
                    </p>
                  </td>
                  <td className="px-4 py-3 w-28">
                    <ConfidenceBar value={alert.confidence ?? 0} showLabel height={5} />
                  </td>
                  <td className="px-4 py-3"><SeverityBadge severity={alert.severity} /></td>
                  <td className="px-4 py-3">
                    <button
                      onClick={() => setExpandedId(expandedId === alert.id ? null : alert.id)}
                      className="text-slate-500 hover:text-slate-300 transition-colors"
                    >
                      {expandedId === alert.id ? <ChevronUp size={15} /> : <ChevronDown size={15} />}
                    </button>
                  </td>
                </tr>

                {expandedId === alert.id && (
                  <tr key={`${alert.id}-exp`} className="border-b border-[#1e2d45]">
                    <td colSpan={8} className="px-4 py-4 bg-[#111827]">
                      <div className="grid grid-cols-2 gap-6">
                        <div>
                          <p className="text-slate-500 text-xs uppercase tracking-widest mb-2">Full Signal Text</p>
                          <p className="text-slate-200 text-xs font-mono leading-relaxed whitespace-pre-wrap">
                            {getAlertText(alert)}
                          </p>
                        </div>
                        <div className="space-y-3">
                          {[
                            ['Location', alert.location || '—'],
                            ['Event Time', formatDateTime(alert.event_time)],
                            ['Language', alert.language || '—'],
                            ['Category', alert.category || '—'],
                            ['ID', alert.id],
                          ].map(([l, v]) => (
                            <div key={l}>
                              <p className="text-slate-500 text-[10px] uppercase tracking-widest">{l}</p>
                              <p className="text-slate-300 text-xs font-mono">{v}</p>
                            </div>
                          ))}
                          <button
                            onClick={() => openDrawer(alert)}
                            className="mt-2 px-3 py-1.5 bg-red-500/15 text-red-400 border border-red-500/30 rounded-lg text-xs font-medium hover:bg-red-500/25 transition-colors"
                          >
                            Open Full Detail →
                          </button>
                        </div>
                      </div>
                    </td>
                  </tr>
                )}
              </>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-slate-500 text-sm">
            Page {page} of {totalPages} · {filtered.length} total
          </p>
          <div className="flex gap-2">
            <button
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page === 1}
              className="px-4 py-1.5 bg-[#1a2235] border border-[#1e2d45] text-slate-300 text-sm rounded-lg disabled:opacity-40 hover:border-white/20 transition-colors"
            >← Prev</button>
            <button
              onClick={() => setPage(p => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
              className="px-4 py-1.5 bg-[#1a2235] border border-[#1e2d45] text-slate-300 text-sm rounded-lg disabled:opacity-40 hover:border-white/20 transition-colors"
            >Next →</button>
          </div>
        </div>
      )}
    </div>
  )
}
