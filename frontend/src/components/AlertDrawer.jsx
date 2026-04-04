import { useEffect } from 'react'
import { X, MapPin, Clock, Tag, Zap, AlertTriangle } from 'lucide-react'
import { getSignalConfig, getSeverityConfig, formatDateTime, relativeTime, getSourceIcon, getAlertText } from '../lib/utils'
import ConfidenceGauge from './ConfidenceGauge'

export default function AlertDrawer({ signal, onClose }) {
  if (!signal) return null
  const sc = getSignalConfig(signal.signal_type)
  const sev = getSeverityConfig(signal.severity)

  useEffect(() => {
    const handler = (e) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 animate-fade-in"
        onClick={onClose}
      />

      {/* Drawer */}
      <div className="fixed right-0 top-0 h-full w-full max-w-lg bg-[#111827] border-l border-[#1e2d45] z-50 animate-slide-in-right flex flex-col shadow-2xl">
        {/* Header */}
        <div className="flex items-start justify-between p-6 border-b border-[#1e2d45]">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className={`px-2 py-0.5 rounded text-xs font-bold ${sc.bg} ${sc.text} border ${sc.border}`}>
                {sc.label}
              </span>
              <span className={`px-2 py-0.5 rounded text-xs font-bold ${sev.bg} ${sev.text} border ${sev.border}`}>
                {sev.label}
              </span>
            </div>
            <p className="text-white font-semibold text-base">Signal Detail</p>
            <p className="text-slate-500 text-xs font-mono mt-0.5 truncate max-w-xs">{signal.id}</p>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-white transition-colors p-1 rounded hover:bg-white/10">
            <X size={20} />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Confidence */}
          <div className="flex items-center gap-6">
            <ConfidenceGauge value={signal.confidence ?? 0} size={80} />
            <div>
              <p className="text-slate-400 text-xs uppercase tracking-widest mb-1">Confidence</p>
              <p className="text-white text-2xl font-bold font-mono">
                {((signal.confidence ?? 0) * 100).toFixed(0)}%
              </p>
            </div>
          </div>

          {/* Metadata grid */}
          <div className="grid grid-cols-2 gap-4">
            {[
              { icon: Tag,           label: 'Source',    val: `${getSourceIcon(signal.source)} ${signal.source ?? '—'}` },
              { icon: MapPin,        label: 'Location',  val: signal.location || '—' },
              { icon: Zap,           label: 'Commodity', val: signal.commodity || '—' },
              { icon: Clock,         label: 'Time',      val: formatDateTime(signal.event_time || signal.created_at) },
              { icon: AlertTriangle, label: 'Language',  val: signal.language || '—' },
              { icon: Tag,           label: 'Category',  val: signal.category || '—' },
            ].map(({ icon: Icon, label, val }) => (
              <div key={label} className="bg-[#1a2235] rounded-lg p-3 border border-[#1e2d45]">
                <div className="flex items-center gap-1.5 text-slate-500 text-xs mb-1">
                  <Icon size={11} />
                  <span className="uppercase tracking-widest">{label}</span>
                </div>
                <p className="text-white text-sm font-medium truncate">{val}</p>
              </div>
            ))}
          </div>

          {/* Signal text */}
          <div className="bg-[#1a2235] rounded-lg border border-[#1e2d45] p-4">
            <p className="text-slate-400 text-xs uppercase tracking-widest mb-3">Signal Text</p>
            <p className="text-slate-200 text-sm leading-relaxed font-mono whitespace-pre-wrap break-words">
            {getAlertText(signal)}
            </p>
          </div>

          {/* Relative time */}
          <div className="flex items-center gap-2 text-slate-500 text-xs">
            <Clock size={12} />
            <span>{relativeTime(signal.event_time || signal.created_at)}</span>
          </div>
        </div>
      </div>
    </>
  )
}
