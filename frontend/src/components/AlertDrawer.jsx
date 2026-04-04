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
        className="fixed inset-0 z-40 animate-fade-in"
        style={{ background: 'rgba(0,0,0,0.75)', backdropFilter: 'blur(8px)', WebkitBackdropFilter: 'blur(8px)' }}
        onClick={onClose}
      />

      {/* Drawer */}
      <div className="fixed right-0 top-0 h-full w-full max-w-lg z-50 animate-slide-in-right flex flex-col shadow-2xl"
        style={{
          background: 'rgba(8,11,20,0.85)',
          backdropFilter: 'blur(32px)',
          WebkitBackdropFilter: 'blur(32px)',
          borderLeft: '1px solid rgba(255,255,255,0.08)',
        }}>
        {/* Header */}
        <div className="flex items-start justify-between p-6" style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
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
            <p className="text-white/30 text-xs font-mono mt-0.5 truncate max-w-xs">{signal.id}</p>
          </div>
          <button onClick={onClose} className="text-white/30 hover:text-white/80 transition-colors p-1.5 rounded-lg hover:bg-white/8">
            <X size={18} />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-5">
          {/* Confidence */}
          <div className="flex items-center gap-6">
            <ConfidenceGauge value={signal.confidence ?? 0} size={80} />
            <div>
              <p className="text-white/40 text-xs uppercase tracking-widest mb-1">Confidence</p>
              <p className="text-white text-2xl font-bold font-mono">
                {((signal.confidence ?? 0) * 100).toFixed(0)}%
              </p>
            </div>
          </div>

          {/* Metadata grid */}
          <div className="grid grid-cols-2 gap-3">
            {[
              { icon: Tag,           label: 'Source',    val: `${getSourceIcon(signal.source)} ${signal.source ?? '—'}` },
              { icon: MapPin,        label: 'Location',  val: signal.location || '—' },
              { icon: Zap,           label: 'Commodity', val: signal.commodity || '—' },
              { icon: Clock,         label: 'Time',      val: formatDateTime(signal.event_time || signal.created_at) },
              { icon: AlertTriangle, label: 'Language',  val: signal.language || '—' },
              { icon: Tag,           label: 'Category',  val: signal.category || '—' },
            ].map(({ icon: Icon, label, val }) => (
              <div key={label} className="rounded-xl p-3"
                style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.07)' }}>
                <div className="flex items-center gap-1.5 text-white/30 text-xs mb-1">
                  <Icon size={11} />
                  <span className="uppercase tracking-widest">{label}</span>
                </div>
                <p className="text-white/90 text-sm font-medium truncate">{val}</p>
              </div>
            ))}
          </div>

          {/* Signal text */}
          <div className="rounded-xl p-4"
            style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.07)' }}>
            <p className="text-white/30 text-xs uppercase tracking-widest mb-3">Signal Text</p>
            <p className="text-white/80 text-sm leading-relaxed font-mono whitespace-pre-wrap break-words">
            {getAlertText(signal)}
            </p>
          </div>

          {/* Relative time */}
          <div className="flex items-center gap-2 text-white/25 text-xs">
            <Clock size={12} />
            <span>{relativeTime(signal.event_time || signal.created_at)}</span>
          </div>
        </div>
      </div>
    </>
  )
}
