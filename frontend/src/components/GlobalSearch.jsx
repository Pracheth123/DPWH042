import { useState, useEffect, useRef } from 'react'
import { Search, X } from 'lucide-react'
import { useAlerts } from '../context/AlertsContext'
import { useUI } from '../context/UIContext'
import { getSignalConfig, truncate, relativeTime } from '../lib/utils'

export default function GlobalSearch({ onClose }) {
  const { alerts } = useAlerts()
  const { openDrawer } = useUI()
  const [query, setQuery] = useState('')
  const inputRef = useRef(null)

  useEffect(() => { inputRef.current?.focus() }, [])

  const results = query.length < 2 ? [] : alerts.filter(a =>
    [a.normalized_text, a.raw_text, a.commodity, a.source, a.location]
      .some(f => f?.toLowerCase().includes(query.toLowerCase()))
  ).slice(0, 10)

  const select = (alert) => {
    openDrawer(alert)
    onClose()
  }

  return (
    <>
      <div className="fixed inset-0 bg-black/70 backdrop-blur-md z-50 animate-fade-in" onClick={onClose} />
      <div className="fixed top-24 left-1/2 -translate-x-1/2 w-full max-w-xl z-50 animate-slide-in-top">
        <div className="bg-[#111827] rounded-2xl border border-[#1e2d45] shadow-2xl overflow-hidden">
          <div className="flex items-center gap-3 px-4 py-4 border-b border-[#1e2d45]">
            <Search size={18} className="text-slate-400 shrink-0" />
            <input
              ref={inputRef}
              value={query}
              onChange={e => setQuery(e.target.value)}
              placeholder="Search signals by text, commodity, source…"
              className="flex-1 bg-transparent text-white placeholder-slate-500 outline-none text-sm"
            />
            <button onClick={onClose} className="text-slate-500 hover:text-slate-300 transition-colors">
              <X size={16} />
            </button>
          </div>

          {results.length > 0 && (
            <ul className="max-h-80 overflow-y-auto divide-y divide-[#1e2d45]">
              {results.map(a => {
                const sc = getSignalConfig(a.signal_type)
                return (
                  <li key={a.id}>
                    <button onClick={() => select(a)}
                      className="w-full flex items-start gap-3 px-4 py-3 hover:bg-white/5 transition-colors text-left">
                      <span className={`shrink-0 text-xs px-2 py-0.5 rounded font-mono font-bold mt-0.5 ${sc.bg} ${sc.text} border ${sc.border}`}>
                        {sc.label}
                      </span>
                      <div className="min-w-0">
                        <p className="text-white text-sm truncate">
                          {truncate(a.normalized_text || a.raw_text, 70)}
                        </p>
                        <p className="text-slate-500 text-xs mt-0.5">
                          {a.source} · {a.commodity} · {relativeTime(a.event_time || a.created_at)}
                        </p>
                      </div>
                    </button>
                  </li>
                )
              })}
            </ul>
          )}

          {query.length >= 2 && results.length === 0 && (
            <p className="text-slate-500 text-sm text-center py-8">No signals match "{query}"</p>
          )}

          <div className="px-4 py-2 border-t border-[#1e2d45] flex items-center justify-between">
            <span className="text-slate-600 text-xs">↑↓ navigate  ↩ open  esc close</span>
            <span className="text-slate-600 text-xs font-mono">⌘K</span>
          </div>
        </div>
      </div>
    </>
  )
}
